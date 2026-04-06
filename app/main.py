from fastapi import FastAPI
from app.api.endpoints import router

app = FastAPI(title="Essay PDF Management MLOps Pipeline (v2 업데이트 완료!)", description="AI powered PDF splitting service using OpenCV and Tesseract-OCR")

app.include_router(router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "status": "Healthy",
        "message": "AI PDF Pipeline API is running. Check out /docs for the interactive Swagger UI.", 
    }
