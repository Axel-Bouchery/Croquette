"""Programme principal de reconnaissance faciale pour le robot Croquette.

Utilisation:
    python -m src.main
    
Contrôles:
    q / ESC  — Quitter le programme
    s        — Prendre une capture d'écran
    r        — Réinitialiser la machine à états (retour PATROL)
    p        — Pause/reprise de l'analyse faciale
"""
import sys
import os
import time
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.stream_reader import StreamReader  
from src.face_engine import FaceEngine, FaceResult
from src.robot_controller import RobotController
from src.state_machine import StateMachine, RobotState
from src.gui_overlay import GUIOverlay

def main():
    print("Croquette - Reconnaissance Faciale")
    
    config = load_config()
    stream = StreamReader(config.stream_url)
    face_engine = FaceEngine(config.face_confidence_threshold, config.resize_factor)
    robot = RobotController(config.robot_ip, config.command_port)
    state_machine = StateMachine(robot, config.scan_timeout, config.alert_rotations, config.retreat_duration)
    gui = GUIOverlay()
    
    print("[Main] Initialisation du modèle de visages...")
    if not face_engine.load_model(config.model_path, config.labels_path):
        print("[Attention] Aucun modèle chargé, la reconnaissance faciale ne fonctionnera pas.")
        print("[Astuce] Exécutez 'python -m src.encode_faces' en premier.")
        
    print("[Main] Connexion au robot...")
    if not robot.connect():
        print("[Attention] Échec de connexion au robot, poursuite en mode caméra seule.")
        
    print("[Main] Démarrage du flux vidéo...")
    stream.start()
    
    # Wait for first frame (up to 10 seconds)
    timeout = time.time() + 10.0
    first_frame = None
    while time.time() < timeout:
        first_frame = stream.get_frame()
        if first_frame is not None:
            break
        time.sleep(0.1)
        
    if first_frame is None:
        print("[Erreur] Impossible de récupérer le flux vidéo après 10 secondes. Arrêt.")
        stream.stop()
        robot.disconnect()
        return

    frame_count = 0
    faces = []
    paused = False
    running = True
    
    cv2.namedWindow("Croquette - Reconnaissance Faciale", cv2.WINDOW_NORMAL)

    try:
        while running:
            frame = stream.get_frame()
            if frame is None:
                # Si le flux est déconnecté ou autre, afficher un écran noir
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Connexion perdue...", (150, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Croquette - Reconnaissance Faciale", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    running = False
                time.sleep(0.01)
                continue
            
            frame_count += 1
            
            # Face analysis (with frame skipping for performance)
            if not paused and frame_count % config.frame_skip == 0:
                faces = face_engine.detect_and_recognize(frame)
            
            # Update state machine
            if not paused:
                state = state_machine.update(faces)
            else:
                state = state_machine.get_state()
            
            state_info = state_machine.get_state_info()
            
            # Draw GUI overlay
            display_frame = gui.draw(frame, faces, state, state_info)
            
            # If paused, add PAUSE indicator
            if paused:
                cv2.putText(display_frame, "PAUSE", (display_frame.shape[1]//2 - 60, display_frame.shape[0]//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            # Display
            cv2.imshow("Croquette - Reconnaissance Faciale", display_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                running = False
            elif key == ord('s'):  # screenshot
                filename = f"screenshot_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                print(f"[Main] Capture sauvegardée: {filename}")
            elif key == ord('r'):  # reset
                state_machine.reset()
                faces = []
                print("[Main] Machine à états réinitialisée")
            elif key == ord('p'):  # pause
                paused = not paused
                if paused:
                    state_machine.reset()
                    print("[Main] Analyse en pause")
                else:
                    print("[Main] Analyse reprise")

    except KeyboardInterrupt:
        print("\n[Main] Interruption utilisateur (Ctrl+C).")
    finally:
        print("\n[Main] Arrêt en cours...")
        stream.stop()
        robot.stop()  # Stop motors
        robot.disconnect()
        face_engine.release()
        cv2.destroyAllWindows()
        print("[Main] Programme terminé.")

if __name__ == "__main__":
    main()
