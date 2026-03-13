"""
OCR Engine service
"""
import os

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
from services.ocr.ocr_base import BaseOCREngine


class OCREngine(BaseOCREngine):
    """Handles OCR operations using PaddleOCR"""

    def _initialize_engine(self):
        """Initialize PaddleOCR with the current project settings."""
        try:
            os.environ["MKLDNN_VERBOSE"] = "0"
            os.environ["ONEDNN_VERBOSE"] = "0"

            init_kwargs = {
                "lang": config.OCR_LANG,
                "text_rec_score_thresh": config.OCR_DROP_SCORE,
                "text_det_thresh": config.OCR_DET_DB_THRESH,
                "text_det_box_thresh": config.OCR_DET_DB_BOX_THRESH,
                "use_textline_orientation": False,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
            }
            if config.OCR_USE_GPU:
                init_kwargs["device"] = "gpu"

            self.ocr = PaddleOCR(**init_kwargs)
        except Exception as e:
            print(f"Error initializing OCR engine: {e}")
            raise

    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """Run PaddleOCR and return final extracted text."""
        if self.ocr is None:
            raise RuntimeError("OCR engine not initialized")

        prepared_image = self._ensure_rgb(image)
        result = self.ocr.predict(
            np.array(prepared_image, dtype=np.uint8),
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            text_rec_score_thresh=config.OCR_DROP_SCORE,
            text_det_thresh=config.OCR_DET_DB_THRESH,
            text_det_box_thresh=config.OCR_DET_DB_BOX_THRESH,
            return_word_box=False,
        )

        lines = []
        for item in result or []:
            if not hasattr(item, "get"):
                continue

            polygons = item.get("rec_polys")
            if polygons is None:
                polygons = item.get("dt_polys")
            if isinstance(polygons, np.ndarray):
                polygons = polygons.tolist()

            texts = item.get("rec_texts")
            if texts is None:
                continue
            if isinstance(texts, np.ndarray):
                texts = texts.tolist()

            for index, text in enumerate(texts):
                cleaned = "" if text is None else str(text).strip()
                if cleaned:
                    x_pos, y_pos = self._get_line_position(polygons, index)
                    lines.append((x_pos, y_pos, cleaned))

        lines = self._sort_lines(lines, read_direction)
        paragraph = self._join_as_paragraph(text for _, _, text in lines)

        return self._finalize_text(paragraph)

    @staticmethod
    def _get_line_position(polygons, index: int) -> tuple[float, float]:
        """Return a sortable center point for a detected text polygon."""
        if not isinstance(polygons, list) or index >= len(polygons):
            return float(index), float(index)

        polygon = polygons[index]
        if isinstance(polygon, np.ndarray):
            polygon = polygon.tolist()

        if not isinstance(polygon, (list, tuple)):
            return float(index), float(index)

        points = []
        for point in polygon:
            if isinstance(point, np.ndarray):
                point = point.tolist()
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                continue

        if not points:
            return float(index), float(index)

        x_coords = [point[0] for point in points]
        y_coords = [point[1] for point in points]
        return sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords)

    @staticmethod
    def _sort_lines(lines: list[tuple[float, float, str]], read_direction: str) -> list[tuple[float, float, str]]:
        """Sort detected lines by the configured reading direction."""
        if read_direction == "vertical_rtl":
            return sorted(lines, key=lambda item: (-item[0], item[1]))
        if read_direction == "vertical_ltr":
            return sorted(lines, key=lambda item: (item[0], item[1]))
        if read_direction == "horizontal_rtl":
            return sorted(lines, key=lambda item: (item[1], -item[0]))
        return sorted(lines, key=lambda item: (item[1], item[0]))

    @staticmethod
    def _join_as_paragraph(texts) -> str:
        """Join OCR segments into a paragraph-style string."""
        cleaned_texts = [text for text in texts if text]
        if not cleaned_texts:
            return ""

        if str(config.OCR_LANG).strip().lower() in {"en", "english"}:
            return " ".join(cleaned_texts)

        return "".join(cleaned_texts)
