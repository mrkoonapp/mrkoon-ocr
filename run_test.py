import os
import requests
import glob
import time

API_URL = "https://mrkoon-ocr-production.up.railway.app/extract"
images = glob.glob("test_image*.*")
images.sort()

def run_test(method, img_path):
    with open(img_path, "rb") as f:
        files = {"file": (img_path, f, "image/jpeg")}
        data = {"document_type": "egyptian_tax_card", "method": method}
        start_time = time.time()
        response = requests.post(API_URL, data=data, files=files)
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            res_json = response.json()
            company = res_json.get("company_name", "")
            tax_num = res_json.get("tax_registration_number", "")
            
            is_tax_card = "Yes" if tax_num or company else "No"
            
            return duration, is_tax_card, company, tax_num
        else:
            return duration, "Error", "Error", "Error"

print(f"Testing {len(images)} images against {API_URL}...\n")
print("-" * 125)
print(f"{'Image':<18} | {'Method':<6} | {'Is Tax Card?':<12} | {'Time(s)':<8} | {'Tax Number':<15} | {'Company Name':<40}")
print("-" * 125)

for img_path in images:
    for method in ["ai", "python"]:
        try:
            duration, is_tax_card, company, tax_num = run_test(method, img_path)
            
            company = (company[:37] + '...') if len(company) > 40 else company
            if not company: company = "N/A"
            if not tax_num: tax_num = "N/A"
            
            print(f"{img_path:<18} | {method:<6} | {is_tax_card:<12} | {duration:<8.2f} | {tax_num:<15} | {company:<40}")
        except Exception as e:
            print(f"{img_path:<18} | {method:<6} | Exception    | N/A      | N/A             | {str(e)[:40]}")
