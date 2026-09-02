import logging
import numpy as np
import cv2
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# Try to import arabic_reshaper for proper character connection
try:
    import arabic_reshaper
    _HAS_RESHAPER = True
except ImportError:
    _HAS_RESHAPER = False
    logger.warning("arabic-reshaper not installed — Arabic characters may appear disconnected")

# ──────────────────────────────────────────────
# PaddleOCR singleton — models load once at startup
# use_angle_cls=True detects rotated text automatically
# ──────────────────────────────────────────────
_ocr = PaddleOCR(
    use_angle_cls=True,
    lang='ar',
    use_gpu=False,
    show_log=False,
)


def _preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Light preprocessing tuned for Egyptian tax cards
    (gold/holographic surface, printed Arabic, Eastern Arabic numerals).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    h, w = img.shape[:2]

    # Upscale small images so OCR has enough detail
    if w < 1000:
        scale = 1000 / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    # Downscale very large images to stay within the 10-second budget
    elif w > 3000:
        scale = 2000 / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Convert to grayscale for contrast enhancement
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE — handles uneven lighting / reflective gold card surfaces
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Light sharpening to crisp up printed text
    kernel = np.array([[0, -1, 0],
                       [-1,  5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)

    return sharpened


def _reshape_arabic(text: str) -> str:
    """Connect isolated Arabic characters output by OCR (ا س م → اسم)."""
    if _HAS_RESHAPER and text:
        try:
            return arabic_reshaper.reshape(text)
        except Exception:
            pass
    return text


def _group_into_lines(results: list) -> list[str]:
    """
    Takes PaddleOCR result list and groups text segments into
    reading-order lines (top→bottom, right→left within each line).
    """
    if not results:
        return []

    items = []
    for item in results:
        bbox = item[0]          # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        text = item[1][0]       # recognised text
        conf = item[1][1]       # confidence

        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_right  = max(p[0] for p in bbox)
        text_h   = abs(bbox[2][1] - bbox[0][1])
        items.append({
            'y': y_center,
            'x': x_right,
            'text': text,
            'conf': conf,
            'h': text_h,
        })

    # Sort top → bottom
    items.sort(key=lambda i: i['y'])

    # Adaptive line-height threshold
    avg_h = sum(i['h'] for i in items) / len(items) if items else 20
    threshold = avg_h * 0.6

    lines: list[str] = []
    cur_line = [items[0]]

    for item in items[1:]:
        if abs(item['y'] - cur_line[0]['y']) < threshold:
            cur_line.append(item)
        else:
            # Within a line, sort right → left (Arabic reading order)
            cur_line.sort(key=lambda i: i['x'], reverse=True)
            lines.append(" ".join(i['text'] for i in cur_line))
            cur_line = [item]

    cur_line.sort(key=lambda i: i['x'], reverse=True)
    lines.append(" ".join(i['text'] for i in cur_line))

    return lines


# ──────────────────────────────────────────────
# Public API — signature stays the same so main.py
# doesn't need changes
# ──────────────────────────────────────────────
def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Takes raw image bytes, preprocesses, runs PaddleOCR, and returns
    the full extracted text (one line per detected text row).
    """
    processed = _preprocess(image_bytes)

    results = _ocr.ocr(processed, cls=True)

    if not results or not results[0]:
        logger.warning("PaddleOCR returned no results")
        return ""

    lines = _group_into_lines(results[0])

    # Reshape Arabic characters for proper connection
    lines = [_reshape_arabic(line) for line in lines]

    full_text = "\n".join(lines)
    logger.info(f"PaddleOCR extracted {len(lines)} lines")
    return full_text
