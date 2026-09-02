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
            "You are an expert OCR and data entry assistant. Analyze the provided image of an Egyptian Tax Card.\n"
            "Extract the following fields accurately:\n"
            "- company_name: The name of the company or taxpayer (usually in Arabic).\n"
            "- tax_registration_number: The 9-digit tax registration number (e.g., 123-456-789 or 123456789). Look carefully for numbers.\n\n"
            "If a field is not readable, leave its value as an empty string.\n"
            "Respond ONLY with a JSON object containing the exact keys 'company_name' and 'tax_registration_number'."
        )
    else:
        prompt = (
            "Extract all the text from the provided image accurately.\n\n"
            "Respond ONLY with a JSON object containing a single key 'extracted_text'."
        )
        
    return _call_openai_with_retry(prompt, base64_image)
