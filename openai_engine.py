import base64
import json
import os
import time
from openai import OpenAI

_client = None

def get_openai_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please configure it to use the AI method.")
        _client = OpenAI(api_key=api_key)
    return _client

def _call_openai_with_retry(prompt: str, base64_image: str, retries: int = 3) -> dict:
    client = get_openai_client()
    last_error = None
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={ "type": "json_object" },
                max_tokens=1000,
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            if content is None:
                last_error = "AI returned empty content"
                continue
                
            parsed = json.loads(content)
            
            # If all expected extracted values are empty, we consider it a failed extraction and retry
            if parsed and all(v == "" or v is None for v in parsed.values()):
                last_error = "AI returned empty values for all fields"
                time.sleep(1)
                continue
                
            return parsed
            
        except Exception as e:
            last_error = str(e)
            time.sleep(1)
            
    return {"error": f"Failed after {retries} attempts. Last error: {last_error}"}

def process_document_with_ai(image_bytes: bytes, document_type: str) -> dict:
    """
    Takes raw image bytes, converts to base64, and extracts text/data using OpenAI Vision API.
    """
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    if document_type == 'egyptian_tax_card':
        prompt = (
            "You are an expert OCR and data entry assistant. Analyze the provided image to determine if it is an Egyptian Tax Card (بطاقة ضريبية).\n"
            "FIRST, check if the image is actually a Tax Card. If it is a National ID (بطاقة تحقيق شخصية / بطاقة رقم قومي) or any other document, you MUST return empty strings for all fields.\n"
            "If it IS a Tax Card, extract the following fields accurately:\n"
            "- company_name: The name of the company or taxpayer (usually in Arabic). Do NOT return the country name ('جمهورية مصر العربية') or government department headers ('وزارة المالية', 'مصلحة الضرائب', etc.). The company name is usually below these headers. Note that the card might be rotated (e.g. rounded corners to the left or right) or upside down. Please read the text regardless of orientation, look carefully for keywords like 'اسم الممول' or 'اسم الشركة' and extract the name next to or below it.\n"
            "- tax_registration_number: The tax registration number. It ALWAYS has EXACTLY 9 digits, formatted as 333-333-333 (separated by '-' for each 3 digits). It is located on the lower right side of the card, just above the bottom decorative border. VERY IMPORTANT: The number is usually written in Eastern Arabic numerals (١٢٣٤٥٦٧٨٩٠). You MUST translate them into standard Western digits (0-9) in your output format (e.g., 123-456-789). Do NOT extract the long 14-digit or 16-digit standard number (Western digits 0-9) located on the bottom left (that is a barcode/registration number, not the tax number). Only extract the 9-digit Arabic numeral sequence on the right.\n\n"
            "If a field is not readable or the document is not a tax card, leave its value as an empty string.\n"
            "Respond ONLY with a JSON object containing the exact keys 'company_name' and 'tax_registration_number'."
        )
    else:
        prompt = (
            "Extract all the text from the provided image accurately.\n\n"
            "Respond ONLY with a JSON object containing a single key 'extracted_text'."
        )
        
    return _call_openai_with_retry(prompt, base64_image)
