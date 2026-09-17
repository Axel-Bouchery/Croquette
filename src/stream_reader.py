import threading
import time
from typing import Optional
import cv2
import numpy as np
import urllib.request

class StreamReader:
    """Lit le flux MJPEG de la caméra dans un thread séparé."""
    def __init__(self, stream_url: str):
        self.stream_url = stream_url
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._running = False
        self._connected = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Démarre le thread de lecture (daemon)."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_stream, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Arrête le thread de lecture et attend qu'il se termine."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get_frame(self) -> Optional[np.ndarray]:
        """Retourne la dernière frame lue (thread-safe)."""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def is_connected(self) -> bool:
        """Retourne l'état de la connexion au flux MJPEG."""
        return self._connected

    def _read_stream(self) -> None:
        bytes_buffer = b''
        while self._running:
            try:
                # Ouvre le flux avec un timeout de 10s
                stream = urllib.request.urlopen(self.stream_url, timeout=10.0)
                
                if not self._connected:
                    print(f"Connecté au flux MJPEG : {self.stream_url}")
                    self._connected = True

                while self._running:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    
                    bytes_buffer += chunk
                    
                    # Sécurité : vider le buffer s'il dépasse 1MB (pour éviter les fuites de mémoire)
                    if len(bytes_buffer) > 1048576:
                        bytes_buffer = b''
                        continue
                        
                    start = bytes_buffer.find(b'\xff\xd8')
                    end = bytes_buffer.find(b'\xff\xd9')
                    
                    if start != -1 and end != -1:
                        jpg = bytes_buffer[start:end+2]
                        bytes_buffer = bytes_buffer[end+2:]
                        
                        # Décodage de l'image JPEG
                        img_array = np.frombuffer(jpg, dtype=np.uint8)
                        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            with self._lock:
                                self._frame = frame
                
                if self._running:
                    print("Le flux a été interrompu. Tentative de reconnexion...")
                    self._connected = False
                    
            except Exception as e:
                if self._connected:
                    print(f"Erreur ou perte de connexion au flux : {e}")
                    self._connected = False
                
                if self._running:
                    # Attendre 2 secondes avant de retenter la connexion
                    time.sleep(2.0)
