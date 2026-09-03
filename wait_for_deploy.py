import requests
import time
import sys

API_URL = "https://mrkoon-ocr-production.up.railway.app/extract"

print("Waiting for deployment to complete...")
for i in range(30): # 30 attempts, 10 seconds each = 5 minutes
    try:
        with open("test_image.jpeg", "rb") as f:
            files = {"file": ("test_image.jpeg", f, "image/jpeg")}
            data = {"document_type": "egyptian_tax_card", "method": "python"}
            response = requests.post(API_URL, data=data, files=files)
            
            if response.status_code == 200:
                print(f"\nDeployment successful! Received 200 OK: {response.text[:100]}")
                sys.exit(0)
            else:
                print(f"Server returned {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"Request failed: {e}")
        
    time.sleep(10)

print("\nDeployment didn't succeed within expected time.")
sys.exit(1)
