import cv2

def process_gray(frame):
    # 1. Делаем ч/б
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. Возвращаем обратно в 3 канала (BGR), 
    # так как main.py ожидает цветную структуру для упаковки в JPEG/WebP
    return gray