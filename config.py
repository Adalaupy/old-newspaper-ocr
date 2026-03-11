"""
Configuration file for OCR application
"""

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
CROP_RECT_COLOR = "red"
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
OCR_USE_GPU = False
OCR_LANG = "ch"  # PaddleOCR language code for traditional Chinese
OCR_DROP_SCORE = 0.05  # Keep more low-confidence candidates to reduce missed words
OCR_DET_DB_THRESH = 0.2  # Lower text detection threshold for faint newspaper print
OCR_DET_DB_BOX_THRESH = 0.35  # Lower box confidence threshold to keep weak text boxes
OCR_UNKNOWN_TOKEN = "[UNK]"  # Placeholder for words that cannot be recognized
OCR_UNKNOWN_CONFIDENCE = 0.35  # Mark low-confidence words as unknown
OCR_PYCORRECTOR_ENABLED = True  # Use pycorrector to post-correct OCR text
OCR_PYCORRECTOR_SKIP_UNKNOWN = True  # Skip correction when [UNK] appears in a line
OCR_GAP_UNKNOWN_ENABLED = True  # Insert unknown marker when a likely word gap is detected
OCR_GAP_FACTOR = 1.9  # Gap ratio threshold for missing-word heuristic
OCR_SAME_LINE_TOLERANCE = 0.7  # Line/column grouping tolerance ratio

# Processing
MAX_CONCURRENT_PROCESSES = 3
