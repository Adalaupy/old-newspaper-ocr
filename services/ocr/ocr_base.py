"""
Base class for OCR engines with shared recognition pipeline.
"""
from abc import ABC
from abc import abstractmethod

from PIL import Image

import config
from services.ocr.ocr_shared import ensure_traditional_chinese
from services.ocr.ocr_shared import initialize_opencc_converter
from services.text_corrector import correct_ocr_text


class BaseOCREngine(ABC):
    """Reusable OCR engine base with shared final text post-processing."""

    def __init__(self):
        self.opencc_converter = initialize_opencc_converter()
        self._initialize_engine()

    @abstractmethod
    def _initialize_engine(self):
        """Initialize the underlying OCR backend."""

    @abstractmethod
    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """Run OCR on the image and return final extracted text."""

    def _finalize_text(self, text: str) -> str:
        """Apply shared cleanup and final text conversion."""
        final_text = "" if text is None else str(text).strip()
        if not final_text:
            return config.OCR_UNKNOWN_TOKEN

        try:
            final_text = correct_ocr_text(final_text)
        except Exception as e:
            print(f"OCR post-processing failed: {e}")
            return config.OCR_UNKNOWN_TOKEN

        if not final_text.strip():
            return config.OCR_UNKNOWN_TOKEN

        return ensure_traditional_chinese(final_text, self.opencc_converter)

    @staticmethod
    def _ensure_rgb(image: Image.Image) -> Image.Image:
        """Ensure image is RGB mode for OCR backends."""
        if image.mode != "RGB":
            return image.convert("RGB")
        return image
