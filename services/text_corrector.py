"""
Shared text correction/postprocessing utilities for OCR engines
"""
from functools import lru_cache

import config


@lru_cache(maxsize=1)
def _load_pycorrector():
    """Lazy-load pycorrector on first use."""
    try:
        import pycorrector
        return pycorrector
    except Exception:
        return None


def correct_ocr_text(text: str) -> str:
    """
    Post-correct OCR text with pycorrector when available and enabled.
    
    Args:
        text: Raw OCR text to correct
        
    Returns:
        Corrected text (or original if correction not available/enabled)
    """
    if not text:
        return text

    if not config.OCR_PYCORRECTOR_ENABLED:
        return text
    
    pycorrector = _load_pycorrector()
    if pycorrector is None:
        return text

    corrected_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            corrected_lines.append(line)
            continue

        if config.OCR_PYCORRECTOR_SKIP_UNKNOWN and config.OCR_UNKNOWN_TOKEN in stripped:
            corrected_lines.append(line)
            continue

        try:
            corrected_line, _ = pycorrector.correct(stripped)
            corrected_lines.append(corrected_line if corrected_line else line)
        except Exception:
            corrected_lines.append(line)

    return '\n'.join(corrected_lines)


