import time
from enum import Enum
from typing import List, Optional, Dict, Any
from src.face_engine import FaceResult
from src.robot_controller import RobotController

class RobotState(Enum):
    PATROL = "PATROL"         # Mouvement normal, évitement d'obstacles par Arduino
    SCAN = "SCAN"             # Visage inconnu détecté, tentative d'identification
    IDENTIFIED = "IDENTIFIED" # Visage reconnu
    ALERT = "ALERT"           # Échec de l'identification, rotation d'alarme
    RETREAT = "RETREAT"       # Personne connue trouvée, recule

class StateMachine:
    """Machine à états pour gérer le comportement du robot selon la détection faciale."""

    def __init__(self, robot: RobotController, scan_timeout: float = 5.0, alert_rotations: int = 10, retreat_duration: float = 3.0):
        self.robot = robot
        self.scan_timeout = scan_timeout
        self.alert_rotations = alert_rotations
        self.retreat_duration = retreat_duration
        self._state = RobotState.PATROL
        
        self._state_start_time: float = 0.0
        self._identified_name: Optional[str] = None
        self._spin_count: int = 0
        self._spin_start_time: float = 0.0
        self._last_command_time: float = 0.0
        
        self._last_command: str = ""
        self._alert_spin_duration = 2.0  # Durée approximative d'une rotation complète (en secondes)

    def _send_command(self, command: str, force: bool = False):
        """Envoie une commande au robot avec limitation de taux (0.3s)."""
        current_time = time.time()
        if force or command != self._last_command or (current_time - self._last_command_time) > 0.3:
            if command == "stop":
                self.robot.stop()
            elif command == "backward":
                self.robot.backward()
            elif command == "left":
                self.robot.left()
            self._last_command = command
            self._last_command_time = current_time

    def update(self, faces: List[FaceResult]) -> RobotState:
        """Met à jour l'état du robot en fonction des visages détectés."""
        current_time = time.time()
        elapsed = current_time - self._state_start_time

        has_unknown = any(f.name is None for f in faces)
        known_faces = [f for f in faces if f.name is not None]
        has_known = len(known_faces) > 0

        if self._state == RobotState.PATROL:
            # En PATROL, on ne fait rien sauf si on détecte un visage
            if has_known:
                self._state = RobotState.RETREAT
                self._state_start_time = current_time
                self._identified_name = known_faces[0].name
                self._send_command("backward", force=True)
            elif has_unknown:
                self._state = RobotState.SCAN
                self._state_start_time = current_time
                self._send_command("stop", force=True)

        elif self._state == RobotState.SCAN:
            # Le robot est arrêté, on scanne pour identifier
            if has_known:
                self._state = RobotState.IDENTIFIED
                self._state_start_time = current_time
                self._identified_name = known_faces[0].name
            elif len(faces) == 0:
                # La personne est partie
                self._state = RobotState.PATROL
                self._state_start_time = current_time
            elif elapsed > self.scan_timeout:
                # Le délai est écoulé et toujours inconnu
                self._state = RobotState.ALERT
                self._state_start_time = current_time
                self._send_command("left", force=True)

        elif self._state == RobotState.IDENTIFIED:
            # Affichage de l'identité pendant 1 seconde
            if elapsed > 1.0:
                self._state = RobotState.RETREAT
                self._state_start_time = current_time
                self._send_command("backward", force=True)

        elif self._state == RobotState.ALERT:
            # Rotation d'alarme
            self._send_command("left")
            total_alert_duration = self.alert_rotations * self._alert_spin_duration
            if elapsed > total_alert_duration:
                self._state = RobotState.PATROL
                self._state_start_time = current_time
                self._send_command("stop", force=True)

        elif self._state == RobotState.RETREAT:
            # Recul après identification
            self._send_command("backward")
            if elapsed > self.retreat_duration:
                self._state = RobotState.PATROL
                self._state_start_time = current_time
                self._send_command("stop", force=True)

        return self._state

    def get_state(self) -> RobotState:
        """Renvoie l'état actuel."""
        return self._state

    def get_state_info(self) -> Dict[str, Any]:
        """Renvoie les informations sur l'état actuel et sa progression."""
        current_time = time.time()
        elapsed = current_time - self._state_start_time
        
        info = {
            "state": self._state.value,
            "elapsed": elapsed,
            "identified_name": self._identified_name,
            "name": self._identified_name
        }

        if self._state == RobotState.SCAN:
            progress = min(100.0, max(0.0, (elapsed / self.scan_timeout) * 100))
            info["scan_progress"] = progress
            info["progress"] = progress
            info["scan_remaining"] = max(0.0, self.scan_timeout - elapsed)
        elif self._state == RobotState.ALERT:
            total_duration = self.alert_rotations * self._alert_spin_duration
            progress = min(100.0, max(0.0, (elapsed / total_duration) * 100))
            info["alert_progress"] = progress
            info["progress"] = progress
        elif self._state == RobotState.RETREAT:
            progress = min(100.0, max(0.0, (elapsed / self.retreat_duration) * 100))
            info["retreat_progress"] = progress
            info["progress"] = progress
            
        return info

    def reset(self) -> None:
        """Réinitialise la machine à états."""
        self._state = RobotState.PATROL
        self._state_start_time = time.time()
        self._identified_name = None
        self._send_command("stop", force=True)
