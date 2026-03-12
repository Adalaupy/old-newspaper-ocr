"""
Shared OCR post-processing utilities used by all OCR engines.
"""
import numpy as np

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


def format_text_by_direction(ocr_result: list, direction: str) -> str:
    """
    Format normalized OCR lines into final multi-line text by reading direction.

    Expected input schema for ocr_result:
    [ [box, [text, confidence]], ... ]
    where box is a list of [x, y] points.
    """
    if not ocr_result:
        return ""

    text_boxes = []
    for line in ocr_result:
        if not isinstance(line, (list, tuple)) or len(line) < 2:
            continue

        box = line[0]
        text_info = line[1]
        if not isinstance(text_info, (list, tuple)) or len(text_info) < 1:
            continue

        text = "" if text_info[0] is None else str(text_info[0]).strip()
        try:
            confidence = float(text_info[1]) if len(text_info) > 1 else 0.0
        except (TypeError, ValueError):
            confidence = 0.0

        if not text or confidence < config.OCR_UNKNOWN_CONFIDENCE:
            text = config.OCR_UNKNOWN_TOKEN

        if not isinstance(box, (list, tuple)):
            continue

        points = []
        for point in box:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                continue

        if not points:
            continue

        x_coords = [point[0] for point in points]
        y_coords = [point[1] for point in points]

        text_boxes.append(
            {
                "text": text,
                "x": sum(x_coords) / len(x_coords),
                "y": sum(y_coords) / len(y_coords),
                "confidence": confidence,
                "width": max(x_coords) - min(x_coords),
                "height": max(y_coords) - min(y_coords),
            }
        )

    if not text_boxes:
        return ""

    if direction == "vertical_rtl":
        text_boxes.sort(key=lambda b: (-b["x"], b["y"]))
    elif direction == "vertical_ltr":
        text_boxes.sort(key=lambda b: (b["x"], b["y"]))
    elif direction == "horizontal_ltr":
        text_boxes.sort(key=lambda b: (b["y"], b["x"]))
    elif direction == "horizontal_rtl":
        text_boxes.sort(key=lambda b: (b["y"], -b["x"]))

    recognized_tokens = insert_gap_unknown_tokens(text_boxes, direction)
    return "\n".join(recognized_tokens)


def insert_gap_unknown_tokens(text_boxes: list, direction: str) -> list:
    """Insert [UNK] when spacing suggests a likely missing word."""
    if not text_boxes:
        return []

    if not config.OCR_GAP_UNKNOWN_ENABLED:
        return [box["text"] for box in text_boxes]

    widths = [max(1.0, float(box.get("width", 1.0))) for box in text_boxes]
    heights = [max(1.0, float(box.get("height", 1.0))) for box in text_boxes]
    median_width = float(np.median(widths))
    median_height = float(np.median(heights))

    same_row_tol = max(2.0, median_height * config.OCR_SAME_LINE_TOLERANCE)
    same_col_tol = max(2.0, median_width * config.OCR_SAME_LINE_TOLERANCE)
    horizontal_gap_thresh = max(median_width * config.OCR_GAP_FACTOR, median_width + 5.0)
    vertical_gap_thresh = max(median_height * config.OCR_GAP_FACTOR, median_height + 5.0)

    tokens = []
    prev = None
    for box in text_boxes:
        if prev is not None:
            missing_gap = False
            if direction in ("horizontal_ltr", "horizontal_rtl"):
                same_line = abs(box["y"] - prev["y"]) <= same_row_tol
                gap = abs(box["x"] - prev["x"])
                if same_line and gap > horizontal_gap_thresh:
                    missing_gap = True
            else:
                same_line = abs(box["x"] - prev["x"]) <= same_col_tol
                gap = abs(box["y"] - prev["y"])
                if same_line and gap > vertical_gap_thresh:
                    missing_gap = True

            if missing_gap:
                tokens.append(config.OCR_UNKNOWN_TOKEN)

        tokens.append(box["text"])
        prev = box

    return tokens


def normalize_polygon_points(points_data) -> list:
    """Normalize polygon points into [[x, y], ...] float format."""
    if isinstance(points_data, np.ndarray):
        points_iterable = points_data.tolist()
    elif isinstance(points_data, (list, tuple)):
        points_iterable = list(points_data)
    else:
        return []

    normalized = []
    for point in points_iterable:
        if isinstance(point, np.ndarray):
            point = point.tolist()
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            normalized.append([float(point[0]), float(point[1])])
        except (TypeError, ValueError):
            continue

    return normalized


def to_float(value, default: float = 0.0) -> float:
    """Convert value to float with a fallback default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default