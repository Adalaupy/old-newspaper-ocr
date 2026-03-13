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
from services.ocr.ocr_shared import normalize_polygon_points
from services.ocr.ocr_shared import to_float


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

    def _run_ocr(self, image: Image.Image):
        """Run PaddleOCR and return raw backend result."""
        if self.ocr is None:
            raise RuntimeError("OCR engine not initialized")

        img_array = np.array(image, dtype=np.uint8)
        return self.ocr.predict(
            img_array,
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            text_rec_score_thresh=config.OCR_DROP_SCORE,
            text_det_thresh=config.OCR_DET_DB_THRESH,
            text_det_box_thresh=config.OCR_DET_DB_BOX_THRESH,
            return_word_box=False,
        )

    def _normalize_ocr_result(self, result: list) -> list:
        """
        Normalize PaddleOCR results to legacy line format:
        [ [box, [text, confidence]], ... ]
        """
        if not result or result == [None]:
            return []

        normalized = []
        for item in result:
            if not hasattr(item, "get"):
                continue

            polygons = item.get("rec_polys")
            if polygons is None:
                polygons = item.get("dt_polys")
            if polygons is None:
                polygons = []

            texts = item.get("rec_texts")
            if texts is None:
                texts = []

            scores = item.get("rec_scores")
            if scores is None:
                scores = []

            if isinstance(polygons, np.ndarray):
                polygons = polygons.tolist()
            if isinstance(texts, np.ndarray):
                texts = texts.tolist()
            if isinstance(scores, np.ndarray):
                scores = scores.tolist()

            for index, polygon in enumerate(polygons):
                points = normalize_polygon_points(polygon)
                if not points:
                    continue

                text = texts[index] if index < len(texts) else ""
                score = scores[index] if index < len(scores) else 0.0
                normalized.append([points, ["" if text is None else str(text).strip(), to_float(score, 0.0)]])

        return normalized
