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
    
    # readtext returns a list of tuples: (bbox, text, confidence)
    result = reader.readtext(img)
    
    # We extract the text parts and join them with newlines
    extracted_lines = [res[1] for res in result]
    full_text = "\n".join(extracted_lines)
    
    return full_text
