import cv2
import numpy as np
import time
from typing import List, Tuple
from src.face_engine import FaceResult
from src.state_machine import RobotState

# Color constants (BGR format for OpenCV)
COLOR_BLUE = (255, 180, 0)       # Scanning
COLOR_GREEN = (0, 220, 0)        # Identified  
COLOR_RED = (0, 0, 255)          # Alert
COLOR_YELLOW = (0, 255, 255)     # Head box during scan
COLOR_WHITE = (255, 255, 255)    # Text
COLOR_BLACK = (0, 0, 0)          # Background
COLOR_ORANGE = (0, 140, 255)     # Retreat

class GUIOverlay:
    def __init__(self):
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0.0
        self.last_fps_update = time.time()
        
    def _draw_rounded_rect(self, frame, pt1, pt2, color, thickness, radius=0.2):
        # Draw a rectangle for now (can be enhanced to rounded)
        cv2.rectangle(frame, pt1, pt2, color, thickness)
        
    def _put_text_with_background(self, frame, text, pos, font_scale, color, bg_color):
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(font_scale * 2))
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        x, y = pos
        cv2.rectangle(frame, (x, y - text_height - baseline), (x + text_width, y + baseline), bg_color, cv2.FILLED)
        cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
        
    def _draw_status_bar(self, frame, state: RobotState, state_info: dict, fps: float):
        h, w = frame.shape[:2]
        
        # Semi-transparent black bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        state_name = state.name
        color = COLOR_WHITE
        
        if state == RobotState.PATROL:
            color = COLOR_WHITE
        elif state == RobotState.SCAN:
            color = COLOR_BLUE
        elif state == RobotState.IDENTIFIED:
            color = COLOR_GREEN
        elif state == RobotState.RETREAT:
            color = COLOR_ORANGE
        elif state == RobotState.ALERT:
            color = COLOR_RED
            
        # Left: State name with colored indicator dot
        cv2.circle(frame, (20, 20), 8, color, -1)
        cv2.putText(frame, state_name, (40, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_WHITE, 2)
        
        # Center: Context info
        info_text = ""
        if state == RobotState.SCAN:
            rem = state_info.get("scan_remaining", 0)
            info_text = f"Analyse en cours... {rem:.1f}s"
        elif state in (RobotState.IDENTIFIED, RobotState.RETREAT):
            name = state_info.get("name", "Inconnu")
            info_text = f"Cible: {name}"
            
        if info_text:
            text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.putText(frame, info_text, ((w - text_size[0]) // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
        # Right: FPS
        fps_text = f"{fps:.1f} FPS"
        fps_color = COLOR_GREEN if fps > 15 else (COLOR_YELLOW if fps > 8 else COLOR_RED)
        fps_size = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, fps_text, (w - fps_size[0] - 10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, fps_color, 2)

    def draw(self, frame: np.ndarray, faces: List[FaceResult], state: RobotState, state_info: dict) -> np.ndarray:
        display_frame = frame.copy()
        
        # Update FPS
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
                # Thin white rect around head
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), COLOR_WHITE, 1)
                
            elif state == RobotState.SCAN:
                # Body rectangle (approximate)
                bx, by, bw, bh = max(0, x-w//2), y, w*2, h*3
                cv2.rectangle(display_frame, (bx, by), (bx+bw, by+bh), COLOR_BLUE, 2)
                # Head rectangle
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), COLOR_YELLOW, 2)
                
                # Label above head
                progress = state_info.get("progress", 0)
                text = f"SCAN EN COURS... {int(progress)}%"
                self._put_text_with_background(display_frame, text, (x, y - 10), 0.5, COLOR_BLACK, COLOR_YELLOW)
                
                # Animated scanning bar
                bar_y = y + int(h * (abs(np.sin(now * 5))))
                cv2.line(display_frame, (x, bar_y), (x+w, bar_y), COLOR_YELLOW, 2)
                
            elif state in (RobotState.IDENTIFIED, RobotState.RETREAT):
                color = COLOR_GREEN if state == RobotState.IDENTIFIED else COLOR_ORANGE
                # Body rect
                bx, by, bw, bh = max(0, x-w//2), y, w*2, h*3
                cv2.rectangle(display_frame, (bx, by), (bx+bw, by+bh), color, 2)
                # Head rect
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                
                # Name label
                name = face.name if face.name else "Inconnu"
                self._put_text_with_background(display_frame, name, (x, y - 10), 0.7, COLOR_BLACK, color)
                
                if state == RobotState.RETREAT:
                    self._put_text_with_background(display_frame, "RETRAITE", (x, y + h + 20), 0.6, COLOR_WHITE, COLOR_ORANGE)
                    
            elif state == RobotState.ALERT:
                # Blinking effect
                if int(now * 3.33) % 2 == 0:
                    bx, by, bw, bh = max(0, x-w//2), y, w*2, h*3
                    cv2.rectangle(display_frame, (bx, by), (bx+bw, by+bh), COLOR_RED, 3)
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), COLOR_RED, 3)
                    self._put_text_with_background(display_frame, "⚠ ALERTE ⚠ ELIMINATION !", (x - 20, y - 15), 0.8, COLOR_WHITE, COLOR_RED)
                    
        # Alert frame border
        if state == RobotState.ALERT and int(now * 3.33) % 2 == 0:
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), COLOR_RED, 20)
            cv2.addWeighted(overlay, 0.4, display_frame, 0.6, 0, display_frame)
            
        # Draw FPS counter in bottom-left
        fps_text = f"{self.current_fps:.1f} FPS"
        fps_color = COLOR_GREEN if self.current_fps > 15 else (COLOR_YELLOW if self.current_fps > 8 else COLOR_RED)
        cv2.putText(display_frame, fps_text, (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2)

        return display_frame
