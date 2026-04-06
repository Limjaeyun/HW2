import fitz
import cv2
import numpy as np
import pytesseract
import sys
import re

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)

page = doc[0]
pix = page.get_pixmap()
img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
if pix.n == 4:
    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
else:
    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, np.array([0, 40, 50]), np.array([180, 255, 255]))
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
valid_contours = [cnt for cnt in contours if cv2.boundingRect(cnt)[2] > 30 and cv2.boundingRect(cnt)[3] > 10]
valid_contours.sort(key=cv2.contourArea, reverse=True)

cnt = valid_contours[0]
x, y, w, h = cv2.boundingRect(cnt)
center_x = x + w / 2

roi = img_np[y:y+h, x:x+w]
is_left = center_x < img_np.shape[1] / 2
if is_left:
    roi = cv2.rotate(roi, cv2.ROTATE_180)

def extract(img, psm):
    return re.sub(r'[^가-힣]', '', pytesseract.image_to_string(img, lang='kor', config=f'--psm {psm}').strip())

# 1. Raw
print(f"Raw PSM 7: {extract(roi, 7)}")
print(f"Raw PSM 6: {extract(roi, 6)}")

# 2. Resize 2x
roi_2x = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
print(f"2x PSM 7: {extract(roi_2x, 7)}")
print(f"2x PSM 6: {extract(roi_2x, 6)}")

# 3. Gray + Otsu
gray = cv2.cvtColor(roi_2x, cv2.COLOR_BGR2GRAY)
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
print(f"Otsu PSM 7: {extract(otsu, 7)}")
print(f"Otsu PSM 6: {extract(otsu, 6)}")

# 4. Adaptive
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
print(f"Adaptive PSM 7: {extract(adaptive, 7)}")
print(f"Adaptive PSM 6: {extract(adaptive, 6)}")

doc.close()
