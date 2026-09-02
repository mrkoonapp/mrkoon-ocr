import time
import sys

# Test the OCR engine
print("Loading PaddleOCR (first load downloads models)...")
t0 = time.time()
from ocr_engine import extract_text_from_image
from parsers import parse_egyptian_tax_card
print(f"Module load time: {time.time() - t0:.1f}s\n")

test_file = sys.argv[1] if len(sys.argv) > 1 else "test_image.jpeg"

with open(test_file, "rb") as f:
    image_bytes = f.read()

print("Warming up model (first predict is slower)...")
_ = extract_text_from_image(image_bytes)

print(f"\nTesting: {test_file} (Warm Model)")
print("=" * 60)

# Time the extraction
t1 = time.time()
raw_text = extract_text_from_image(image_bytes)
ocr_time = time.time() - t1

print(f"OCR time: {ocr_time:.2f}s")
print(f"\n--- Raw OCR Text ---")
print(raw_text)

# Time the parsing
t2 = time.time()
result = parse_egyptian_tax_card(raw_text)
parse_time = time.time() - t2

print(f"\n--- Parsed Result ---")
print(f"  company_name:            {result['company_name']}")
print(f"  tax_registration_number: {result['tax_registration_number']}")
print(f"\nParse time: {parse_time:.4f}s")
print(f"Total time: {ocr_time + parse_time:.2f}s")
print(f"Under 10s?  {'✅ YES' if (ocr_time + parse_time) < 10 else '❌ NO'}")
