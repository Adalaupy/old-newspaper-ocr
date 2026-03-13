"""OCR engine implementations package."""

from services.ocr.ocr_base import BaseOCREngine
from services.ocr.ocr_engine_easyocr import OCREngine as EasyOCREngine
from services.ocr.ocr_engine_mistral import OCREngine as MistralOCREngine
from services.ocr.ocr_engine_paddle import OCREngine as PaddleOCREngine

__all__ = ["BaseOCREngine", "EasyOCREngine", "MistralOCREngine", "PaddleOCREngine"]