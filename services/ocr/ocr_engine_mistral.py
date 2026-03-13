"""
OCR Engine service using Mistral OCR API.
"""
import importlib
import os

from PIL import Image

import config
from services.ocr.ocr_base import BaseOCREngine
from services.ocr.ocr_shared import build_png_data_url
from services.ocr.ocr_shared import split_markdown_lines


class OCREngine(BaseOCREngine):
    """Handles OCR operations using Mistral OCR."""

    def _initialize_engine(self):
        """Initialize Mistral client with API key from config/.env."""
        mistral_class = self._resolve_mistral_client_class()

        api_key = (getattr(config, "MISTRAL_API_KEY", "") or os.getenv("MISTRAL_API_KEY", "")).strip()
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is missing. Set it in .env or your environment variables.")

        self.client = mistral_class(api_key=api_key)

    def recognize_text(self, image: Image.Image, read_direction: str = "vertical_rtl") -> str:
        """Run Mistral OCR and return final extracted text."""
        if not hasattr(self, "client") or self.client is None:
            raise RuntimeError("OCR engine not initialized")

        prepared_image = self._ensure_rgb(image)
        request_kwargs = {
            "document": {
                "type": "image_url",
                "image_url": build_png_data_url(prepared_image),
            },
            "model": config.OCR_MISTRAL_MODEL,
            "include_image_base64": config.OCR_MISTRAL_INCLUDE_IMAGE_BASE64,
        }

        language_hint = self._resolve_language_hint()
        if language_hint and getattr(config, "OCR_MISTRAL_LANGUAGE_HINT_ENABLED", True):
            request_kwargs["document_annotation_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "language_guided_ocr",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                },
            }
            request_kwargs["document_annotation_prompt"] = (
                "The document language is expected to be "
                f"{language_hint}. Extract OCR text faithfully and return only that text in the field `text`."
            )

        response = self.client.ocr.process(**request_kwargs)
        payload = self._response_to_dict(response)

        lines = []
        for page in payload.get("pages", []):
            lines.extend(split_markdown_lines(self._get_page_markdown(page)))

        return self._finalize_text("\n".join(lines))

    @staticmethod
    def _response_to_dict(response) -> dict:
        """Convert Mistral SDK response object to plain dictionary."""
        if response is None:
            return {}

        if isinstance(response, dict):
            return response

        if hasattr(response, "model_dump"):
            try:
                return response.model_dump()
            except Exception:
                pass

        if hasattr(response, "dict"):
            try:
                return response.dict()
            except Exception:
                pass

        pages = getattr(response, "pages", None)
        if pages is not None:
            return {"pages": pages}

        return {}

    @staticmethod
    def _get_page_markdown(page) -> str:
        """Extract markdown text from a single page payload."""
        if page is None:
            return ""
        if isinstance(page, dict):
            return page.get("markdown", "")
        return getattr(page, "markdown", "")

    def _resolve_language_hint(self) -> str:
        """Resolve language hint from config when enabled."""
        explicit_hint = getattr(config, "OCR_MISTRAL_LANGUAGE_HINT", "")
        if isinstance(explicit_hint, str) and explicit_hint.strip():
            return explicit_hint.strip()

        lang_code = str(getattr(config, "OCR_LANG", "") or "").strip().lower()
        return OCREngine._map_lang_code_to_hint(lang_code)

    @staticmethod
    def _map_lang_code_to_hint(lang_code: str) -> str:
        """Map internal language codes to human-readable hints for Mistral."""
        code = str(lang_code or "").strip().lower()
        lang_map = {
            "ch": "Traditional Chinese",
            "chinese": "Traditional Chinese",
            "chinese_cht": "Traditional Chinese",
            "ch_tra": "Traditional Chinese",
            "ch_sim": "Simplified Chinese",
            "en": "English",
            "english": "English",
        }
        return lang_map.get(code, "")

    @staticmethod
    def _resolve_mistral_client_class():
        """Resolve Mistral client class across SDK variants."""
        try:
            module = importlib.import_module("mistralai")
            if hasattr(module, "Mistral"):
                return module.Mistral
        except ImportError:
            pass

        try:
            module = importlib.import_module("mistralai.client")
            if hasattr(module, "Mistral"):
                return module.Mistral
        except ImportError:
            pass

        raise ImportError("mistralai is not installed. Install it with: pip install mistralai")
