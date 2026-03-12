import cv2
import numpy as np

class ARGameProcessor3D:
    def __init__(self):
        # Используем твой словарь ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

    def process_ar_game(self, frame):
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        # Матрица камеры для корректной перспективы
        f = w 
        cam_matrix = np.array([[f, 0, w/2], [0, f, h/2], [0, 0, 1]], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1))

        if ids is not None:
            for i in range(len(ids)):
                # Рисуем куб только на маркере с ID 0 (или на всех, если убрать if)
                if ids[i] == 0:
                    # 3D координаты углов маркера в его локальной системе (Z=0 - это плоскость бумаги)
                    # s - это половина размера. Если маркер 5см, то s=2.5
                    s = 40 
                    obj_pts = np.array([[-s,s,0], [s,s,0], [s,-s,0], [-s,-s,0]], dtype=np.float32)
                    
                    # Вычисляем поворот и позицию (PnP)
                    ret, rvec, tvec = cv2.solvePnP(obj_pts, corners[i], cam_matrix, dist_coeffs)
                    
                    if ret:
                        # Точки полноценного куба (отрицательный Z, чтобы рос ВВЕРХ от маркера)
                        # Мы рисуем 8 точек: 4 на маркере и 4 в воздухе
                        cube_3d = np.float32([
                            [-s,s,0], [s,s,0], [s,-s,0], [-s,-s,0],       # Основание
                            [-s,s,-s*2], [s,s,-s*2], [s,-s,-s*2], [-s,-s,-s*2] # Верхушка
                        ])
                        
                        imgpts, _ = cv2.projectPoints(cube_3d, rvec, tvec, cam_matrix, dist_coeffs)
                        imgpts = np.int32(imgpts).reshape(-1, 2)

                        # 1. Рисуем задние стенки (для объема)
                        cv2.fillConvexPoly(frame, np.array([imgpts[0], imgpts[1], imgpts[5], imgpts[4]]), (150, 0, 150))
                        cv2.fillConvexPoly(frame, np.array([imgpts[1], imgpts[2], imgpts[6], imgpts[5]]), (100, 0, 100))
                        cv2.fillConvexPoly(frame, np.array([imgpts[2], imgpts[3], imgpts[7], imgpts[6]]), (120, 0, 120))
                        cv2.fillConvexPoly(frame, np.array([imgpts[3], imgpts[0], imgpts[4], imgpts[7]]), (140, 0, 140))
                        
                        # 2. Рисуем верхнюю грань (крышку)
                        cv2.fillConvexPoly(frame, np.array([imgpts[4], imgpts[5], imgpts[6], imgpts[7]]), (200, 50, 200))

                        # 3. Белая обводка ребер для стиля AR.js
                        for j in range(4):
                            cv2.line(frame, tuple(imgpts[j]), tuple(imgpts[(j+1)%4]), (255, 255, 255), 2)
                            cv2.line(frame, tuple(imgpts[j+4]), tuple(imgpts[(j+1)%4+4]), (255, 255, 255), 2)
                            cv2.line(frame, tuple(imgpts[j]), tuple(imgpts[j+4]), (255, 255, 255), 2)

        return frame

# Блок запуска
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    proc = ARGameProcessor3D()
    while True:
        ret, frame = cap.read()
        if not ret: break
        cv2.imshow('STABLE AR CUBE', proc.process_ar_game(frame))
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()