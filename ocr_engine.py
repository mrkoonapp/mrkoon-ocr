import os
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
import logging
import numpy as np
import cv2
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# PaddleOCR singleton — models load once at startup
#
# Performance tuning for <10s per request:
#   - use_doc_orientation_classify=False  → skip full-document rotation
#   - use_doc_unwarping=False             → skip document dewarping
#   - use_textline_orientation=False      → skip per-line rotation (saves ~2s)
#   - text_detection_model_name='PP-OCRv5_mobile_det' → fast mobile detector
#   - device='cpu'
# ──────────────────────────────────────────────
# PaddleOCR singleton — models load once at startup
#
# Performance tuning for <1s per request on CPU:
# ──────────────────────────────────────────────
_ocr = PaddleOCR(
    use_textline_orientation=False,   # Skips text orientation classifier
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    text_detection_model_name='PP-OCRv5_mobile_det',
    text_recognition_model_name='arabic_PP-OCRv5_mobile_rec',
    lang='ar',
    device='cpu',                     # Enforce explicit CPU processing (v3.7 API)
    enable_mkldnn=False,              # Disable MKLDNN to prevent OneDNN crash on Linux
)


def _preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Light preprocessing tuned for Egyptian tax cards
    (gold/holographic surface, printed Arabic, Eastern Arabic numerals).
    Returns a 3-channel color image required by PaddleOCR.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    h, w = img.shape[:2]

    # Force a small target width to achieve extreme CPU performance (<2s)
    target_w = 900
    if w != target_w:
        scale = target_w / w
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)

    # Convert to grayscale for contrast enhancement
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE on L channel of LAB color space — counters plastic card reflections
    # (using grayscale directly as it was proven to yield better text recognition)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # PaddleOCR 3.7 requires a 3-channel image
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _group_into_lines(texts: list[str], scores: list[float], polys: list) -> list[str]:
    """
    Groups OCR text segments into clean reading-order lines
    (top→bottom, right→left within each line for Arabic).
    """
    if not texts:
        return []

    items = []
    for text, score, poly in zip(texts, scores, polys):
        # Filter low confidence blocks (0.65 threshold prevents card background pattern extraction)
        if score < 0.65:
            continue

        poly_list = poly.tolist() if hasattr(poly, 'tolist') else poly
        y_center = (poly_list[0][1] + poly_list[2][1]) / 2.0
        x_right  = max(p[0] for p in poly_list)
        text_h   = abs(poly_list[2][1] - poly_list[0][1])

        items.append({
            'y': y_center,
            'x': x_right,
            'text': text,
            'conf': score,
            'h': text_h,
        })

    if not items:
        return []

    # Sort strictly from top to bottom first
    items.sort(key=lambda i: i['y'])

    # Dynamic line-height separation threshold
    avg_h = sum(i['h'] for i in items) / len(items)
    threshold = avg_h * 0.5

    lines: list[str] = []
    cur_line = [items[0]]

    for item in items[1:]:
        if abs(item['y'] - cur_line[0]['y']) < threshold:
            cur_line.append(item)
        else:
            # Sort elements inside the same horizontal line from Right to Left
            cur_line.sort(key=lambda i: i['x'], reverse=True)
            lines.append(" ".join(i['text'] for i in cur_line))
            cur_line = [item]

    # Handle trailing line
    cur_line.sort(key=lambda i: i['x'], reverse=True)
    lines.append(" ".join(i['text'] for i in cur_line))

    return lines


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Takes raw image bytes, preprocesses, runs PaddleOCR, and returns
    the full extracted text (one line per detected text row).
    """
    processed = _preprocess(image_bytes)

    # PaddleOCR 3.7 API uses predict() instead of ocr()
    results = list(_ocr.predict(processed))

    if not results:
        logger.warning("PaddleOCR returned no text results")
        return ""

    result = results[0]
    texts = result['rec_texts']
    scores = result['rec_scores']
    polys = result['dt_polys']

    lines = _group_into_lines(texts, scores, polys)
    full_text = "\n".join(lines)
    
    logger.info(f"PaddleOCR extracted {len(lines)} lines successfully.")
    return full_text
