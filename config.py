"""
Configuration file for OCR application
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Keep configuration import-safe even when python-dotenv is unavailable.
    pass

# Supported languages for OCR
SUPPORTED_LANGUAGES = {
    "Traditional Chinese": "ch",
    "Simplified Chinese": "chinese_cht",
    "English": "en",
}

# Reading directions
READ_DIRECTIONS = {
    "Vertical Right-to-Left (Traditional)": "vertical_rtl",
    "Vertical Left-to-Right": "vertical_ltr",
    "Horizontal Left-to-Right": "horizontal_ltr",
    "Horizontal Right-to-Left": "horizontal_rtl",
}

# Default settings
DEFAULT_READ_DIRECTION = "vertical_rtl"
DEFAULT_LANGUAGE = "Traditional Chinese"

# UI Settings
WINDOW_TITLE = "Old Newspaper OCR"
WINDOW_SIZE = "1400x900"
CANVAS_BG_COLOR = "#2b2b2b"
CROP_RECT_COLOR = "blue"
CROP_RECT_WIDTH = 2
SELECTED_CROP_COLOR = "yellow"

# Image settings
MAX_DISPLAY_WIDTH = 1000
MAX_DISPLAY_HEIGHT = 800
ZOOM_FACTOR = 1.2
ROTATION_ANGLE = 90  # degrees

# File settings
DEFAULT_FILENAME_FORMAT = "%Y%m%d_{id}"
OUTPUT_FOLDER = "output"
SUPPORTED_IMAGE_FORMATS = [
    ("Image files", "*.png *.jpg *.jpeg *.tiff *.bmp"),
    ("PDF files", "*.pdf"),
    ("All files", "*.*")
]

# OCR settings
# OCR engine module name under services/ocr/, e.g. "ocr_engine_paddle" -> services/ocr/ocr_engine_paddle.py
OCR_ENGINE = "ocr_engine_mistral"
# Backward-compatible alias for typo usage.
ORC_ENGINE = OCR_ENGINE
OCR_ENGINE_OPTIONS = {
    "PaddleOCR": "ocr_engine_paddle",
    "EasyOCR": "ocr_engine_easyocr",
    "Mistral OCR": "ocr_engine_mistral",
}

OCR_USE_GPU = False
OCR_LANG = "ch"  # PaddleOCR language code for traditional Chinese
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
OCR_MISTRAL_MODEL = "mistral-ocr-latest"
OCR_MISTRAL_INCLUDE_IMAGE_BASE64 = True
OCR_MISTRAL_LANGUAGE_HINT_ENABLED = True
OCR_MISTRAL_LANGUAGE_HINT = ""  # Optional override, e.g. "Traditional Chinese"
OCR_DROP_SCORE = 0  # Keep more low-confidence candidates to reduce missed words
OCR_DET_DB_THRESH = 0.2  # Lower text detection threshold for faint newspaper print
OCR_DET_DB_BOX_THRESH = 0.35  # Lower box confidence threshold to keep weak text boxes
OCR_ENFORCE_TRADITIONAL_CHINESE = True  # Always convert final OCR output to traditional Chinese
OCR_TRADITIONAL_CONVERSION = "s2t"  # OpenCC conversion profile (simplified to traditional)
OCR_UNKNOWN_TOKEN = "[UNK]"  # Placeholder for words that cannot be recognized
OCR_UNKNOWN_CONFIDENCE = 0  # Mark low-confidence words as unknown (0 = disabled)
OCR_PYCORRECTOR_ENABLED = True  # Use pycorrector to post-correct OCR text
OCR_PYCORRECTOR_SKIP_UNKNOWN = True  # Skip correction when [UNK] appears in a line
OCR_GAP_UNKNOWN_ENABLED = False  # Insert unknown marker when a likely word gap is detected
OCR_GAP_FACTOR = 1.9  # Gap ratio threshold for missing-word heuristic
OCR_SAME_LINE_TOLERANCE = 0.5 # Line/column grouping tolerance ratio

# Processing
MAX_CONCURRENT_PROCESSES = 3
