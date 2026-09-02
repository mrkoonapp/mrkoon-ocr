import easyocr
import numpy as np
import cv2

# Initialize the reader for Arabic and English
reader = easyocr.Reader(['ar', 'en'], gpu=False)

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Takes raw image bytes, converts to cv2 image, and extracts text using EasyOCR.
    Returns the joined text.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocessing to improve OCR accuracy
    # Resize to 2x scale
    width = int(img.shape[1] * 2)
    height = int(img.shape[0] * 2)
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # Convert to grayscale
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    
    # readtext with detail=1, contrast adjusting
    result = reader.readtext(gray, detail=1, paragraph=False, contrast_ths=0.1, adjust_contrast=0.5)
    
    # We extract the text parts and join them with newlines
    extracted_lines = [res[1] for res in result]
    full_text = "\n".join(extracted_lines)
    
    return full_text
