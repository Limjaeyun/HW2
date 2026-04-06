import fitz
import cv2
import numpy as np
import pytesseract
import sys
import re

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)

for i in range(min(3, len(doc))):
    page = doc[i]
    pix = page.get_pixmap()
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
    else:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
    cv2.imwrite(f"/app/page_{i}_raw.jpg", img_np)

    hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 40, 50]), np.array([180, 255, 255]))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_contours = [cnt for cnt in contours if cv2.boundingRect(cnt)[2] > 30 and cv2.boundingRect(cnt)[3] > 10]
    valid_contours.sort(key=cv2.contourArea, reverse=True)
    
    debug_img = img_np.copy()
    
    for idx, cnt in enumerate(valid_contours[:5]):
        x, y, w, h = cv2.boundingRect(cnt)
        center_x = x + w / 2
        
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(debug_img, f"#{idx}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        roi = img_np[y:y+h, x:x+w]
        is_left = center_x < img_np.shape[1] / 2
        if is_left:
            roi_to_ocr = cv2.rotate(roi, cv2.ROTATE_180)
        else:
            roi_to_ocr = roi
            
        cv2.imwrite(f"/app/page_{i}_roi_{idx}.jpg", roi_to_ocr)
        
        roi_large = cv2.resize(roi_to_ocr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        ocr_1 = pytesseract.image_to_string(roi_large, lang='kor', config='--psm 6').strip()
        c_name_1 = re.sub(r'[^가-힣]', '', ocr_1)
        
        gray_roi = cv2.cvtColor(roi_large, cv2.COLOR_BGR2GRAY)
        thresh_roi = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
        
        cv2.imwrite(f"/app/page_{i}_thresh_{idx}.jpg", thresh_roi)

        ocr_2 = pytesseract.image_to_string(thresh_roi, lang='kor', config='--psm 6').strip()
        c_name_2 = re.sub(r'[^가-힣]', '', ocr_2)
        print(f"Page {i} Contour #{idx} - is_left: {is_left}")
        print(f"  OCR 1: '{ocr_1}' -> '{c_name_1}'")
        print(f"  OCR 2: '{ocr_2}' -> '{c_name_2}'")
        
    cv2.imwrite(f"/app/page_{i}_debug.jpg", debug_img)

doc.close()
