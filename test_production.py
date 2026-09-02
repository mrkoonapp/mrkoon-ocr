import os
import requests
import glob
import time

def test_images(api_url):
    images = glob.glob("test_image*.*")
    images.sort()
    
    print(f"Testing {len(images)} images against {api_url}...\n")
    print(f"{'Image':<18} | {'Method':<6} | {'Company Name':<30} | {'Tax Number':<15}")
    print("-" * 80)
    
    for img_path in images:
        for method in ["ai", "python"]:
            try:
                with open(img_path, "rb") as f:
                    files = {"file": (img_path, f, "image/jpeg")}
                    data = {"document_type": "egyptian_tax_card", "method": method}
                    start_time = time.time()
                    response = requests.post(api_url, data=data, files=files)
                    
                if response.status_code == 200:
                    res_json = response.json()
                    company = res_json.get("company_name", "N/A")
                    tax_num = res_json.get("tax_registration_number", "N/A")
                    
                    # Truncate strings for formatting
                    company = (company[:27] + '...') if len(company) > 30 else company
                    tax_num = (tax_num[:12] + '...') if len(tax_num) > 15 else tax_num
                    
                    print(f"{img_path:<18} | {method:<6} | {company:<30} | {tax_num:<15}")
                else:
                    print(f"{img_path:<18} | {method:<6} | Error {response.status_code:<24} | N/A")
                    
            except Exception as e:
                print(f"{img_path:<18} | {method:<6} | Exception: {str(e)[:20]:<19} | N/A")
                
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_images(sys.argv[1])
    else:
        print("Usage: python test_production.py <API_URL>")
