import cv2
import numpy as np
import math

class ARGameProcessor:
    def __init__(self):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # --- ОРИГИНАЛЬНЫЕ ЦВЕТА ---
        self.COLORS = {
            'zone': (255, 0, 255),    # Фиолетовый
            'ball': (255, 255, 0),    # Голубой/Циан
            'pen': (0, 255, 0),       # Зеленый
            'pen_box': (100, 255, 100), # Светло-зеленый
            'wall': (100, 50, 0),     # Коричневый
            'collision': (255, 50, 50),
            'direction': (255, 150, 0)
        }
        
        # Состояние (Локальные координаты для стабильности)
        self.ball_local_pos = [0.5, 0.5] 
        self.ball_velocity = [0.0, 0.0] 
        self.ball_friction = 0.97
        self.ball_radius_px = 15
        
        self.game_zone = None 
        self.walls = []
        self.pen_vertices = []
        self.pen_position = None
        
        self.lower_green = np.array([35, 60, 60])
        self.upper_green = np.array([85, 255, 255])

    def create_walls(self):
        if not self.game_zone: return
        x1, y1, x2, y2 = self.game_zone
        w, h = x2 - x1, y2 - y1
        self.walls = [
            {'rect': (x1, y1 + h//3, x2 - w//3, y1 + h//3 + 15), 'type': 'horizontal'},
            {'rect': (x2 - w//3, y1 + h//3, x2 - w//3 + 15, y2 - h//3), 'type': 'vertical'},
            {'rect': (x1 + w//3, y1 + 2*h//3, x2, y1 + 2*h//3 + 15), 'type': 'horizontal'},
            {'rect': (x1 + w//3, y1 + h//3, x1 + w//3 + 15, y1 + 2*h//3), 'type': 'vertical'}
        ]

    def process_ar_game(self, frame):
        h_f, w_f, _ = frame.shape
        mask = np.zeros((h_f, w_f, 3), dtype=np.uint8)
        
        # 1. Детекция маркеров
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        m_pos = {}
        if ids is not None:
            for i, m_id in enumerate(ids.flatten()):
                if m_id in [0, 1]:
                    m_pos[int(m_id)] = (int(np.mean(corners[i][0][:, 0])), int(np.mean(corners[i][0][:, 1])))

        # Если нашли оба маркера — обновляем зону. Если нет — используем старую.
        if 0 in m_pos and 1 in m_pos:
            p1, p2 = m_pos[0], m_pos[1]
            self.game_zone = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
            self.create_walls()

        # 2. ТРЕКИНГ РУЧКИ (ВСЕГДА ПО ВСЕМУ КАДРУ)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        p_mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        cnts, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            largest = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(largest) > 300:
                rect = cv2.minAreaRect(largest)
                self.pen_position = (int(rect[0][0]), int(rect[0][1]))
                self.pen_vertices = cv2.boxPoints(rect).astype(np.int32)
        else:
            self.pen_vertices = []

        # 3. ФИЗИКА И ОТРИСОВКА (если зона когда-либо была найдена)
        if self.game_zone:
            self._update_physics()
            self._draw_elements(mask)
            
        return mask

    def _update_physics(self):
        x1, y1, x2, y2 = self.game_zone
        zw, zh = x2 - x1, y2 - y1
        if zw <= 0 or zh <= 0: return

        # Движение
        self.ball_velocity[0] *= self.ball_friction
        self.ball_velocity[1] *= self.ball_friction
        self.ball_local_pos[0] += self.ball_velocity[0] / zw
        self.ball_local_pos[1] += self.ball_velocity[1] / zh

        # Текущий пиксельный X/Y
        gbx = x1 + self.ball_local_pos[0] * zw
        gby = y1 + self.ball_local_pos[1] * zh

        # Границы (Локально)
        rx, ry = self.ball_radius_px / zw, self.ball_radius_px / zh
        if self.ball_local_pos[0] < rx:
            self.ball_local_pos[0] = rx
            self.ball_velocity[0] *= -0.9
        elif self.ball_local_pos[0] > 1.0 - rx:
            self.ball_local_pos[0] = 1.0 - rx
            self.ball_velocity[0] *= -0.9
        if self.ball_local_pos[1] < ry:
            self.ball_local_pos[1] = ry
            self.ball_velocity[1] *= -0.9
        elif self.ball_local_pos[1] > 1.0 - ry:
            self.ball_local_pos[1] = 1.0 - ry
            self.ball_velocity[1] *= -0.9

        # Стены (Глобально)
        for wall in self.walls:
            wx1, wy1, wx2, wy2 = wall['rect']
            cx = max(wx1, min(gbx, wx2))
            cy = max(wy1, min(gby, wy2))
            if math.hypot(gbx - cx, gby - cy) <= self.ball_radius_px:
                if wall['type'] == 'horizontal':
                    self.ball_velocity[1] *= -0.8
                    self.ball_local_pos[1] = (wy1 - self.ball_radius_px - y1)/zh if gby < wy1 else (wy2 + self.ball_radius_px - y1)/zh
                else:
                    self.ball_velocity[0] *= -0.8
                    self.ball_local_pos[0] = (wx1 - self.ball_radius_px - x1)/zw if gbx < wx1 else (wx2 + self.ball_radius_px - x1)/zw

        # Ручка
        if len(self.pen_vertices) == 4:
            dist = cv2.pointPolygonTest(self.pen_vertices, (gbx, gby), True)
            if dist >= -self.ball_radius_px:
                self.ball_velocity[0] = (gbx - self.pen_position[0]) * 0.5
                self.ball_velocity[1] = (gby - self.pen_position[1]) * 0.5

    def _draw_elements(self, mask):
        x1, y1, x2, y2 = self.game_zone
        zw, zh = x2 - x1, y2 - y1
        gbx, gby = int(x1 + self.ball_local_pos[0] * zw), int(y1 + self.ball_local_pos[1] * zh)

        # Стены и Зона
        for wall in self.walls:
            wx1, wy1, wx2, wy2 = wall['rect']
            cv2.rectangle(mask, (wx1, wy1), (wx2, wy2), self.COLORS['wall'], -1)
        cv2.rectangle(mask, (x1, y1), (x2, y2), self.COLORS['zone'], 3)

        # Мяч (Оригинальный визуал)
        cv2.circle(mask, (gbx+2, gby+2), self.ball_radius_px, (30,30,30), -1) # Тень
        for r in range(self.ball_radius_px, 0, -2):
            c = int(255 * (r/self.ball_radius_px))
            cv2.circle(mask, (gbx, gby), r, (c, c, 0), -1)
        cv2.circle(mask, (gbx, gby), self.ball_radius_px, self.COLORS['ball'], 2)

        # Ручка
        if len(self.pen_vertices) == 4:
            cv2.drawContours(mask, [self.pen_vertices], 0, self.COLORS['pen_box'], 2)

engine = ARGameProcessor()
def process_ar_game(frame):
    return engine.process_ar_game(frame)