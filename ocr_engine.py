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
_ocr = PaddleOCR(
    use_textline_orientation=True,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    text_detection_model_name='PP-OCRv5_server_det',
    text_recognition_model_name='arabic_PP-OCRv5_mobile_rec',
    lang='ar',
    device='cpu',
)


def _preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Light preprocessing tuned for Egyptian tax cards
    (gold/holographic surface, printed Arabic, Eastern Arabic numerals).
    Returns a 3-channel color image (required by PaddleOCR 3.7 pipeline).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    h, w = img.shape[:2]

    # Force resize to 1200px width to ensure fast inference (<10s)
    # even with the more accurate server_det model
    target_w = 1200
    if w != target_w:
        scale = target_w / w
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)

    # CLAHE on L channel of LAB color space — enhances contrast
    # while keeping the 3-channel format PaddleOCR 3.7 requires
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_ch = clahe.apply(l_ch)
    enhanced = cv2.merge([l_ch, a_ch, b_ch])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    return enhanced


def _group_into_lines(texts: list[str], scores: list[float], polys: list) -> list[str]:
    """
    Groups OCR text segments into reading-order lines
    (top→bottom, right→left within each line).

    Uses PaddleOCR 3.7 result format: rec_texts, rec_scores, dt_polys.
    Filters out low-confidence results.
    """
    if not texts:
        return []

    # Build items with position info, filter low confidence
    items = []
    for text, score, poly in zip(texts, scores, polys):
        if score < 0.4:
            continue  # Skip garbage detections

        # poly is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        poly_list = poly.tolist() if hasattr(poly, 'tolist') else poly
        y_center = (poly_list[0][1] + poly_list[2][1]) / 2
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

    Note: PaddleOCR 3.7 already outputs properly connected Arabic text,
    so no additional reshaping (arabic_reshaper) is needed.
    """
    processed = _preprocess(image_bytes)

    # PaddleOCR 3.7 uses predict() — returns OCRResult objects
    results = list(_ocr.predict(processed))

    if not results:
        logger.warning("PaddleOCR returned no results")
        return ""

    result = results[0]
    texts = result['rec_texts']
    scores = result['rec_scores']
    polys = result['dt_polys']

    lines = _group_into_lines(texts, scores, polys)

    full_text = "\n".join(lines)
    logger.info(f"PaddleOCR extracted {len(lines)} lines")
    return full_text
