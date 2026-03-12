import cv2
import numpy as np

# 1. Выбираем словарь (как ты и просил - AprilTag 16h5)
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5)

# 2. Настраиваем детектор "из коробки"
aruco_params = cv2.aruco.DetectorParameters()
# Включаем уточнение углов для стабильности 3D
aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# Параметры камеры (нужны для drawFrameAxes)
# Если у тебя нет данных калибровки, используем стандартную заглушку
camera_matrix = np.array([[1000, 0, 640], [0, 1000, 360], [0, 0, 1]], dtype="float32")
dist_coeffs = np.zeros((4, 1))

def process_aruco(frame):
    mask = np.zeros_like(frame)
    
    # ОСНОВНОЙ МЕТОД: Поиск маркеров
    corners, ids, rejected = detector.detectMarkers(frame)

    if ids is not None:
        # ФУНКЦИЯ 1: Отрисовка границ и ID (2D данные)
        cv2.aruco.drawDetectedMarkers(mask, corners, ids)

        # ФУНКЦИЯ 2: Оценка позы и отрисовка осей (3D данные)
        # В новых версиях OpenCV для этого есть удобный метод в модуле aruco
        for i in range(len(ids)):
            # Оцениваем позу через solvePnP (встроено в логику AR)
            # markerLength = 0.05 (размер маркера в метрах)
            obj_points = np.array([[-0.025, 0.025, 0], [0.025, 0.025, 0], 
                                   [0.025, -0.025, 0], [-0.025, -0.025, 0]], dtype="float32")
            
            _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], camera_matrix, dist_coeffs)

            # ФУНКЦИЯ 3: Отрисовка 3D осей (коробочный метод)
            cv2.drawFrameAxes(mask, camera_matrix, dist_coeffs, rvec, tvec, 0.03)
    
    # ФУНКЦИЯ 4: Визуализация "отвергнутых" (тех, что камера видит, но не может прочесть)
    # if rejected:
    #     cv2.aruco.drawDetectedMarkers(mask, rejected, borderColor=(50, 50, 50))

    return mask