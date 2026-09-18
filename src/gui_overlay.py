import cv2
import numpy as np
import time
import os
from typing import List, Tuple
from src.face_engine import FaceResult
from src.state_machine import RobotState

# Color constants (BGR format for OpenCV)
COLOR_BLUE = (255, 180, 0)
COLOR_GREEN = (0, 220, 0)
COLOR_RED = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_ORANGE = (0, 140, 255)


class GUIOverlay:
    def __init__(self):
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0.0
        self.last_fps_update = time.time()

        unicorn_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "unicorn.png",
        )
        self.unicorn = cv2.imread(unicorn_path, cv2.IMREAD_UNCHANGED)
        if self.unicorn is None:
            print(f"[Attention] Image de licorne introuvable : {unicorn_path}")

        # Position conservée entre les frames : après avoir suivi un visage,
        # la licorne reprend sa promenade depuis cette position.
        self.unicorn_x = 0
        self.unicorn_speed = 2

    def _draw_rounded_rect(self, frame, pt1, pt2, color, thickness, radius=0.2):
        cv2.rectangle(frame, pt1, pt2, color, thickness)

    def _put_text_with_background(self, frame, text, pos, font_scale, color, bg_color):
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(font_scale * 2))
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        x, y = pos
        cv2.rectangle(frame, (x, y - text_height - baseline), (x + text_width, y + baseline), bg_color, cv2.FILLED)
        cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)

    def _overlay_unicorn(self, frame, x, y, width):
        """Superpose le PNG avec son canal alpha, même s'il dépasse du cadre."""
        if self.unicorn is None or self.unicorn.size == 0:
            return

        source_height, source_width = self.unicorn.shape[:2]
        if source_width <= 0:
            return
        height = max(1, int(source_height * width / source_width))
        unicorn = cv2.resize(self.unicorn, (width, height), interpolation=cv2.INTER_AREA)

        frame_height, frame_width = frame.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(frame_width, int(x) + width), min(frame_height, int(y) + height)
        if x1 >= x2 or y1 >= y2:
            return

        crop_x1, crop_y1 = x1 - int(x), y1 - int(y)
        crop = unicorn[crop_y1:crop_y1 + y2 - y1, crop_x1:crop_x1 + x2 - x1]
        destination = frame[y1:y2, x1:x2]

        if crop.ndim == 3 and crop.shape[2] == 4:
            alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
            foreground = crop[:, :, :3].astype(np.float32)
            background = destination.astype(np.float32)
            destination[:] = (foreground * alpha + background * (1.0 - alpha)).astype(np.uint8)
        else:
            destination[:] = crop[:, :, :3]

    def _draw_unicorn(self, frame, faces: List[FaceResult]):
        """Suit un visage ; sans visage, la licorne reprend sa promenade."""
        if self.unicorn is None or self.unicorn.size == 0:
            return

        if faces:
            # On suit le plus grand visage détecté, généralement le plus proche.
            x, y, face_width, face_height = max(
                (face.box for face in faces),
                key=lambda box: box[2] * box[3],
            )
            width = max(40, int(face_width * 1.45))
            source_ratio = self.unicorn.shape[0] / self.unicorn.shape[1]
            rendered_height = max(1, int(width * source_ratio))

            # Centre l'image de licorne sur la tête détectée.
            unicorn_x = int(x + face_width / 2 - width / 2)
            unicorn_y = int(y + face_height / 2 - rendered_height / 2)
            self.unicorn_x = unicorn_x
            self._overlay_unicorn(frame, unicorn_x, unicorn_y, width)
            return

        # Aucun visage : déplacement horizontal et flottement vertical.
        frame_height, frame_width = frame.shape[:2]
        source_height, source_width = self.unicorn.shape[:2]
        width = 120
        height = max(1, int(source_height * width / source_width))
        self.unicorn_x += self.unicorn_speed
        if self.unicorn_x > frame_width:
            self.unicorn_x = -width
        y = int(frame_height * 0.68 + 12 * np.sin(time.time() * 3.0))
        self._overlay_unicorn(frame, self.unicorn_x, y, width)

    def _draw_status_bar(self, frame, state: RobotState, state_info: dict, fps: float):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        color = {
            RobotState.PATROL: COLOR_WHITE,
            RobotState.SCAN: COLOR_BLUE,
            RobotState.IDENTIFIED: COLOR_GREEN,
            RobotState.RETREAT: COLOR_ORANGE,
            RobotState.ALERT: COLOR_RED,
        }.get(state, COLOR_WHITE)
        cv2.circle(frame, (20, 20), 8, color, -1)
        cv2.putText(frame, state.name, (40, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_WHITE, 2)

        info_text = ""
        if state == RobotState.SCAN:
            info_text = f"Analyse en cours... {state_info.get('scan_remaining', 0):.1f}s"
        elif state in (RobotState.IDENTIFIED, RobotState.RETREAT):
            info_text = f"Cible: {state_info.get('name', 'Inconnu')}"
        if info_text:
            text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.putText(frame, info_text, ((w - text_size[0]) // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        fps_text = f"{fps:.1f} FPS"
        fps_color = COLOR_GREEN if fps > 15 else (COLOR_YELLOW if fps > 8 else COLOR_RED)
        fps_size = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, fps_text, (w - fps_size[0] - 10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, fps_color, 2)

    def draw(self, frame: np.ndarray, faces: List[FaceResult], state: RobotState, state_info: dict) -> np.ndarray:
        display_frame = frame.copy()
        self.frame_count += 1
        now = time.time()
        if now - self.last_fps_update > 1.0:
            self.current_fps = self.frame_count / (now - self.last_fps_update)
            self.frame_count = 0
            self.last_fps_update = now

        self._draw_status_bar(display_frame, state, state_info, self.current_fps)

        for face in faces:
            x, y, w, h = face.box
            if state == RobotState.PATROL:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), COLOR_WHITE, 1)
            elif state == RobotState.SCAN:
                cv2.rectangle(display_frame, (max(0, x - w // 2), y), (x + w * 2, y + h * 3), COLOR_BLUE, 2)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), COLOR_YELLOW, 2)
                self._put_text_with_background(display_frame, f"SCAN EN COURS... {int(state_info.get('progress', 0))}%", (x, y - 10), 0.5, COLOR_BLACK, COLOR_YELLOW)
                bar_y = y + int(h * abs(np.sin(now * 5)))
                cv2.line(display_frame, (x, bar_y), (x + w, bar_y), COLOR_YELLOW, 2)
            elif state in (RobotState.IDENTIFIED, RobotState.RETREAT):
                color = COLOR_GREEN if state == RobotState.IDENTIFIED else COLOR_ORANGE
                cv2.rectangle(display_frame, (max(0, x - w // 2), y), (x + w * 2, y + h * 3), color, 2)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                self._put_text_with_background(display_frame, face.name or "Inconnu", (x, y - 10), 0.7, COLOR_BLACK, color)
            elif state == RobotState.ALERT and int(now * 3.33) % 2 == 0:
                cv2.rectangle(display_frame, (max(0, x - w // 2), y), (x + w * 2, y + h * 3), COLOR_RED, 3)

        if state == RobotState.ALERT and int(now * 3.33) % 2 == 0:
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), COLOR_RED, 20)
            cv2.addWeighted(overlay, 0.4, display_frame, 0.6, 0, display_frame)

        # La licorne suit le visage, puis reprend sa trajectoire lorsqu'il disparaît.
        self._draw_unicorn(display_frame, faces)

        fps_text = f"{self.current_fps:.1f} FPS"
        cv2.putText(display_frame, fps_text, (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_GREEN, 2)
        return display_frame
