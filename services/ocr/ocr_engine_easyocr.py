"""
OCR Engine service using EasyOCR
"""
from PIL import Image
import numpy as np

import config
from services.ocr.ocr_base import BaseOCREngine

try:
    import easyocr
except ImportError:
    easyocr = None


class OCREngine(BaseOCREngine):
    """Handles OCR operations using EasyOCR"""

    def _initialize_engine(self):
        """Initialize EasyOCR reader."""
        if easyocr is None:
            raise ImportError("easyocr is not installed. Install it with: pip install easyocr")

        try:
            lang_map = {
                "ch": "ch_sim",
                "chinese": "ch_sim",
                "chinese_cht": "ch_tra",
                "en": "en",
                "english": "en",
            }
            easyocr_lang = lang_map.get(config.OCR_LANG, "ch_sim")
            self.reader = easyocr.Reader([easyocr_lang], gpu=config.OCR_USE_GPU)
        except Exception as e:
            print(f"Error initializing EasyOCR engine: {e}")
            raise

    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """Run EasyOCR and return final extracted text."""
        if self.reader is None:
            raise RuntimeError("OCR engine not initialized")

        prepared_image = self._ensure_rgb(image)
        result = self.reader.readtext(np.array(prepared_image, dtype=np.uint8))

        lines = []
        for item in result or []:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue

            text = "" if item[1] is None else str(item[1]).strip()
            if text:
                lines.append(text)

        return self._finalize_text("\n".join(lines))
