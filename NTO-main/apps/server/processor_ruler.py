import cv2
import mediapipe as mp
import numpy as np
import math

# Твой рабочий импорт и инициализация
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

def process_ruler(frame):
    h, w, _ = frame.shape
    
    # Больше не создаем mask = np.zeros, рисуем прямо в frame
    # Это позволит функции в main.py сравнить оригинал и измененный кадр

    # Твоя рабочая схема детекции
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    res = detector.detect(mp_image)

    if res.hand_landmarks:
        for landmarks in res.hand_landmarks:
            # 1. Получаем ключевые точки
            idx = landmarks[8]  # Указательный
            thmb = landmarks[4] # Большой
            
            x1, y1 = int(thmb.x * w), int(thmb.y * h)
            x2, y2 = int(idx.x * w), int(idx.y * h)

            # 2. Математика
            dist = int(np.hypot(x2 - x1, y2 - y1))
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            is_pinched = dist < 40
            color = (0, 0, 255) if is_pinched else (0, 255, 0)
            
            # 3. ТВОИ ВИЗУАЛЬНЫЕ ЭФФЕКТЫ (теперь на frame)
            # Силовое поле
            cv2.circle(frame, (x1, y1), dist // 2, color, 1)
            
            # Соединительная линия
            thickness = max(1, 10 - dist // 20)
            cv2.line(frame, (x1, y1), (x2, y2), color, thickness)

            # Отрисовка суставов
            for lm in landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 2, (255, 255, 255), -1)

            # Инфо-панель
            cv2.putText(frame, f"Dist: {dist}px", (x2 + 20, y2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(frame, f"Angle: {int(angle)}deg", (x2 + 20, y2 + 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            if is_pinched:
                cv2.putText(frame, "ACTION: SELECT", (w//2 - 50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    return frame # Возвращаем измененный кадр