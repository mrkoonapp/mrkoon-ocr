from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional

from ocr_engine import extract_text_from_image
from parsers import parse_egyptian_tax_card

app = FastAPI(title="MrKoon OCR Service")

@app.post("/extract")
async def extract_document(
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        image_bytes = await file.read()
        
        # 1. Extract raw text
        raw_text = extract_text_from_image(image_bytes)
        
        # 2. Parse based on document type
        if document_type == 'egyptian_tax_card':
            parsed_data = parse_egyptian_tax_card(raw_text)
            return JSONResponse(content=parsed_data)
        else:
            # Default fallback
            return JSONResponse(content={"extracted_text": raw_text})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
