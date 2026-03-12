"""Services package"""
import importlib

import config

from services.image_processor import ImageProcessor
from services.pdf_handler import PDFHandler
from services.file_manager import FileManager


def _load_ocr_engine_class():
    """Load OCREngine class from the configured engine module."""
    engine_module_name = getattr(config, "OCR_ENGINE", None) or getattr(config, "ORC_ENGINE", "ocr_engine_paddle")
    engine_module_name = str(engine_module_name).strip()
    if engine_module_name.endswith(".py"):
        engine_module_name = engine_module_name[:-3]

    if not engine_module_name:
        engine_module_name = "ocr_engine_paddle"

    candidate_modules = [engine_module_name]
    if engine_module_name.lower() != engine_module_name:
        candidate_modules.append(engine_module_name.lower())

    last_error = None
    for module_name in candidate_modules:
        try:
            module = importlib.import_module(f"services.{module_name}")
            if hasattr(module, "OCREngine"):
                return module.OCREngine
            raise ImportError(f"services.{module_name} does not define OCREngine")
        except Exception as exc:
            last_error = exc

    raise ImportError(
        f"Failed to load OCR engine module '{engine_module_name}'. "
        f"Ensure services/{engine_module_name}.py exists and defines OCREngine."
    ) from last_error


OCREngine = _load_ocr_engine_class()

__all__ = ['ImageProcessor', 'OCREngine', 'PDFHandler', 'FileManager']
