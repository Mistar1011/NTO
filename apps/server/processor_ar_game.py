import cv2
import numpy as np
import math

class ARGameServer:
    def __init__(self):

        self.friction = 0.96       # Замедление мяча
        self.max_speed = 10.0       # Чтобы не пробивал стены
        self.min_speed = 0.4        # Порог остановки
        self.pen_force = 5.0       # Сила удара ручкой
        self.wall_bounce = 0.80     # Упругость стен
        self.ball_radius = 18       
        self.finish_radius = 35     

        # Настройка AprilTag 16h5
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.game_zone = None
        self.ball_pos = None  
        self.ball_vel = [0.0, 0.0]
        self.start_point = None
        self.finish_point = None
        self.walls = []

        # Цвета для маски (на черном фоне будут светиться)
        self.COLORS = {
            'zone': (255, 0, 255),   
            'ball': (0, 255, 255),  
            'pen': (0, 255, 0),     
            'wall': (180, 120, 50),  
            'start': (0, 255, 0),    
            'finish': (0, 0, 255)     
        }

        # Зеленая ручка
        self.lower_green = np.array([35, 60, 60])
        self.upper_green = np.array([85, 255, 255])

    def build_level(self, zx1, zy1, zx2, zy2):
        zw, zh = zx2 - zx1, zy2 - zy1
        self.start_point = (zx1 + int(zw * 0.1), zy2 - int(zh * 0.15))
        self.finish_point = (zx2 - int(zw * 0.1), zy1 + int(zh * 0.15))
        
        # Лабиринт из стен
        self.walls = [
            (zx1 + int(zw * 0.35), zy1 + int(zh * 0.3), zx1 + int(zw * 0.45), zy2),
            (zx1 + int(zw * 0.65), zy1, zx1 + int(zw * 0.75), zy1 + int(zh * 0.7))
        ]

    def check_wall_collision(self):
        if not self.ball_pos: return
        for (wx1, wy1, wx2, wy2) in self.walls:
            cx = max(wx1, min(self.ball_pos[0], wx2))
            cy = max(wy1, min(self.ball_pos[1], wy2))
            dx, dy = self.ball_pos[0] - cx, self.ball_pos[1] - cy
            dist = math.hypot(dx, dy)

            if dist < self.ball_radius:
                if dist == 0: dx, dy = -self.ball_vel[0], -self.ball_vel[1]; dist = 1.0
                overlap = self.ball_radius - dist
                nx, ny = dx / dist, dy / dist
                self.ball_pos[0] += nx * overlap
                self.ball_pos[1] += ny * overlap
                dot = self.ball_vel[0] * nx + self.ball_vel[1] * ny
                self.ball_vel[0] -= 2 * dot * nx * self.wall_bounce
                self.ball_vel[1] -= 2 * dot * ny * self.wall_bounce

    def process_frame(self, frame):
        h, w, _ = frame.shape
        mask = np.zeros((h, w, 3), dtype=np.uint8)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        m0, m1 = None, None
        if ids is not None:
            for i, idx in enumerate(ids.flatten()):
                if idx == 0: m0 = np.mean(corners[i][0], axis=0)
                if idx == 1: m1 = np.mean(corners[i][0], axis=0)

        if m0 is not None and m1 is not None:
            x1, y1 = int(min(m0[0], m1[0])), int(min(m0[1], m1[1]))
            x2, y2 = int(max(m0[0], m1[0])), int(max(m0[1], m1[1]))
            self.game_zone = (x1, y1, x2, y2)
            self.build_level(x1, y1, x2, y2)
            if self.ball_pos is None: self.ball_pos = list(self.start_point)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        p_mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        cnts, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pen_pos, pen_box = None, None
        if cnts:
            largest = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(largest) > 400:
                rect = cv2.minAreaRect(largest)
                pen_box = cv2.boxPoints(rect).astype(np.int32)
                pen_pos = (int(rect[0][0]), int(rect[0][1]))

        if self.game_zone and self.ball_pos:
            zx1, zy1, zx2, zy2 = self.game_zone
            self.ball_vel[0] *= self.friction
            self.ball_vel[1] *= self.friction
            self.ball_pos[0] += self.ball_vel[0]
            self.ball_pos[1] += self.ball_vel[1]

            if self.ball_pos[0] <= zx1 + self.ball_radius or self.ball_pos[0] >= zx2 - self.ball_radius:
                self.ball_vel[0] *= -1; self.ball_pos[0] = np.clip(self.ball_pos[0], zx1+self.ball_radius, zx2-self.ball_radius)
            if self.ball_pos[1] <= zy1 + self.ball_radius or self.ball_pos[1] >= zy2 - self.ball_radius:
                self.ball_vel[1] *= -1; self.ball_pos[1] = np.clip(self.ball_pos[1], zy1+self.ball_radius, zy2-self.ball_radius)

            self.check_wall_collision()

            if pen_box is not None:
                dist = cv2.pointPolygonTest(pen_box, (self.ball_pos[0], self.ball_pos[1]), True)
                if dist >= -self.ball_radius:
                    dx, dy = self.ball_pos[0] - pen_pos[0], self.ball_pos[1] - pen_pos[1]
                    d = math.hypot(dx, dy) or 1
                    self.ball_vel[0], self.ball_vel[1] = (dx/d)*self.pen_force, (dy/d)*self.pen_force

            if math.hypot(self.ball_pos[0]-self.finish_point[0], self.ball_pos[1]-self.finish_point[1]) < self.finish_radius:
                self.ball_pos = list(self.start_point); self.ball_vel = [0,0]

            cv2.rectangle(mask, (zx1, zy1), (zx2, zy2), self.COLORS['zone'], 3)
            cv2.circle(mask, self.start_point, 20, self.COLORS['start'], 2)
            cv2.circle(mask, self.finish_point, self.finish_radius, self.COLORS['finish'], -1)
            for w_box in self.walls: cv2.rectangle(mask, (w_box[0], w_box[1]), (w_box[2], w_box[3]), self.COLORS['wall'], -1)
            cv2.circle(mask, (int(self.ball_pos[0]), int(self.ball_pos[1])), self.ball_radius, self.COLORS['ball'], -1)
            if pen_box is not None: cv2.drawContours(mask, [pen_box], 0, self.COLORS['pen'], 2)

        return mask, frame

engine = ARGameServer()
def process_ar_game(frame):
    mask, _ = engine.process_frame(frame)
    return mask

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        mask, flipped_frame = engine.process_frame(frame)
        
        combined = cv2.addWeighted(flipped_frame, 0.7, mask, 1.0, 0)
        
        cv2.imshow("SERVER MASK (Black)", combined)
        
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()
#Вроде работает, проверь плиз
