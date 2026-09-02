import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Lazy load models so we don't crash startup if Surya isn't installed
det_processor, det_model = None, None
rec_model, rec_processor = None, None
_surya_loaded = False

def _load_surya():
    global det_processor, det_model, rec_model, rec_processor, _surya_loaded
    if not _surya_loaded:
        logger.info("Loading Surya OCR models...")
        from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
        from surya.model.recognition.model import load_model as load_rec_model
        from surya.model.recognition.processor import load_processor as load_rec_processor
        
        det_processor, det_model = load_det_processor(), load_det_model()
        rec_model, rec_processor = load_rec_model(), load_rec_processor()
        _surya_loaded = True
        logger.info("Surya OCR models loaded successfully.")

def extract_text_with_surya(image_bytes: bytes) -> str:
    """
    Extracts text using the highly-accurate Surya OCR engine.
    """
    _load_surya()
    from surya.ocr import run_ocr
    
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Run OCR (assuming Arabic language 'ar')
    predictions = run_ocr([img], [['ar']], det_model, det_processor, rec_model, rec_processor)
    
    if not predictions:
        logger.warning("Surya OCR returned no predictions.")
        return ""
        
    res = predictions[0]
    
    lines = []
    for line in res.text_lines:
        lines.append(line.text)
        
    full_text = "\n".join(lines)
    logger.info(f"Surya OCR extracted {len(lines)} lines.")
    return full_text
