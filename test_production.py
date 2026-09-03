import os
import requests
import glob
import time

def test_images(api_url):
    images = glob.glob("test_image*.*")
    images.sort()
    
    print(f"Testing {len(images)} images against {api_url}...\n")
    print(f"{'Image':<18} | {'Method':<6} | {'Time(s)':<7} | {'Company Name':<30} | {'Tax Number':<15}")
    print("-" * 80)
    
    for img_path in images:
        for method in ["ai", "python", "stdnum"]:
            try:
                with open(img_path, "rb") as f:
                    files = {"file": (img_path, f, "image/jpeg")}
                    data = {"document_type": "egyptian_tax_card", "method": method}
                    start_time = time.time()
                    response = requests.post(api_url, data=data, files=files)
                    
                if response.status_code == 200:
                    duration = time.time() - start_time
                    res_json = response.json()
                    
                    if method == "stdnum":
                        tax_num = res_json.get("tax_registration_number", "N/A")
                        is_valid = res_json.get("is_valid_egyptian_tax_number", False)
                        valid_str = "VALID" if is_valid else "INVALID"
                        print(f"{img_path:<18} | {method:<6} | {duration:<7.2f} | Stdnum Check: {valid_str:<16} | {tax_num:<15}")
                    else:
                        company = res_json.get("company_name", "N/A")
                        if company is None:
                            company = "N/A"
                        tax_num = res_json.get("tax_registration_number", "N/A")
                        if tax_num is None:
                            tax_num = "N/A"
                        
                        # Truncate strings for formatting
                        company = (company[:27] + '...') if len(company) > 30 else company
                        tax_num = (tax_num[:12] + '...') if len(tax_num) > 15 else tax_num
                        
                        print(f"{img_path:<18} | {method:<6} | {duration:<7.2f} | {company:<30} | {tax_num:<15}")
                else:
                    duration = time.time() - start_time
                    print(f"{img_path:<18} | {method:<6} | {duration:<7.2f} | Error {response.status_code}: {response.text[:20]:<15} | N/A")
                    
            except Exception as e:
                print(f"{img_path:<18} | {method:<6} | Exception: {str(e)[:20]:<19} | N/A")
                
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_images(sys.argv[1])
    else:
        print("Usage: python test_production.py <API_URL>")
