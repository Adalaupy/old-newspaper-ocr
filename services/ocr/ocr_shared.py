"""
Shared OCR utilities used by OCR engines.
"""
import base64
import io

from PIL import Image
from PIL import ImageOps

import config


def initialize_opencc_converter():
    """Initialize OpenCC converter for final Traditional Chinese output."""
    if not config.OCR_ENFORCE_TRADITIONAL_CHINESE:
        return None

    try:
        from opencc import OpenCC
    except Exception:
        print("OpenCC is not available; OCR output will not be converted to Traditional Chinese")
        return None

    try:
        return OpenCC(config.OCR_TRADITIONAL_CONVERSION)
    except Exception as e:
        print(f"Failed to initialize OpenCC converter: {e}")
        return None


def ensure_traditional_chinese(text: str, converter) -> str:
    """Convert OCR text to Traditional Chinese when configured and available."""
    if not text:
        return text

    if not config.OCR_ENFORCE_TRADITIONAL_CHINESE:
        return text

    if converter is None:
        return text

    try:
        return converter.convert(text)
    except Exception:
        return text


def build_png_data_url(image: Image.Image) -> str:
    """Convert a PIL image to a lossless PNG data URL."""
    normalized_image = ImageOps.exif_transpose(image)
    buffer = io.BytesIO()
    normalized_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def split_markdown_lines(markdown_text: str, ignored_prefixes: tuple[str, ...] = ("![img-", "[tbl-")) -> list:
    """Split markdown into clean text lines and skip placeholder prefixes."""
    lines = []
    for line in str(markdown_text).splitlines():
        normalized_line = line.strip()
        if not normalized_line:
            continue
        if any(normalized_line.startswith(prefix) for prefix in ignored_prefixes):
            continue
        # Skip markdown table rows (| cell | cell |) and separator lines (| --- |)
        if normalized_line.startswith("|"):
            continue
        lines.append(normalized_line)
    return lines
