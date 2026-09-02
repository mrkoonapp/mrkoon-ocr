from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional

from ocr_engine import extract_text_from_image
from parsers import parse_egyptian_tax_card
from openai_engine import process_document_with_ai

from fastapi.concurrency import run_in_threadpool

app = FastAPI(title="MrKoon OCR Service")

@app.post("/extract")
async def extract_document(
    document_type: str = Form(...),
    method: str = Form("python"),
    file: UploadFile = File(...)
):
    try:
        image_bytes = await file.read()
        
        if method == "ai":
            parsed_data = await run_in_threadpool(process_document_with_ai, image_bytes, document_type)
            return JSONResponse(content=parsed_data)
        elif method == "python":
            # 1. Extract raw text
            raw_text = await run_in_threadpool(extract_text_from_image, image_bytes)
            
            # 2. Parse based on document type
            if document_type == 'egyptian_tax_card':
                parsed_data = parse_egyptian_tax_card(raw_text)
                return JSONResponse(content=parsed_data)
            else:
                # Default fallback
                return JSONResponse(content={"extracted_text": raw_text})
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid method. Choose 'ai' or 'python'."})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
