# Croquette

Robot de surveillance et d'interaction visuelle basé sur Python, OpenCV et la reconnaissance faciale.

## Sommaire

- [Présentation](#présentation)
- [Fonctionnement général](#fonctionnement-général)
- [Fonctionnalités](#fonctionnalités)
  - [Flux vidéo](#flux-vidéo)
  - [Détection et reconnaissance faciale](#détection-et-reconnaissance-faciale)
  - [Licorne animée](#licorne-animée)
  - [Machine à états](#machine-à-états)
  - [Interface graphique](#interface-graphique)
  - [Pilotage du robot](#pilotage-du-robot)
- [Architecture du projet](#architecture-du-projet)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entraînement du modèle](#entraînement-du-modèle)
- [Lancement](#lancement)
- [Contrôles clavier](#contrôles-clavier)
- [Dépannage](#dépannage)
- [Licence](#licence)

## Présentation

Croquette est un projet de robot autonome qui combine la lecture d'un flux vidéo, la détection et la reconnaissance de visages, une machine à états comportementale, une interface OpenCV et le pilotage d'un châssis via TCP.

Le robot surveille son environnement, identifie les visages connus et adapte son comportement selon la situation : patrouille, analyse, identification, recul ou alerte. Une licorne est également affichée dans le flux vidéo : elle se promène lorsqu'aucun visage n'est détecté et se place sur le visage lorsqu'une personne apparaît.

## Fonctionnement général

À chaque image reçue, le programme suit cette chaîne de traitement :

1. `StreamReader` récupère une image depuis le flux MJPEG.
2. `FaceEngine` recherche les visages et tente d'identifier les personnes reconnues.
3. `StateMachine` met à jour l'état du robot à partir des résultats de détection.
4. `GUIOverlay` dessine les annotations, les informations de statut et la licorne.
5. `RobotController` envoie au robot les commandes correspondant à l'état courant.
6. OpenCV affiche l'image finale dans une fenêtre.

L'analyse faciale peut être effectuée seulement sur certaines images grâce à `FRAME_SKIP`, afin de conserver un affichage fluide.

## Fonctionnalités

### Flux vidéo

Le module `src/stream_reader.py` lit un flux MJPEG HTTP, généralement fourni par une ESP32-CAM. La lecture s'effectue dans un thread séparé afin que les ralentissements réseau ne bloquent pas complètement l'interface ou l'analyse.

L'adresse du flux est construite à partir de `ROBOT_IP` et `ROBOT_STREAM_PORT`. Si le flux est indisponible, le programme affiche un message de connexion perdue et continue de surveiller la reconnexion.

### Détection et reconnaissance faciale

Le module `src/face_engine.py` réalise deux opérations distinctes :

1. **Détection** : MediaPipe Face Detection est utilisé lorsqu'il est disponible. Le programme utilise automatiquement le classifieur Haar Cascade d'OpenCV comme solution de secours.
2. **Reconnaissance** : lorsqu'un modèle a été chargé, l'image de chaque visage détecté est préparée puis comparée avec le modèle LBPH d'OpenCV.

Pour chaque visage, le moteur produit une boîte `(x, y, largeur, hauteur)`, une boîte corporelle estimée, un nom éventuel et un score de confiance. Un visage dont le score dépasse `FACE_CONFIDENCE_THRESHOLD` reste considéré comme inconnu.

La reconnaissance nécessite au préalable un entraînement avec des photos rangées par personne dans `known_faces/`. Les fichiers générés sont `face_model.yml` et `face_labels.json`.

### Licorne animée

L'animation est gérée par `src/gui_overlay.py` et utilise l'image `assets/unicorn.png`.

Le comportement est le suivant :

- **Aucun visage détecté** : la licorne avance horizontalement de gauche à droite et flotte légèrement verticalement.
- **Un visage détecté** : la licorne est redimensionnée en fonction de la boîte du visage et centrée sur celui-ci.
- **Plusieurs visages détectés** : elle suit le plus grand visage, généralement celui qui est le plus proche de la caméra.
- **Visage disparu** : la licorne reprend sa promenade à partir de sa dernière position connue.

L'image est superposée au flux avec son canal alpha lorsqu'il existe, ce qui permet de conserver un fond transparent. Le fichier doit être placé exactement ici :

```text
assets/unicorn.png
```

L'overlay est dessiné après les annotations faciales afin que la tête de licorne soit visible au-dessus du visage détecté.

### Machine à états

Le module `src/state_machine.py` coordonne le comportement du robot. Les principaux états sont :

- `PATROL` : surveillance ou déplacement normal ;
- `SCAN` : analyse d'un visage inconnu pendant la durée configurée ;
- `IDENTIFIED` : un visage connu a été reconnu ;
- `RETREAT` : recul ou éloignement après identification ;
- `ALERT` : alerte visuelle et rotation défensive lorsqu'un visage reste inconnu trop longtemps.

Les temporisations et le nombre de rotations sont réglables dans `.env`. La touche `r` permet de remettre la machine à états en `PATROL`.

### Interface graphique

Le module `src/gui_overlay.py` enrichit chaque image avec :

- l'état actuel du robot ;
- les boîtes autour des visages ;
- la progression du scan ;
- le nom d'une personne reconnue ;
- une bordure clignotante en cas d'alerte ;
- le nombre d'images par seconde ;
- la licorne animée.

L'image annotée est ensuite affichée par `src/main.py` avec `cv2.imshow()`.

### Pilotage du robot

`src/robot_controller.py` communique avec le châssis par TCP. Les commandes envoyées sont des textes terminés par un saut de ligne :

- `forward` : avancer ;
- `backward` : reculer ;
- `left` : pivoter à gauche ;
- `right` : pivoter à droite ;
- `stop` : arrêter les moteurs.

Si la connexion TCP échoue, l'application continue en mode caméra seule : la détection et l'interface restent disponibles, mais les moteurs ne sont pas pilotés.

## Architecture du projet

```text
Croquette/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── known_faces/
│   ├── Axel/
│   │   ├── photo1.jpg
│   │   └── ...
│   └── AutrePersonne/
│       └── ...
├── face_model.yml
├── face_labels.json
├── assets/
│   └── unicorn.png
├── src/
│   ├── config.py
│   ├── encode_faces.py
│   ├── face_engine.py
│   ├── gui_overlay.py
│   ├── main.py
│   ├── robot_controller.py
│   ├── state_machine.py
│   └── stream_reader.py
└── tests/
```

## Prérequis

- Python 3.9+ recommandé ;
- caméra MJPEG accessible via HTTP, par exemple une ESP32-CAM ;
- robot ou périphérique avec serveur TCP pour le pilotage moteur ;
- ordinateur connecté au même réseau que la caméra et le robot.

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Axel-Bouchery/Croquette.git
cd Croquette
```

### 2. Créer un environnement virtuel

Linux / macOS :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Configuration

Créez un fichier `.env` à la racine du projet :

```ini
ROBOT_IP=192.168.4.1
ROBOT_STREAM_PORT=81
ROBOT_COMMAND_PORT=80

SCAN_TIMEOUT=5.0
ALERT_ROTATIONS=10
RETREAT_DURATION=3.0

FACE_CONFIDENCE_THRESHOLD=80.0
KNOWN_FACES_DIR=known_faces
MODEL_PATH=face_model.yml
LABELS_PATH=face_labels.json

FRAME_SKIP=3
RESIZE_FACTOR=4
```

### Paramètres importants

- `ROBOT_IP` : adresse IP du robot ou du module de commande ;
- `ROBOT_STREAM_PORT` : port du flux vidéo MJPEG ;
- `ROBOT_COMMAND_PORT` : port TCP de commande des moteurs ;
- `SCAN_TIMEOUT` : durée maximale d'analyse d'un visage inconnu ;
- `ALERT_ROTATIONS` : nombre de rotations effectuées pendant l'alerte ;
- `RETREAT_DURATION` : durée du recul ;
- `FACE_CONFIDENCE_THRESHOLD` : seuil LBPH ; une valeur plus basse est plus stricte ;
- `FRAME_SKIP` : nombre d'images entre deux analyses faciales ;
- `RESIZE_FACTOR` : facteur de réduction utilisé avant la détection.

## Entraînement du modèle

Ajoutez un sous-dossier par personne dans `known_faces/` :

```text
known_faces/
├── Axel/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
├── Jules/
│   ├── photo1.jpg
│   └── photo2.jpg
└── ...
```

Utilisez de préférence 5 à 15 photos variées par personne, avec un visage visible et suffisamment éclairé. Lancez ensuite :

```bash
python -m src.encode_faces
```

Le script détecte les visages dans les photos, entraîne le modèle LBPH et génère `face_model.yml` ainsi que `face_labels.json`.

## Lancement

Démarrez le programme principal avec :

```bash
python -m src.main
```

Le programme charge la configuration, initialise la détection, ouvre le flux vidéo, tente de se connecter au robot puis affiche les images annotées.

## Contrôles clavier

Dans la fenêtre OpenCV :

| Touche | Action |
|---|---|
| `q` ou `Esc` | Quitter le programme et arrêter proprement les moteurs |
| `s` | Prendre une capture d'écran |
| `r` | Réinitialiser la machine à états |
| `p` | Mettre en pause ou reprendre l'analyse faciale |

## Dépannage

### Le flux vidéo ne démarre pas

- Vérifiez la connexion réseau au robot ;
- testez le flux dans un navigateur avec `http://IP:PORT/stream` ;
- vérifiez `ROBOT_IP` et `ROBOT_STREAM_PORT` dans `.env`.

### La licorne ne s'affiche pas

- vérifiez que le fichier existe exactement à `assets/unicorn.png` ;
- vérifiez que le fichier est une image PNG lisible ;
- lancez le programme depuis la racine du projet avec `python -m src.main` ;
- vérifiez la console : le programme affiche une alerte si le fichier est introuvable.

### La licorne ne suit pas le visage

- vérifiez que les rectangles de détection apparaissent autour des visages ;
- augmentez la luminosité ou rapprochez le visage de la caméra ;
- réduisez `RESIZE_FACTOR` si le visage est trop petit ;
- réduisez `FRAME_SKIP` pour actualiser plus souvent la position.

### Le robot ne répond pas

- vérifiez `ROBOT_IP` et `ROBOT_COMMAND_PORT` ;
- confirmez que le serveur TCP de l'ESP32 est actif ;
- le programme peut continuer en mode caméra seule si la connexion échoue.

### Les visages ne sont pas reconnus

- vérifiez la qualité et le nombre des images dans `known_faces/` ;
- relancez `python -m src.encode_faces` ;
- ajustez `FACE_CONFIDENCE_THRESHOLD`.

### Le programme est lent

- augmentez `FRAME_SKIP` ;
- augmentez `RESIZE_FACTOR` ;
- utilisez des images de caméra moins grandes ;
- vérifiez que l'ordinateur dispose des dépendances OpenCV et MediaPipe adaptées.

## Licence

Projet personnel et expérimental de robotique et de vision par ordinateur. Le code est fourni à titre éducatif et peut être adapté pour des usages personnels ou de démonstration.
