from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from app.services.pipeline import process_pdf

router = APIRouter()

@router.post("/process-pdf/", summary="Upload assignments PDF and get processed ZIP")
async def extract_and_split_pdf(file: UploadFile = File(...)):
    """
    1. 문서 180도 회전 보정
    2. 포스트잇의 이름 OCR 인식
    3. '첨삭/모의논술' 텍스트 분류
    4. 학생별로 쪼갠 파일이 들어있는 ZIP 파일로 반환
    """
    # 메모리에 PDF 파일 버퍼 할당
    pdf_contents = await file.read()
    
    # AI 파이프라인 처리 (CPU 바운드)
    zip_output_buffer = process_pdf(pdf_contents)
    
    # 쪼개진 PDF들이 담긴 zip 반환
    return StreamingResponse(
        zip_output_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="processed_results.zip"'}
    )
