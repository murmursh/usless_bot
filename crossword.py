import cv2
import numpy as np
from PIL import Image, ImageDraw


def extract_crossword_grid(image_path):
    img = cv2.imread(image_path)
    h, w, _ = img.shape

    # Crop top area (crossword zone)
    y1, y2 = int(h * 0.19), int(h * 0.60)
    x1, x2 = int(0), int(w)
    cropped = img[y1:y2, x1:x2]

    cv2.imwrite('ccropped.png', cropped)
    # Convert to HSV for color filtering (blue squares)
    # hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)

    # empty
    target_color = np.array([98, 107, 20])  # BGR equivalent of RGB 20, 107, 98
    tolerance = 10
    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)
    mask_empty = cv2.inRange(cropped, lower_bound, upper_bound)

    #filled
    target_color = np.array([31, 231, 251])  # BGR equivalent of RGB 251, 231, 31
    tolerance = 30
    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)
    mask_filled = cv2.inRange(cropped, lower_bound, upper_bound)

    mask = cv2.bitwise_or(mask_empty, mask_filled)

    masked = cv2.bitwise_and(cropped, cropped, mask=mask)
    cv2.imwrite('cmasked.png', masked)
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter out small noise
        if w > 10 and h > 10:
            boxes.append((x, y, w, h))
    contered = cv2.drawContours(masked, contours, -1, (0,255,0), 3)
    cv2.imwrite('ccontered.png', contered)
    # Sort by Y, then X
    boxes = sorted(boxes, key=lambda b: (b[1]//50, b[0]))

    # Estimate grid step size
    if not boxes:
        return []

    # Get centers
    centers = [(x + w//2, y + h//2) for (x, y, w, h) in boxes]

    # Cluster Y into rows
    cell_h = int(np.median([h for (_, _, _, h) in boxes]))
    rows_dict = {}
    for (cx, cy) in centers:
        row = int(round(cy / cell_h))
        rows_dict.setdefault(row, []).append((cx, cy))

    # Sort rows by Y
    rows = [rows_dict[k] for k in sorted(rows_dict.keys())]

    # Collect all X positions
    xs = sorted([cx for (cx, _) in centers])
    cell_w = int(np.median([w for (_, _, w, _) in boxes]))

    # Cluster X into columns
    cols = []
    for x in xs:
        if not cols or abs(x - cols[-1]) > cell_w // 2:
            cols.append(x)

    # Build matrix
    matrix = []
    for row in rows:
        row_vec = [0] * len(cols)
        for (cx, cy) in row:
            # find nearest column
            col_idx = np.argmin([abs(cx - c) for c in cols])
            row_vec[col_idx] = 1
        matrix.append(row_vec)

    return matrix
'''

[0, 0, 1, 0, 1, 0]
[0, 0, 1, 0, 1, 0]
[0, 1, 1, 1, 1, 1]
[0, 1, 0, 0, 0, 0]
[1, 1, 1, 0, 0, 0]
[0, 1, 0, 0, 0, 0]
'''


def matrix_to_crossword_image(matrix, cell_size=30, margin=20):
    """
    Преобразует матрицу в изображение кроссворда.
    
    Args:
        matrix: 2D список или numpy array с 0 и 1
        cell_size: размер одной клетки в пикселях
        margin: отступ от краев изображения
    
    Returns:
        PIL Image object
    """
    # Преобразуем в numpy array для удобства
    matrix = np.array(matrix)
    rows, cols = matrix.shape
    
    # Размеры изображения
    width = cols * cell_size + 2 * margin
    height = rows * cell_size + 2 * margin
    
    # Создаем изображение
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Цвета
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (200, 200, 200)
    
    # Рисуем сетку
    for i in range(rows + 1):
        y = margin + i * cell_size
        draw.line([(margin, y), (margin + cols * cell_size, y)], fill=GRAY, width=1)
    
    for j in range(cols + 1):
        x = margin + j * cell_size
        draw.line([(x, margin), (x, margin + rows * cell_size)], fill=GRAY, width=1)
    
    # Заполняем клетки
    for i in range(rows):
        for j in range(cols):
            if matrix[i, j] == 1:
                # Черная клетка (заполненная)
                x1 = margin + j * cell_size
                y1 = margin + i * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                draw.rectangle([x1, y1, x2, y2], fill=BLACK)
    
    return img

if __name__ == "__main__":
    path = "screenshot.png"
    crossword = extract_crossword_grid(path)
    img = matrix_to_crossword_image(crossword)