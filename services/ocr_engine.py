"""
OCR Engine service
"""
import inspect
import os
import tempfile
import uuid

# Configure Paddle runtime flags before importing paddle/paddleocr.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_DISABLE_MKLDNN", "1")
os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_enable_new_ir_in_executor", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import config
import pycorrector

try:
    from opencc import OpenCC
except Exception:
    OpenCC = None



class OCREngine:
    """Handles OCR operations using PaddleOCR"""
    
    def __init__(self):
        """Initialize OCR engine"""
        self.ocr = None
        self.pycorrector_available = pycorrector is not None
        self.opencc_converter = self._initialize_opencc_converter()
        self._initialize_ocr()

    def _initialize_opencc_converter(self):
        """Initialize OpenCC converter for final Traditional Chinese output."""
        if not config.OCR_ENFORCE_TRADITIONAL_CHINESE:
            return None

        if OpenCC is None:
            print("OpenCC is not available; OCR output will not be converted to Traditional Chinese")
            return None

        try:
            return OpenCC(config.OCR_TRADITIONAL_CONVERSION)
        except Exception as e:
            print(f"Failed to initialize OpenCC converter: {e}")
            return None
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR with default settings"""
        try:
            # Keep OneDNN logs quiet; disabling flags are set at module import time.
            os.environ["MKLDNN_VERBOSE"] = "0"
            os.environ["ONEDNN_VERBOSE"] = "0"

            init_signature = inspect.signature(PaddleOCR.__init__)
            supported_args = set(init_signature.parameters.keys())

            init_kwargs = {
                "lang": config.OCR_LANG,
            }

            if "drop_score" in supported_args:
                init_kwargs["drop_score"] = config.OCR_DROP_SCORE
            if "text_rec_score_thresh" in supported_args:
                init_kwargs["text_rec_score_thresh"] = config.OCR_DROP_SCORE
            if "det_db_thresh" in supported_args:
                init_kwargs["det_db_thresh"] = config.OCR_DET_DB_THRESH
            if "det_db_box_thresh" in supported_args:
                init_kwargs["det_db_box_thresh"] = config.OCR_DET_DB_BOX_THRESH

            if "device" in supported_args:
                init_kwargs["device"] = "gpu" if config.OCR_USE_GPU else "cpu"
            elif "use_gpu" in supported_args:
                init_kwargs["use_gpu"] = config.OCR_USE_GPU

            if "use_textline_orientation" in supported_args:
                init_kwargs["use_textline_orientation"] = False
            elif "use_angle_cls" in supported_args:
                init_kwargs["use_angle_cls"] = False

            if "use_doc_orientation_classify" in supported_args:
                init_kwargs["use_doc_orientation_classify"] = False
            if "use_doc_unwarping" in supported_args:
                init_kwargs["use_doc_unwarping"] = False
            if "use_doc_preprocessor" in supported_args:
                init_kwargs["use_doc_preprocessor"] = False
            
            # Explicitly disable MKLDNN if parameter exists
            if "enable_mkldnn" in supported_args:
                init_kwargs["enable_mkldnn"] = False
            if "use_mkldnn" in supported_args:
                init_kwargs["use_mkldnn"] = False

            self.ocr = PaddleOCR(**init_kwargs)
        except Exception as e:
            print(f"Error initializing OCR engine: {e}")
            raise

    def _predict(self, input_data):
        """Run OCR prediction using the current PaddleOCR API."""
        if self.ocr is None:
            raise RuntimeError("OCR engine not initialized")

        if not hasattr(self.ocr, "predict"):
            raise RuntimeError("PaddleOCR predict() is not available")

        predict_signature = inspect.signature(self.ocr.predict)
        supported_args = set(predict_signature.parameters.keys())

        predict_kwargs = {}
        if "batch_size" in supported_args:
            predict_kwargs["batch_size"] = 1
        if "use_textline_orientation" in supported_args:
            predict_kwargs["use_textline_orientation"] = False
        if "use_angle_cls" in supported_args:
            predict_kwargs["use_angle_cls"] = False
        if "use_doc_orientation_classify" in supported_args:
            predict_kwargs["use_doc_orientation_classify"] = False
        if "use_doc_unwarping" in supported_args:
            predict_kwargs["use_doc_unwarping"] = False
        if "use_doc_preprocessor" in supported_args:
            predict_kwargs["use_doc_preprocessor"] = False

        return self.ocr.predict(input_data, **predict_kwargs)
    
    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """
        Perform OCR on an image
        
        Args:
            image: PIL Image to process
            read_direction: Reading direction (vertical_rtl, vertical_ltr, horizontal_ltr, horizontal_rtl)
            
        Returns:
            Recognized text as string
        """
        if self.ocr is None:
            raise RuntimeError("OCR engine not initialized")
        
        # Ensure image is in RGB mode (not RGBA, P, L, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Method 1: Try with file path (most reliable, avoids OneDNN issues)
        temp_file = None
        try:
            # Save to temporary file
            temp_file = os.path.join(tempfile.gettempdir(), f"ocr_temp_{uuid.uuid4().hex}.png")
            image.save(temp_file, format='PNG')
            result = self._predict(temp_file)
        except Exception as file_error:
            # Method 2: Fallback to numpy array
            try:
                img_array = np.array(image, dtype=np.uint8)
                result = self._predict(img_array)
            except Exception as array_error:
                print(f"OCR processing failed: {array_error}")
                return config.OCR_UNKNOWN_TOKEN
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

        try:
            normalized = self._normalize_ocr_result(result)
        except Exception as normalize_error:
            print(f"OCR normalize failed: {normalize_error}")
            return config.OCR_UNKNOWN_TOKEN

        if not normalized:
            return config.OCR_UNKNOWN_TOKEN
        
        # Extract text based on reading direction
        try:
            text = self._format_text_by_direction(normalized, read_direction)
        except Exception as format_error:
            print(f"OCR format failed: {format_error}")
            return config.OCR_UNKNOWN_TOKEN

        if not text.strip():
            return config.OCR_UNKNOWN_TOKEN

        return self._ensure_traditional_chinese(text)
    
    def _format_text_by_direction(self, ocr_result: list, direction: str) -> str:
        """
        Format OCR results based on reading direction
        
        Args:
            ocr_result: Raw OCR result from PaddleOCR
            direction: Reading direction
            
        Returns:
            Formatted text string
        """
        if not ocr_result:
            return ""
        
        # Extract text boxes with coordinates
        text_boxes = []
        for line in ocr_result:

            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            
            box = line[0]  # Coordinates
            text_info = line[1]

            if not isinstance(text_info, (list, tuple)) or len(text_info) < 1:
                continue

            text = "" if text_info[0] is None else str(text_info[0]).strip()



            try:
                confidence = float(text_info[1]) if len(text_info) > 1 else 0.0
            except (TypeError, ValueError):
                confidence = 0.0

            if not text or confidence < config.OCR_UNKNOWN_CONFIDENCE:
                text = config.OCR_UNKNOWN_TOKEN

            if not isinstance(box, (list, tuple)):
                continue

            points = []
            for point in box:
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    continue
                try:
                    points.append((float(point[0]), float(point[1])))
                except (TypeError, ValueError):
                    continue

            if not points:
                continue

            
            # Calculate center point for sorting
            x_coords = [point[0] for point in points]
            y_coords = [point[1] for point in points]
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            box_width = max(x_coords) - min(x_coords)
            box_height = max(y_coords) - min(y_coords)
            
            text_boxes.append({
                'text': text,
                'x': center_x,
                'y': center_y,
                'confidence': confidence,
                'width': box_width,
                'height': box_height,
            })

        if not text_boxes:
            return ""
        
        # Sort based on reading direction
        if direction == "vertical_rtl":
            # Traditional Chinese: right to left, top to bottom
            # Group by columns (x), sort columns right to left, within column top to bottom
            text_boxes.sort(key=lambda b: (-b['x'], b['y']))
        elif direction == "vertical_ltr":
            # Left to right, top to bottom
            text_boxes.sort(key=lambda b: (b['x'], b['y']))
        elif direction == "horizontal_ltr":
            # Standard left to right, top to bottom
            text_boxes.sort(key=lambda b: (b['y'], b['x']))
        elif direction == "horizontal_rtl":
            # Right to left, top to bottom
            text_boxes.sort(key=lambda b: (b['y'], -b['x']))
        
        # Combine text with optional missing-word marker insertion.
        recognized_tokens = self._insert_gap_unknown_tokens(text_boxes, direction)
        recognized_text = '\n'.join(recognized_tokens)

        return self._apply_pycorrector(recognized_text)

    def _insert_gap_unknown_tokens(self, text_boxes: list, direction: str) -> list:
        """Insert [UNK] when spacing suggests a likely missing word."""
        if not text_boxes:
            return []

        if not config.OCR_GAP_UNKNOWN_ENABLED:
            return [box['text'] for box in text_boxes]



        widths = [max(1.0, float(box.get('width', 1.0))) for box in text_boxes]
        heights = [max(1.0, float(box.get('height', 1.0))) for box in text_boxes]
        median_width = float(np.median(widths))
        median_height = float(np.median(heights))

        same_row_tol = max(2.0, median_height * config.OCR_SAME_LINE_TOLERANCE)
        same_col_tol = max(2.0, median_width * config.OCR_SAME_LINE_TOLERANCE)
        horizontal_gap_thresh = max(median_width * config.OCR_GAP_FACTOR, median_width + 5.0)
        vertical_gap_thresh = max(median_height * config.OCR_GAP_FACTOR, median_height + 5.0)

        tokens = []
        prev = None
        for box in text_boxes:
            if prev is not None:
                missing_gap = False
                if direction in ("horizontal_ltr", "horizontal_rtl"):
                    same_line = abs(box['y'] - prev['y']) <= same_row_tol
                    gap = abs(box['x'] - prev['x'])
                    if same_line and gap > horizontal_gap_thresh:
                        missing_gap = True
                else:
                    same_line = abs(box['x'] - prev['x']) <= same_col_tol
                    gap = abs(box['y'] - prev['y'])
                    if same_line and gap > vertical_gap_thresh:
                        missing_gap = True

                if missing_gap:
                    tokens.append(config.OCR_UNKNOWN_TOKEN)

            tokens.append(box['text'])
            prev = box

        return tokens

    def _apply_pycorrector(self, text: str) -> str:
        """Post-correct OCR text with pycorrector when available."""
        if not text:
            return text

        if not config.OCR_PYCORRECTOR_ENABLED or not self.pycorrector_available:
            return text

        corrected_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                corrected_lines.append(line)
                continue

            if config.OCR_PYCORRECTOR_SKIP_UNKNOWN and config.OCR_UNKNOWN_TOKEN in stripped:
                corrected_lines.append(line)
                continue

            try:
                corrected_line, _ = pycorrector.correct(stripped)
                corrected_lines.append(corrected_line if corrected_line else line)
            except Exception:
                corrected_lines.append(line)

        return '\n'.join(corrected_lines)

    def _ensure_traditional_chinese(self, text: str) -> str:
        """Convert final OCR text to Traditional Chinese when configured."""
        if not text:
            return text

        if not config.OCR_ENFORCE_TRADITIONAL_CHINESE:
            return text

        if self.opencc_converter is None:
            return text

        try:
            return self.opencc_converter.convert(text)
        except Exception:
            return text

    def _normalize_ocr_result(self, result: list) -> list:
        """
        Normalize PaddleOCR results to legacy line format:
        [ [box, [text, confidence]], ... ]
        """
        if not result:
            return []
        
        # Handle None result (no text detected)
        if result is None or result == [None]:
            return []

        def is_legacy_line(line):
            return (
                isinstance(line, (list, tuple))
                and len(line) >= 2
                and isinstance(line[0], (list, tuple))
                and isinstance(line[1], (list, tuple))
                and len(line[1]) >= 1
            )

        # Legacy ocr() method wraps result in extra list for pages: [[lines...]]
        # Keep this unwrap for backward compatibility.
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
            # Check if first element is the actual lines list
            if result[0] and isinstance(result[0][0], (list, tuple)):
                result = result[0]

        # PaddleOCR predict() may return custom result objects with to_dict()
        if isinstance(result, list) and result and not isinstance(result[0], (list, tuple, dict)):
            converted = []
            for item in result:
                if hasattr(item, "to_dict"):
                    try:
                        converted.append(item.to_dict())
                    except Exception:
                        continue
                elif hasattr(item, "res") and isinstance(item.res, dict):
                    converted.append(item.res)
                elif hasattr(item, "keys"):
                    try:
                        converted.append({k: item[k] for k in item.keys()})
                    except Exception:
                        continue
            if converted:
                result = converted
        
        # Legacy format: [ [box, [text, confidence]], ... ]
        if isinstance(result, list) and result:
            if all(is_legacy_line(line) for line in result):
                return result

            if isinstance(result[0], (list, tuple)) and all(is_legacy_line(line) for line in result[0]):
                return list(result[0])

        # PaddleOCR v3 predict() usually returns list of dict-like page results
        if isinstance(result, list) and result and isinstance(result[0], dict):
            normalized = []
            for item in result:
                polygon_data = item.get("rec_polys")
                if polygon_data is None:
                    polygon_data = item.get("dt_polys")
                if polygon_data is None:
                    polygon_data = item.get("polygon")

                if polygon_data is None:
                    continue

                if isinstance(polygon_data, np.ndarray):
                    polygons = polygon_data.tolist()
                elif isinstance(polygon_data, (list, tuple)):
                    polygons = list(polygon_data)
                else:
                    polygons = [polygon_data]

                rec_text = item.get("rec_texts")
                if rec_text is None:
                    rec_text = item.get("rec_text")
                if rec_text is None:
                    rec_text = item.get("texts")
                if isinstance(rec_text, np.ndarray):
                    texts = rec_text.tolist()
                elif isinstance(rec_text, (list, tuple)):
                    texts = list(rec_text)
                elif rec_text is None:
                    texts = []
                else:
                    texts = [rec_text]

                rec_score = item.get("rec_scores")
                if rec_score is None:
                    rec_score = item.get("rec_score")
                if rec_score is None:
                    rec_score = item.get("scores")
                if isinstance(rec_score, np.ndarray):
                    scores = rec_score.tolist()
                elif isinstance(rec_score, (list, tuple)):
                    scores = list(rec_score)
                elif rec_score is None:
                    scores = []
                else:
                    scores = [rec_score]

                for idx, polygon in enumerate(polygons):
                    if isinstance(polygon, np.ndarray):
                        polygon_points = polygon.tolist()
                    elif isinstance(polygon, (list, tuple)):
                        polygon_points = list(polygon)
                    else:
                        continue

                    points = []
                    for point in polygon_points:
                        if isinstance(point, np.ndarray):
                            point = point.tolist()
                        if not isinstance(point, (list, tuple)) or len(point) < 2:
                            continue
                        try:
                            points.append([float(point[0]), float(point[1])])
                        except Exception:
                            continue

                    if not points:
                        continue

                    if idx < len(texts):
                        text = "" if texts[idx] is None else str(texts[idx])
                    elif item.get("text") is not None:
                        text = str(item.get("text"))
                    else:
                        text = ""

                    if idx < len(scores):
                        score_value = scores[idx]
                    else:
                        score_value = item.get("score", 0.0)

                    try:
                        confidence = float(score_value)
                    except Exception:
                        confidence = 0.0

                    normalized.append([points, [text, confidence]])
            return normalized

        return []
