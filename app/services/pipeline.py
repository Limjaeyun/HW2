import fitz  # PyMuPDF
import cv2
import numpy as np
import easyocr
import re
import zipfile
import difflib
from io import BytesIO

# 모델 로드 (서버 부팅 시 1회 메모리 로드)
reader = easyocr.Reader(['ko'], gpu=False)

def process_pdf(pdf_bytes: bytes) -> BytesIO:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    student_pages = {} # student_name -> { "category": [page_idx] }
    unknown_counter = 1
    current_student = "알수없음학생" # 안전장치 기본 묶음 폴더
    
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap()
        
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
        # 1. 포스트잇 컬러 인식
        hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 40, 50]), np.array([180, 255, 255]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [cnt for cnt in contours if cv2.boundingRect(cnt)[2] > 30 and cv2.boundingRect(cnt)[3] > 10]
        
        page_student = None
        
        if valid_contours:
            # 면적순 1위 추출
            valid_contours.sort(key=cv2.contourArea, reverse=True)
            biggest_cnt = valid_contours[0]
            x, y, w, h = cv2.boundingRect(biggest_cnt)
            center_x = x + w / 2
            
            # 왼쪽에 있다면 180도 회전
            is_left = center_x < img_np.shape[1] / 2
            if is_left:
                print(f"Page {i} post-it on LEFT! Rotating 180 degrees.")
                new_rotation = (page.rotation + 180) % 360
                page.set_rotation(new_rotation)
                pix = page.get_pixmap()
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR) if pix.n == 4 else cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            # 똑바른 상태에서 재검색
            hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, 40, 50]), np.array([180, 255, 255]))
            new_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            new_valid_contours = [cnt for cnt in new_contours if cv2.boundingRect(cnt)[2] > 30 and cv2.boundingRect(cnt)[3] > 10]
            
            if new_valid_contours:
                new_valid_contours.sort(key=cv2.contourArea, reverse=True)
                final_cnt = new_valid_contours[0]
                nx, ny, nw, nh = cv2.boundingRect(final_cnt)
                
                roi = img_np[ny:ny+nh, nx:nx+nw]
                
                # 딥러닝 기반 EasyOCR로 악필 필기체 완벽 인식
                ocr_result = reader.readtext(roi, detail=0)
                ocr_text = "".join(ocr_result).replace(" ", "")
                clean_name = re.sub(r'[^가-힣]', '', ocr_text)
                print(f"Page {i} EasyOCR Raw: {ocr_result} -> Cleaned: {clean_name}")
                
                if len(clean_name) >= 2 and len(clean_name) <= 5:
                    best_match = None
                    best_ratio = 0.0
                    for existing_student in student_pages.keys():
                        if existing_student == "알수없음학생" or existing_student.startswith("미인식학생"):
                            continue
                            
                        # 1. 순서 기반 텍스트 유사도
                        seq_ratio = difflib.SequenceMatcher(None, clean_name, existing_student).ratio()
                        
                        # 2. 순서 무시 문자열 교집합 기반 유사도 (예: "허운", "운모허" 매칭을 위함)
                        set_a, set_b = set(clean_name), set(existing_student)
                        intersection_len = len(set_a.intersection(set_b))
                        
                        subset_ratio = 0.0
                        if min(len(set_a), len(set_b)) > 0:
                            subset_ratio = intersection_len / min(len(set_a), len(set_b))
                            
                        # 두 글자 이상 겹치면서, 짧은 쪽 이름의 글자가 긴 쪽 이름에 거의 다 들어있는 경우(80%이상) 보정
                        if intersection_len >= 2 and subset_ratio >= 0.80:
                            ratio = max(seq_ratio, 0.85) # 강제 그룹핑
                        else:
                            ratio = seq_ratio

                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = existing_student
                    
                    if best_match and best_ratio >= 0.60:
                        page_student = best_match
                        print(f"Page {i} Text MATCH: {clean_name} -> {best_match} ({best_ratio:.2f})")
                    else:
                        page_student = clean_name
                        print(f"Page {i} NEW Text-based Student: {clean_name}")

        if not page_student:
            if current_student == "알수없음학생":
                page_student = f"미인식학생_{unknown_counter}"
                unknown_counter += 1
                print(f"Page {i} Failed OCR -> {page_student}")
            else:
                page_student = current_student
                print(f"Page {i} Failed OCR / No Postit -> Inherited: {page_student}")

        current_student = page_student

        # 상단 텍스트 분류 ('첨삭' / '모의논술')
        category = "일반"
        top_h = int(img_np.shape[0] * 0.3)
        top_img = img_np[0:top_h, :]
        
        # 상단 텍스트도 EasyOCR로 읽기
        ocr_top_result = reader.readtext(top_img, detail=0)
        ocr_top_text = "".join(ocr_top_result).replace(" ", "")
        
        if "첨삭" in ocr_top_text: category = "첨삭"
        elif "모의논술" in ocr_top_text: category = "모의논술"
        else:
            page_text = page.get_text().replace(" ", "")
            if "첨삭" in page_text: category = "첨삭"
            elif "모의논술" in page_text: category = "모의논술"
                
        print(f"Page {i} Category: {category} / Student: {page_student}")
                
        if page_student not in student_pages:
            student_pages[page_student] = {}
        if category not in student_pages[page_student]:
            student_pages[page_student][category] = []
            
        student_pages[page_student][category].append(i) 

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for student, categories in student_pages.items():
            for category, page_indices in categories.items():
                if not page_indices: continue
                
                new_doc = fitz.open()
                for idx in page_indices:
                    new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
                    new_doc[-1].set_rotation(doc[idx].rotation)
                    
                file_name = f"{student}_{category}.pdf"
                pdf_bytes = new_doc.tobytes()
                zf.writestr(file_name, pdf_bytes)
                new_doc.close()
                
    doc.close()
    zip_buffer.seek(0)
    return zip_buffer
