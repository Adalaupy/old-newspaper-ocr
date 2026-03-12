"""
Base class for OCR engines with shared recognition pipeline.
"""
from abc import ABC
from abc import abstractmethod

from PIL import Image

import config
from services.ocr_shared import ensure_traditional_chinese
from services.ocr_shared import format_text_by_direction
from services.ocr_shared import initialize_opencc_converter
from services.text_corrector import correct_ocr_text


class BaseOCREngine(ABC):
    """Reusable OCR engine base with common text post-processing flow."""

    def __init__(self):
        self.opencc_converter = initialize_opencc_converter()
        self._initialize_engine()

    @abstractmethod
    def _initialize_engine(self):
        """Initialize the underlying OCR backend."""

    @abstractmethod
    def _run_ocr(self, image: Image.Image):
        """Run OCR backend and return raw backend-specific result."""

    @abstractmethod
    def _normalize_ocr_result(self, result) -> list:
        """Normalize backend-specific OCR result into standard line schema."""

    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """
        Shared recognition pipeline for all engines.

        Returns recognized text as a string.
        """
        prepared_image = self._ensure_rgb(image)

        try:
            raw_result = self._run_ocr(prepared_image)
        except Exception as e:
            print(f"OCR processing failed: {e}")
            return config.OCR_UNKNOWN_TOKEN

        try:
            normalized = self._normalize_ocr_result(raw_result)
        except Exception as e:
            print(f"OCR normalize failed: {e}")
            return config.OCR_UNKNOWN_TOKEN

        if not normalized:
            return config.OCR_UNKNOWN_TOKEN

        try:
            text = format_text_by_direction(normalized, read_direction)
            text = correct_ocr_text(text)
        except Exception as e:
            print(f"OCR format failed: {e}")
            return config.OCR_UNKNOWN_TOKEN

        if not text.strip():
            return config.OCR_UNKNOWN_TOKEN

        return ensure_traditional_chinese(text, self.opencc_converter)

    @staticmethod
    def _ensure_rgb(image: Image.Image) -> Image.Image:
        """Ensure image is RGB mode for OCR backends."""
        if image.mode != "RGB":
            return image.convert("RGB")
        return image