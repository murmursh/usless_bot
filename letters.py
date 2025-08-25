import re
import cv2
import os
import easyocr
import numpy as np
import pytesseract
import tempfile


def ocr_tesseract_optimized(image):
    """Optimized Tesseract with multiple attempts and TIFF conversion"""

    # Try different PSM modes
    psm_modes = [6,]
    best_text = ""
    
    # Invert colors
    image = cv2.bitwise_not(image)
    h,w = image.shape[:2]
    image = cv2.resize(image, (w*10, h*10), interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    try:
        cv2.imwrite(temp_filename, image)
        
        tiff_image = cv2.imread(temp_filename)
        
        for psm in psm_modes:
            config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
            text = pytesseract.image_to_string(tiff_image, lang='rus', config=config)
            
            # Check if this gives more Cyrillic letters
            cyrillic_count = len(re.findall(r'[А-ЯЁ]', text))
            if cyrillic_count > len(re.findall(r'[А-ЯЁ]', best_text)):
                best_text = text
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)
    
    return best_text.strip().upper()


def ocr_easyocr(image):
    """Use EasyOCR for Cyrillic text recognition"""
    reader = easyocr.Reader(['ru'], gpu=False)  # Set gpu=True if you have CUDA
    # Initialize reader with Russian language
    
    # EasyOCR works better with BGR images
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    # Perform OCR
    results = reader.readtext(image, detail=0)
    
    # Combine all detected text
    text = ' '.join(results)
    return text.upper()

def extract_cyrillic_letters(image_path):
    # Load image
    img = cv2.imread(image_path)
    h, w, _ = img.shape

    # Crop bottom area (where the circle with letters is)
    # Adjust values if needed depending on screenshots
    y1 = int(h * 0.65)   # start ~65% down the screen
    y2 = int(h*0.90)               # bottom of image
    x1 = int(w * 0.15)   # left margin
    x2 = int(w * 0.85)   # right margin
    cropped = img[y1:y2, x1:x2]

    target_color = np.array([98, 108, 38])  # BGR equivalent of RGB(38, 108, 98)

    tolerance = 30

    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)

    mask = cv2.inRange(cropped, lower_bound, upper_bound)

    cropped = cv2.bitwise_and(cropped, cropped, mask=mask)
    result = np.zeros_like(cropped)
    result[mask > 0] = [255, 255, 255] 

    # Convert to grayscale for processing
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    cv2.imwrite('new.png', result)

    # Apply threshold to get binary image (white letters on black background)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours of letters
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and sort contours from left to right
    letter_contours = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter out small noise
        if w > 10 and h > 10:
            letter_contours.append((x, y, w, h))
    
    # Sort contours by x-coordinate (left to right)
    letter_contours.sort(key=lambda x: x[0])
    
    # Extract individual letter images
    letter_images = []
    for x, y, w, h in letter_contours:
        letter_img = thresh[y:y+h, x:x+w]
        letter_images.append(letter_img)
    
    # Join letters horizontally
    if letter_images:
        # Find max height to resize all letters to same height
        max_height = max(img.shape[0] for img in letter_images)
        
        # Resize all letters to have same height and add black padding
        resized_letters = []
        for letter in letter_images:
            # Calculate aspect ratio
            h, w = letter.shape
            aspect_ratio = w / h
            new_w = int(max_height * aspect_ratio)
            
            # Resize letter
            resized = cv2.resize(letter, (new_w, max_height))
            
            # Add black padding around the letter (0 = black)
            padded = np.zeros((max_height + 20, new_w + 20), dtype=np.uint8)
            padded[10:10+max_height, 10:10+new_w] = resized
            
            resized_letters.append(padded)
        
        # Combine all letters horizontally
        combined_image = np.hstack(resized_letters)
        
        # Save the combined image
        cv2.imwrite('combined_letters.png', combined_image)
        
        # Perform OCR on the combined image
        return ocr_tesseract_optimized(combined_image)
    
    return "No letters found"

if __name__ == "__main__":
    path = "screenshot.png"  # Replace with your screenshot file
    letters = extract_cyrillic_letters(path)
    print("Extracted letters:", letters)