"""
OCR Engine service using EasyOCR
"""
from PIL import Image
import numpy as np
import config
from services.ocr_base import BaseOCREngine
from services.ocr_shared import normalize_polygon_points
from services.ocr_shared import to_float

try:
    import easyocr
except ImportError:
    easyocr = None

class OCREngine(BaseOCREngine):
    """Handles OCR operations using EasyOCR"""

    def _initialize_engine(self):
        """Initialize EasyOCR reader"""
        if easyocr is None:
            raise ImportError("easyocr is not installed. Install it with: pip install easyocr")

        try:
            # Determine language codes for EasyOCR
            # config.OCR_LANG is typically "ch" for Chinese or "en" for English
            # EasyOCR uses language codes like 'ch_sim', 'ch_tra', 'en', etc.
            lang_code = config.OCR_LANG
            
            # Map common OCR language codes to EasyOCR language codes
            lang_map = {
                'ch': 'ch_sim',      # Simplified Chinese (default for "ch")
                'chinese': 'ch_sim',
                'chinese_cht': 'ch_tra',  # Traditional Chinese
                'en': 'en',
                'english': 'en',
            }
            
            easyocr_lang = lang_map.get(lang_code, 'ch_sim')
            
            # Initialize EasyOCR reader with GPU support if enabled
            gpu = config.OCR_USE_GPU
            self.reader = easyocr.Reader([easyocr_lang], gpu=gpu)
        except Exception as e:
            print(f"Error initializing EasyOCR engine: {e}")
            raise

    def _run_ocr(self, image: Image.Image):
        """Run EasyOCR and return raw backend result."""
        if self.reader is None:
            raise RuntimeError("OCR engine not initialized")

        img_array = np.array(image, dtype=np.uint8)
        return self.reader.readtext(img_array)

    def _normalize_ocr_result(self, results: list) -> list:
        """
        Normalize EasyOCR results to internal format: [ [box, [text, confidence]], ... ]
        
        EasyOCR returns: [(points, text, confidence), ...]
        """
        if not results:
            return []
        
        normalized = []
        for item in results:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            
            points = item[0]  # List of (x, y) tuples
            text = item[1]    # Recognized text
            confidence = item[2]  # Confidence score
            
            box = normalize_polygon_points(points)
            
            if not box:
                continue
            
            # Handle text
            if text is None:
                text = ""
            else:
                text = str(text).strip()
            
            # Handle confidence
            conf = to_float(confidence, 0.0)
            
            normalized.append([box, [text, conf]])
        
        return normalized

