import base64
import json
import os
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def process_document_with_ai(image_bytes: bytes, document_type: str) -> dict:
    """
    Takes raw image bytes, converts to base64, and extracts text/data using OpenAI Vision API.
    """
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    if document_type == 'egyptian_tax_card':
        prompt = (
            "Extract the following information from the provided Egyptian Tax Card image:\n"
            "- company_name\n"
            "- tax_registration_number (usually a 9-digit number, e.g., 123-456-789 or similar)\n\n"
            "Respond ONLY with a JSON object containing the keys 'company_name' and 'tax_registration_number'."
        )
    else:
        prompt = (
            "Extract all the text from the provided image.\n\n"
            "Respond ONLY with a JSON object containing a single key 'extracted_text'."
        )
        
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
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format={ "type": "json_object" }
    )
    
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except:
        return {"error": "Failed to parse JSON from AI response", "raw_response": content}
