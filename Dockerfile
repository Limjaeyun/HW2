FROM python:3.11-slim

# Install system dependencies
# tesseract-ocr: Tesseract engine
# tesseract-ocr-kor: Korean language pack (필수)
# libtesseract-dev: Tesseract C++ 라이브러리 인터페이스 (여러 파이썬 패키지 의존성)
# libgl1-mesa-glx, libglib2.0-0: OpenCV 라이브러리용 시스템 종속성
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kor \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Pre-download EasyOCR models to speed up initial inference
RUN python -c "import easyocr; easyocr.Reader(['ko'], gpu=False)"

# Expose FastAPI port
EXPOSE 8000

# Run Uvicorn async server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
