import cv2
import numpy as np
from ultralytics import YOLO

# Загружаем один раз при старте сервера
model = YOLO('yolov8n.pt')

def process_yolo(frame):
    # 1. Инференс
    # imgsz=480 — отличный выбор для скорости
    results = model(frame, verbose=False, imgsz=480)
    
    # 2. РИСУЕМ ИЗ КОРОБКИ
    # Вместо img=mask подставляем img=frame.
    # Теперь YOLO нарисует боксы и подписи прямо поверх видеопотока.
    annotated_frame = results[0].plot(
        img=frame, 
        conf=True, 
        labels=True, 
        boxes=True,
        line_width=2
    )
    
    return annotated_frame