"""
OCR Engine service using Mistral OCR API.
"""
import importlib
import json
import os
import re

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
        if getattr(config, "OCR_MISTRAL_REQUEST_DOCUMENT_ANNOTATION", True):
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
            request_kwargs["document_annotation_prompt"] = self._build_annotation_prompt(language_hint)

        response = self.client.ocr.process(**request_kwargs)
        payload = self._response_to_dict(response)

        annotation_text = ""
        if getattr(config, "OCR_MISTRAL_REQUEST_DOCUMENT_ANNOTATION", True):
            annotation_text = self._extract_document_annotation_text(payload)

        if annotation_text:
            lines = split_markdown_lines(annotation_text)
        else:
            lines = []
            for page in payload.get("pages", []):
                lines.extend(self._clean_markdown_fallback_lines(self._get_page_markdown(page)))

        return self._finalize_text("\n".join(lines))

    def _should_apply_text_correction(self) -> bool:
        """Keep Mistral output unmodified unless explicitly enabled."""
        return bool(getattr(config, "OCR_MISTRAL_APPLY_PYCORRECTOR", False))

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
            payload = {"pages": pages}
            annotation = getattr(response, "document_annotation", None)
            if annotation is not None:
                payload["document_annotation"] = annotation
            return payload

        return {}

    @staticmethod
    def _get_page_markdown(page) -> str:
        """Extract markdown text from a single page payload."""
        if page is None:
            return ""
        if isinstance(page, dict):
            return page.get("markdown", "")
        return getattr(page, "markdown", "")

    @staticmethod
    def _extract_document_annotation_text(payload: dict) -> str:
        """Extract plain text from document_annotation payload when available."""
        annotation = payload.get("document_annotation")
        if annotation is None:
            return ""

        if isinstance(annotation, str):
            stripped = annotation.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        value = parsed.get("text")
                        if isinstance(value, str) and value.strip():
                            return value
                except Exception:
                    # Some responses contain raw newlines in JSON-like strings.
                    try:
                        sanitized = stripped.replace("\r\n", "\\n").replace("\n", "\\n")
                        parsed = json.loads(sanitized)
                        if isinstance(parsed, dict):
                            value = parsed.get("text")
                            if isinstance(value, str) and value.strip():
                                return value
                    except Exception:
                        pass
            return annotation

        if isinstance(annotation, dict):
            value = annotation.get("text")
            if isinstance(value, str) and value.strip():
                return value

        return ""

    @staticmethod
    def _build_annotation_prompt(language_hint: str) -> str:
        """Build a strict transcription prompt for Mistral OCR."""
        prompt_parts = []
        if language_hint and getattr(config, "OCR_MISTRAL_LANGUAGE_HINT_ENABLED", True):
            prompt_parts.append(f"The document language is expected to be {language_hint}.")

        if getattr(config, "OCR_MISTRAL_STRICT_TRANSCRIPTION", True):
            prompt_parts.append(
                "Transcribe the document exactly as written. Do not summarize, infer missing words, "
                "translate, reorder content, or convert paragraphs into bullet points. Preserve reading "
                "order, punctuation, numbers, and line breaks. Return only the exact transcription in the field `text`."
            )
        else:
            prompt_parts.append(
                "Extract OCR text faithfully and return only that text in the field `text`."
            )

        return " ".join(prompt_parts)

    @classmethod
    def _clean_markdown_fallback_lines(cls, markdown_text: str) -> list[str]:
        """Normalize markdown fallback text into cleaner plain-text lines."""
        lines = split_markdown_lines(markdown_text)
        if not getattr(config, "OCR_MISTRAL_CLEAN_MARKDOWN_FALLBACK", True):
            return lines

        cleaned_lines = []
        for line in lines:
            normalized_line = cls._strip_markdown_prefix(line)
            if normalized_line:
                cleaned_lines.append(normalized_line)
        return cleaned_lines

    @staticmethod
    def _strip_markdown_prefix(line: str) -> str:
        """Remove markdown list and heading markers from fallback OCR text."""
        normalized_line = str(line).strip()
        if not normalized_line:
            return ""

        # Drop markdown table rows and separator lines entirely
        if normalized_line.startswith("|"):
            return ""

        normalized_line = re.sub(r"^#{1,6}\s+", "", normalized_line)
        normalized_line = re.sub(r"^>\s+", "", normalized_line)
        normalized_line = re.sub(r"^[-*+]\s+", "", normalized_line)
        normalized_line = re.sub(r"^\d+[.)]\s+", "", normalized_line)
        return normalized_line.strip()

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
