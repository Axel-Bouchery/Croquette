"""Script utilitaire pour encoder les visages connus.

Utilisation:
    python -m src.encode_faces
    
Ce script scanne le dossier 'known_faces/' et entraîne le modèle
de reconnaissance faciale LBPH. Le modèle est sauvegardé pour
utilisation par le programme principal.

Structure attendue:
    known_faces/
    ├── Axel/
    │   ├── photo1.jpg
    │   ├── photo2.jpg
    │   └── photo3.jpg
    └── Autre_Personne/
        ├── photo1.jpg
        └── photo2.jpg
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.face_engine import FaceEngine

def main():
    print("=" * 50)
    print("  Encodage des visages connus - Croquette")
    print("=" * 50)
    print()
    
    config = load_config()
    
    # Check that known_faces directory exists
    if not os.path.isdir(config.known_faces_dir):
        print(f"[ERREUR] Le dossier '{config.known_faces_dir}' n'existe pas.")
        print(f"Créez-le et ajoutez des sous-dossiers avec des photos.")
        print(f"Exemple:")
        print(f"  {config.known_faces_dir}/Axel/photo1.jpg")
        print(f"  {config.known_faces_dir}/Axel/photo2.jpg")
        sys.exit(1)
    
    # Check for subdirectories
    subdirs = [d for d in os.listdir(config.known_faces_dir) 
               if os.path.isdir(os.path.join(config.known_faces_dir, d))]
    if not subdirs:
        print(f"[ERREUR] Aucun sous-dossier trouvé dans '{config.known_faces_dir}'.")
        sys.exit(1)
    
    print(f"Personnes trouvées: {', '.join(subdirs)}")
    print()
    
    # Create engine and train
    engine = FaceEngine(
        confidence_threshold=config.face_confidence_threshold,
        resize_factor=1  # Full resolution for training
    )
    
    count = engine.train_from_directory(config.known_faces_dir)
    
    if count == 0:
        print("[ERREUR] Aucun visage détecté dans les images.")
        print("Assurez-vous que les photos montrent clairement un visage.")
        engine.release()
        sys.exit(1)
    
    # Save model
    engine.save_model(config.model_path, config.labels_path)
    engine.release()
    
    print()
    print(f"Terminé ! {count} visage(s) encodé(s) avec succès.")
    print(f"Modèle sauvegardé: {config.model_path}")
    print(f"Labels sauvegardés: {config.labels_path}")

if __name__ == "__main__":
    main()
