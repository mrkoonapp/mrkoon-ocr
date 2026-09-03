import os
import time
import glob

# Try importing the local engine
from ocr_engine import extract_text_from_image
from parsers import parse_egyptian_tax_card
import asyncio

async def run_local_test():
    images = glob.glob("test_image*.*")
    images.sort()
    
    print(f"Testing {len(images)} images LOCALLY with python method...\n")
    print("-" * 125)
    print(f"{'Image':<18} | {'Is Tax Card?':<12} | {'Time(s)':<8} | {'Tax Number':<15} | {'Company Name':<40}")
    print("-" * 125)
    
    for img_path in images:
        try:
            start_time = time.time()
            
            with open(img_path, "rb") as f:
                image_bytes = f.read()
                
            raw_text = extract_text_from_image(image_bytes)
            parsed_data = parse_egyptian_tax_card(raw_text)
            
            end_time = time.time()
            duration = end_time - start_time
            
            company = parsed_data.get("company_name", "")
            tax_num = parsed_data.get("tax_registration_number", "")
            
            is_tax_card = "Yes" if tax_num or company else "No"
            
            company = (company[:37] + '...') if len(company) > 40 else company
            if not company: company = "N/A"
            if not tax_num: tax_num = "N/A"
            
            print(f"{img_path:<18} | {is_tax_card:<12} | {duration:<8.2f} | {tax_num:<15} | {company:<40}")
            
        except Exception as e:
            print(f"{img_path:<18} | Exception    | N/A      | N/A             | {str(e)[:40]}")

if __name__ == "__main__":
    asyncio.run(run_local_test())
