"""Services package"""
import importlib

import config

from services.image_processor import ImageProcessor
from services.pdf_handler import PDFHandler
from services.file_manager import FileManager


def _normalize_engine_module_name(engine_module_name: str) -> str:
    """Map legacy engine names to the services/ocr package layout."""
    normalized = str(engine_module_name).strip()
    if normalized.endswith(".py"):
        normalized = normalized[:-3]

    if not normalized:
        normalized = "ocr_engine_paddle"

    if normalized.startswith("services."):
        normalized = normalized[len("services."):]

    if "." not in normalized:
        normalized = f"ocr.{normalized}"

    return normalized


def _load_ocr_engine_class_from_module(engine_module_name: str):
    """Load OCREngine class from a specific engine module name."""
    engine_module_name = _normalize_engine_module_name(engine_module_name)

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
        f"Ensure the module exists under services/ and defines OCREngine."
    ) from last_error


def _load_ocr_engine_class():
    """Load OCREngine class from the configured engine module."""
    engine_module_name = getattr(config, "OCR_ENGINE", None) or getattr(config, "ORC_ENGINE", "ocr_engine_paddle")
    return _load_ocr_engine_class_from_module(engine_module_name)


def create_ocr_engine():
    """Create a fresh OCR engine instance from the current config."""
    return _load_ocr_engine_class()()


def create_ocr_engine_from_module(engine_module_name: str):
    """Create a fresh OCR engine instance from a specific module name."""
    return _load_ocr_engine_class_from_module(engine_module_name)()


OCREngine = _load_ocr_engine_class()

__all__ = [
    'ImageProcessor',
    'OCREngine',
    'PDFHandler',
    'FileManager',
    'create_ocr_engine',
    'create_ocr_engine_from_module',
]
