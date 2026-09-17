import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    robot_ip: str = "192.168.4.1"
    stream_port: int = 81
    command_port: int = 80
    scan_timeout: float = 5.0
    alert_rotations: int = 10
    retreat_duration: float = 3.0
    face_confidence_threshold: float = 80.0
    known_faces_dir: str = "known_faces"
    model_path: str = "face_model.yml"
    labels_path: str = "face_labels.json"
    frame_skip: int = 3
    resize_factor: int = 4

    @property
    def stream_url(self) -> str:
        return f"http://{self.robot_ip}:{self.stream_port}/stream"

    @property
    def command_url(self) -> str:
        return f"http://{self.robot_ip}:{self.command_port}"

def load_config() -> Config:
    """Charge la configuration depuis le fichier .env avec des valeurs par défaut."""
    load_dotenv()
    
    return Config(
        robot_ip=os.getenv("ROBOT_IP", "192.168.4.1"),
        stream_port=int(os.getenv("ROBOT_STREAM_PORT", "81")),
        command_port=int(os.getenv("ROBOT_COMMAND_PORT", "80")),
        scan_timeout=float(os.getenv("SCAN_TIMEOUT", "5.0")),
        alert_rotations=int(os.getenv("ALERT_ROTATIONS", "10")),
        retreat_duration=float(os.getenv("RETREAT_DURATION", "3.0")),
        face_confidence_threshold=float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "80.0")),
        known_faces_dir=os.getenv("KNOWN_FACES_DIR", "known_faces"),
        model_path=os.getenv("MODEL_PATH", "face_model.yml"),
        labels_path=os.getenv("LABELS_PATH", "face_labels.json"),
        frame_skip=int(os.getenv("FRAME_SKIP", "3")),
        resize_factor=int(os.getenv("RESIZE_FACTOR", "4"))
    )
