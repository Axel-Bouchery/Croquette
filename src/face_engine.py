import cv2
import numpy as np
import mediapipe as mp
import json
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

@dataclass
class FaceResult:
    head_bbox: Tuple[int, int, int, int]  # (x, y, w, h) of face
    body_bbox: Tuple[int, int, int, int]  # (x, y, w, h) estimated body
    name: Optional[str]  # None = unknown person
    confidence: float     # LBPH confidence (lower = better match)

    @property
    def box(self) -> Tuple[int, int, int, int]:
        return self.head_bbox

class FaceEngine:
    def __init__(self, confidence_threshold: float = 80.0, resize_factor: int = 4):
        self.confidence_threshold = confidence_threshold
        self.resize_factor = resize_factor
        self._recognizer = cv2.face.LBPHFaceRecognizer_create()
        self._label_map: Dict[int, str] = {}
        self._model_loaded: bool = False
        self._use_mediapipe: bool = False
        self._detector = None
        self._cascade = None

        # Tentative d'initialisation de MediaPipe (versions antérieures à 1.0)
        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_detection'):
            try:
                self._mp_face = mp.solutions.face_detection
                self._detector = self._mp_face.FaceDetection(
                    model_selection=0,  # 0 = short range (< 2m), best for robot
                    min_detection_confidence=0.5
                )
                self._use_mediapipe = True
                print("[FaceEngine] Détecteur utilisé : MediaPipe Solutions")
            except Exception:
                self._use_mediapipe = False

        # Fallback automatique sur OpenCV Haar Cascade si MediaPipe solutions n'est pas disponible
        if not self._use_mediapipe:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._cascade = cv2.CascadeClassifier(cascade_path)
            print(f"[FaceEngine] Détecteur utilisé : OpenCV Haar Cascade ({cascade_path})")

    def _detect_faces_boxes(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Détecte les visages et renvoie une liste de boîtes (x, y, w, h)."""
        if img is None or img.size == 0:
            return []

        if self._use_mediapipe and self._detector is not None:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self._detector.process(img_rgb)
            boxes = []
            if results.detections:
                h, w = img.shape[:2]
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    x = int(bboxC.xmin * w)
                    y = int(bboxC.ymin * h)
                    bw = int(bboxC.width * w)
                    bh = int(bboxC.height * h)
                    boxes.append((x, y, bw, bh))
            return boxes
        elif self._cascade is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            detections = self._cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in detections]
        return []

    def train_from_directory(self, known_faces_dir: str) -> int:
        faces = []
        labels = []
        label_id = 0
        total_encoded = 0

        for person_name in os.listdir(known_faces_dir):
            person_dir = os.path.join(known_faces_dir, person_name)
            if not os.path.isdir(person_dir):
                continue
            
            self._label_map[label_id] = person_name
            person_count = 0

            for filename in os.listdir(person_dir):
                img_path = os.path.join(person_dir, filename)
                img = cv2.imread(img_path)
                if img is None:
                    continue

                boxes = self._detect_faces_boxes(img)
                if boxes:
                    x, y, box_w, box_h = boxes[0]
                    face_crop = self._crop_and_prepare_face(img, x, y, box_w, box_h)
                    if face_crop is not None:
                        faces.append(face_crop)
                        labels.append(label_id)
                        person_count += 1
                        total_encoded += 1
            
            print(f"[FaceEngine] Encodage de {person_name}: {person_count} visage(s)")
            label_id += 1

        if len(faces) > 0:
            self._recognizer.train(faces, np.array(labels))

        return total_encoded

    def save_model(self, model_path: str, labels_path: str) -> None:
        self._recognizer.write(model_path)
        with open(labels_path, 'w') as f:
            json.dump(self._label_map, f)
        print(f"[FaceEngine] Modèle sauvegardé avec succès.")

    def load_model(self, model_path: str, labels_path: str) -> bool:
        try:
            self._recognizer.read(model_path)
            with open(labels_path, 'r') as f:
                label_map_str = json.load(f)
            self._label_map = {int(k): v for k, v in label_map_str.items()}
            self._model_loaded = True
            return True
        except FileNotFoundError:
            print(f"[FaceEngine] Erreur : fichiers manquants pour le modèle.")
            return False
        except Exception as e:
            print(f"[FaceEngine] Erreur de chargement: {e}")
            return False

    def detect_and_recognize(self, frame: np.ndarray) -> List[FaceResult]:
        face_results = []
        if frame is None or frame.size == 0:
            return face_results

        h, w = frame.shape[:2]
        small_frame = cv2.resize(frame, (w // self.resize_factor, h // self.resize_factor))
        
        boxes = self._detect_faces_boxes(small_frame)
        if not boxes:
            return face_results

        for (sx, sy, sw, sh) in boxes:
            x = sx * self.resize_factor
            y = sy * self.resize_factor
            box_w = sw * self.resize_factor
            box_h = sh * self.resize_factor
            
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            box_w = max(0, min(box_w, w - x))
            box_h = max(0, min(box_h, h - y))
            
            head_bbox = (x, y, box_w, box_h)
            
            body_w = int(box_w * 2.5)
            body_h = int(box_h * 4.0)
            body_x = int(x + box_w / 2 - body_w / 2)
            body_y = y
            
            body_x = max(0, min(body_x, w - 1))
            body_y = max(0, min(body_y, h - 1))
            body_w = max(0, min(body_w, w - body_x))
            body_h = max(0, min(body_h, h - body_y))
            
            body_bbox = (body_x, body_y, body_w, body_h)
            
            name = None
            confidence = 999.0
            
            if self._model_loaded:
                face_crop = self._crop_and_prepare_face(frame, x, y, box_w, box_h)
                if face_crop is not None:
                    try:
                        label, conf = self._recognizer.predict(face_crop)
                        confidence = conf
                        if confidence < self.confidence_threshold:
                            name = self._label_map.get(label, None)
                    except cv2.error:
                        pass
            
            face_results.append(FaceResult(head_bbox, body_bbox, name, confidence))

        return face_results

    def release(self) -> None:
        if self._detector is not None and hasattr(self._detector, 'close'):
            self._detector.close()

    def _crop_and_prepare_face(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        fh, fw = frame.shape[:2]

        margin_x = max(20, int(w * 0.15))
        margin_y = max(20, int(h * 0.20))

        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(fw, x + w + margin_x)
        y2 = min(fh, y + h + margin_y)

        cw = x2 - x1
        ch = y2 - y1

        if cw < 20 or ch < 20:
            return None

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Conserve une zone carrée pour le modèle LBPH, plus stable sur les images de test et en flux réel.
        size = max(cw, ch)
        pad = int((size - min(cw, ch)) / 2)
        if cw > ch:
            pad_top = 0
            pad_bottom = 0
            pad_left = pad
            pad_right = pad
        else:
            pad_top = pad
            pad_bottom = pad
            pad_left = 0
            pad_right = 0

        padded = cv2.copyMakeBorder(
            gray,
            pad_top, pad_bottom,
            pad_left, pad_right,
            cv2.BORDER_CONSTANT,
            value=0
        )

        resized = cv2.resize(padded, (220, 220), interpolation=cv2.INTER_AREA)
        equalized = cv2.equalizeHist(resized)
        return equalized
