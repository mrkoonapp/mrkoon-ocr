FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download PaddleOCR models at build time so the first request isn't slow
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_textline_orientation=True, lang='ar', use_gpu=False)"

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8000

# Run the FastAPI app
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port \${PORT:-8000}"
