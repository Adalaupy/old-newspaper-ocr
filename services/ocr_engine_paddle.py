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
from services.ocr_base import BaseOCREngine
from services.ocr_shared import normalize_polygon_points
from services.ocr_shared import to_float



class OCREngine(BaseOCREngine):
    """Handles OCR operations using PaddleOCR"""

    def _initialize_engine(self):
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

    def _run_ocr(self, image: Image.Image):
        """Run PaddleOCR and return raw backend result."""
        # Method 1: Try with file path (most reliable, avoids OneDNN issues)
        temp_file = None
        try:
            # Save to temporary file
            temp_file = os.path.join(tempfile.gettempdir(), f"ocr_temp_{uuid.uuid4().hex}.png")
            image.save(temp_file, format='PNG')
            return self._predict(temp_file)
        except Exception:
            # Method 2: Fallback to numpy array
            img_array = np.array(image, dtype=np.uint8)
            return self._predict(img_array)
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

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
                    points = normalize_polygon_points(polygon)

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

                    confidence = to_float(score_value, 0.0)

                    normalized.append([points, [text, confidence]])
            return normalized

        return []
