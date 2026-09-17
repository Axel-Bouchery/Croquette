import socket
import threading
from typing import Optional

class RobotController:
    """Contrôleur du robot pour communiquer avec l'ESP32."""
    
    def __init__(self, ip: str, port: int = 80):
        """Initialise le contrôleur du robot."""
        self.ip = ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.lock = threading.Lock()
        self.connected = False

    def connect(self) -> bool:
        """Établit une connexion TCP avec l'ESP32."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.ip, self.port))
            self.connected = True
            print(f"[Robot] Connecté à {self.ip}:{self.port}")
            return True
        except (socket.error, ConnectionRefusedError, socket.timeout) as e:
            print(f"[Robot] Erreur de connexion à {self.ip}:{self.port} : {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Ferme la connexion avec l'ESP32."""
        if self.socket and self.connected:
            try:
                self.socket.close()
            except Exception:
                pass
        self.connected = False
        print("[Robot] Déconnecté")

    def _send_command(self, command: str) -> bool:
        """Envoie une commande de façon sécurisée via le socket TCP."""
        with self.lock:
            if not self.connected:
                if not self.connect():
                    return False
            
            try:
                if self.socket:
                    self.socket.sendall(command.encode('utf-8'))
                    return True
                return False
            except socket.error as e:
                print(f"[Robot] Erreur lors de l'envoi de la commande : {e}")
                self.connected = False
                return False

    def forward(self) -> bool:
        """Fait avancer le robot."""
        return self._send_command("forward\n")

    def backward(self) -> bool:
        """Fait reculer le robot."""
        return self._send_command("backward\n")

    def left(self) -> bool:
        """Fait tourner le robot à gauche."""
        return self._send_command("left\n")

    def right(self) -> bool:
        """Fait tourner le robot à droite."""
        return self._send_command("right\n")

    def stop(self) -> bool:
        """Arrête le robot."""
        return self._send_command("stop\n")

    def spin(self, duration: float = 1.0) -> None:
        """Fait tourner le robot en continu."""
        self.left()

    def retreat(self) -> None:
        """Fait reculer le robot."""
        self.backward()

    @property
    def is_connected(self) -> bool:
        """Retourne l'état de la connexion."""
        return self.connected
