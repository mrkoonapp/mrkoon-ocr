import os
import base64
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

with open("test_image2.jpg", "rb") as f:
    base64_image = base64.b64encode(f.read()).decode('utf-8')

prompt = """You are an expert OCR and data entry assistant. Analyze the provided image to determine if it is an Egyptian Tax Card (بطاقة ضريبية).
FIRST, check if the image is actually a Tax Card. If it is a National ID (بطاقة تحقيق شخصية / بطاقة رقم قومي) or any other document, you MUST return empty strings for all fields.
If it IS a Tax Card, extract the following fields accurately:
- company_name: The name of the company or taxpayer (usually in Arabic). Do NOT return the country name ('جمهورية مصر العربية') or government department headers ('وزارة المالية', 'مصلحة الضرائب', etc.). The company name is usually below these headers. Note that the card might be rotated (e.g. rounded corners to the left or right) or upside down. Please read the text regardless of orientation, look carefully for keywords like 'اسم الممول' or 'اسم الشركة' and extract the name next to or below it.
- tax_registration_number: The tax registration number. It ALWAYS has EXACTLY 9 digits, typically separated by '-' for each 3 digits. It is located on the lower right side of the card, just above the bottom decorative border. VERY IMPORTANT: Do NOT extract the long 14-digit or 16-digit standard number (Western digits 0-9) located on the bottom left (that is a barcode/registration number, not the tax number). Only extract the 9-digit sequence on the right. Write it EXACTLY as it appears in the image, using the original Eastern Arabic numerals (e.g. ٥٨٢-٣٤٤-٥٧٢). DO NOT convert or translate them to Western digits (0-9).

If a field is not readable or the document is not a tax card, leave its value as an empty string.
Respond ONLY with a JSON object containing the exact keys 'company_name' and 'tax_registration_number'."""

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
            ]
        }
    ],
    response_format={ "type": "json_object" },
    temperature=0.0
)

print(response.choices[0].message.content)
