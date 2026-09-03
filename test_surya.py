import time
from PIL import Image
import sys

print("Loading Surya models...")
t0 = time.time()
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
print(f"Models loaded in {time.time() - t0:.2f}s")

def test_surya(img_path):
    print(f"Testing {img_path}...")
    img = Image.open(img_path)
    
    t1 = time.time()
    predictions = run_ocr([img], [['ar']], det_model, det_processor, rec_model, rec_processor)
    print(f"OCR Time: {time.time() - t1:.2f}s")
    
    res = predictions[0]
    for line in res.text_lines:
        print(f"[{line.confidence:.2f}] {line.text}")

if __name__ == "__main__":
    test_surya("test_image.jpeg")
