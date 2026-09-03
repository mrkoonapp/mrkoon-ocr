import os
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
import os
import time
import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Optional

from ocr_engine import extract_text_from_image
from parsers import parse_egyptian_tax_card
from openai_engine import process_document_with_ai

from fastapi.concurrency import run_in_threadpool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

async def cleanup_old_images():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    if now - os.path.getmtime(file_path) > SEVEN_DAYS_SECONDS:
                        os.remove(file_path)
                        logger.info(f"Deleted old image: {filename}")
        except Exception as e:
            logger.error(f"Error during cleanup of old images: {e}")
        
        # Wait 24 hours before running again
        await asyncio.sleep(24 * 60 * 60)

from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background task
    task = asyncio.create_task(cleanup_old_images())
    yield
    # Shutdown: Cancel background task
    task.cancel()

app = FastAPI(title="MrKoon OCR Service", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/extract")
async def extract_document(
    document_type: str = Form(...),
    method: str = Form("python"),
    file: UploadFile = File(...)
):
    try:
        logger.info(f"Received request: /extract | method: {method} | document_type: {document_type} | file: {file.filename}")
        image_bytes = await file.read()
        
        # Save the image
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Saved image to {file_path}")
        
        if method == "ai":
            parsed_data = await run_in_threadpool(process_document_with_ai, image_bytes, document_type)
            
            # Translate Eastern Arabic numerals to standard Western digits reliably
            if isinstance(parsed_data, dict) and "tax_registration_number" in parsed_data:
                tr_num = parsed_data["tax_registration_number"]
                if tr_num:
                    arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    parsed_data["tax_registration_number"] = tr_num.translate(arabic_to_western)

            logger.info(f"Successfully processed (ai) | Response: {parsed_data}")
            return JSONResponse(content=parsed_data)
        elif method == "python":
            # 1. Extract raw text
            raw_text = await run_in_threadpool(extract_text_from_image, image_bytes)
            
            # 2. Parse based on document type
            if document_type == 'egyptian_tax_card':
                parsed_data = parse_egyptian_tax_card(raw_text)
                logger.info(f"Successfully processed (python - egyptian_tax_card) | Response: {parsed_data}")
                return JSONResponse(content=parsed_data)
            else:
                # Default fallback
                logger.info(f"Successfully processed (python - default) | Response text length: {len(raw_text)}")
                return JSONResponse(content={"extracted_text": raw_text})
        elif method == "stdnum":
            # Standalone method to validate and return the full payload
            from stdnum.eg import tn
            
            raw_text = await run_in_threadpool(extract_text_from_image, image_bytes)
            parsed_data = parse_egyptian_tax_card(raw_text)
            
            number = parsed_data.get("tax_registration_number", "")
            if number:
                parsed_data["is_valid_egyptian_tax_number"] = tn.is_valid(number)
            else:
                parsed_data["is_valid_egyptian_tax_number"] = False
                
            logger.info(f"Successfully processed (stdnum) | Response: {parsed_data}")
            return JSONResponse(content=parsed_data)
        else:
            logger.warning(f"Invalid method requested: {method}")
            return JSONResponse(status_code=400, content={"error": "Invalid method. Choose 'ai', 'python', or 'stdnum'."})
            
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
