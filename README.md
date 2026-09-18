# Croquette

Robot de surveillance et d'interaction visuelle basé sur Python, OpenCV et la reconnaissance faciale.

## Sommaire

- [Présentation](#présentation)
- [Composants du robot](#composants-du-robot)
  - [Électronique et contrôle](#électronique-et-contrôle)
  - [Motorisation et propulsion](#motorisation-et-propulsion)
  - [Capteurs et modules](#capteurs-et-modules)
  - [Structure et alimentation](#structure-et-alimentation)
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

Croquette est un robot mobile de surveillance basé sur un châssis **Conqueror Robot Tank**. Le projet combine la lecture d'un flux vidéo, la détection et la reconnaissance de visages, une machine à états comportementale, une interface OpenCV et le pilotage du châssis via TCP.

Le robot surveille son environnement, identifie les visages connus et adapte son comportement selon la situation : patrouille, analyse, identification, recul ou alerte. Une licorne est affichée dans le flux vidéo : elle se promène lorsqu'aucun visage n'est détecté et se place sur le visage lorsqu'une personne apparaît.

## Composants du robot

Le robot repose sur un châssis à chenilles **Conqueror Robot Tank**, équipé d'une caméra orientable et de plusieurs modules de contrôle et de détection.

### Électronique et contrôle

- **Carte de contrôle principale** : Arduino UNO R3, responsable de la logique embarquée et du contrôle des périphériques.
- **Carte d'extension** : I/O Extension Board, qui simplifie le câblage et la distribution de l'alimentation vers les différents modules.
- **Pilote de moteurs** : double pont en H de type DRV8835, utilisé pour commander indépendamment les deux moteurs à courant continu.
- **Caméra et Wi-Fi** : caméra OV2640 associée à un module ESP32-WROVER pour la transmission du flux vidéo en Wi-Fi et les échanges UART avec l'électronique du robot.

Dans l'architecture logicielle, l'ordinateur exécute la détection et la reconnaissance faciale. Il reçoit le flux vidéo de l'ESP32-WROVER et peut envoyer les commandes de déplacement au contrôleur via TCP.

### Motorisation et propulsion

- **Deux moteurs à courant continu** avec réducteur 1:48.
- **Deux chenilles en caoutchouc** pour se déplacer sur différents types de surfaces.
- **Roues motrices**, roues libres et galets de tension pour guider les chenilles.
- **Deux servomoteurs SG90** pour orienter la caméra selon deux axes : panoramique et inclinaison.
- **Gimbal caméra 2 DOF** permettant de modifier l'orientation du point de vue sans déplacer le châssis.

Le pilote DRV8835 permet de contrôler la vitesse et le sens de rotation de chaque moteur. En faisant tourner les moteurs dans des sens opposés, le robot peut pivoter sur place.

### Capteurs et modules

- **HC-SR04** : capteur à ultrasons destiné à mesurer la distance devant le robot et à contribuer à la détection d'obstacles.
- **Module infrarouge multi-voies de suivi de ligne** : installé sous le châssis pour détecter une ligne au sol.
- **Récepteur infrarouge** : permet le pilotage du robot avec une télécommande IR.

Ces composants peuvent être utilisés par le programme embarqué pour ajouter des comportements autonomes, comme l'évitement d'obstacles, le suivi de ligne ou le pilotage manuel. Le programme Python de ce dépôt utilise principalement le flux caméra, la reconnaissance faciale et le contrôle TCP.

### Structure et alimentation

- **Châssis** : plaques latérales, plaque de base et plaques supérieures en acrylique ou en alliage.
- **Suspension** : système à balanciers et amortisseurs pour améliorer la stabilité des chenilles.
- **Alimentation** : boîtier pour batterie lithium 7,4 V composé de deux cellules 18650, avec interrupteur marche/arrêt.
- **Accastillage** : colonnes en laiton, boulons M3/M4, écrous frein et câblage Dupont.

> Respectez les caractéristiques électriques des cartes, moteurs et servomoteurs. Une batterie lithium doit être utilisée avec un support et une protection adaptés.

## Fonctionnement général

À chaque image reçue, le programme suit cette chaîne de traitement :

1. `StreamReader` récupère une image depuis le flux MJPEG de l'ESP32-WROVER.
2. `FaceEngine` recherche les visages et tente d'identifier les personnes reconnues.
3. `StateMachine` met à jour l'état du robot à partir des résultats de détection.
4. `GUIOverlay` dessine les annotations, les informations de statut et la licorne.
5. `RobotController` envoie au robot les commandes correspondant à l'état courant.
6. OpenCV affiche l'image finale dans une fenêtre.

L'analyse faciale peut être effectuée seulement sur certaines images grâce à `FRAME_SKIP`, afin de conserver un affichage fluide.

## Fonctionnalités

### Flux vidéo

Le module `src/stream_reader.py` lit un flux MJPEG HTTP, généralement fourni par la caméra OV2640 reliée à l'ESP32-WROVER. La lecture s'effectue dans un thread séparé afin que les ralentissements réseau ne bloquent pas complètement l'interface ou l'analyse.

L'adresse du flux est construite à partir de `ROBOT_IP` et `ROBOT_STREAM_PORT`. Si le flux est indisponible, le programme affiche un message de connexion perdue.

### Détection et reconnaissance faciale

Le module `src/face_engine.py` réalise deux opérations distinctes :

1. **Détection** : MediaPipe Face Detection est utilisé lorsqu'il est disponible. Le programme utilise automatiquement le classifieur Haar Cascade d'OpenCV comme solution de secours.
2. **Reconnaissance** : lorsqu'un modèle a été chargé, l'image de chaque visage détecté est préparée puis comparée avec le modèle LBPH d'OpenCV.

Pour chaque visage, le moteur produit une boîte `(x, y, largeur, hauteur)`, une boîte corporelle estimée, un nom éventuel et un score de confiance. La reconnaissance nécessite un entraînement avec des photos rangées par personne dans `known_faces/`.

### Licorne animée

L'animation est gérée par `src/gui_overlay.py` et utilise `assets/unicorn.png`.

- **Aucun visage détecté** : la licorne avance horizontalement et flotte légèrement verticalement.
- **Un visage détecté** : elle est redimensionnée et centrée sur la tête détectée.
- **Plusieurs visages** : elle suit le plus grand visage, généralement le plus proche.
- **Visage disparu** : elle reprend sa promenade à partir de sa dernière position.

Le PNG est superposé avec son canal alpha afin de conserver la transparence. Le fichier doit se trouver exactement ici :

```text
assets/unicorn.png
```

### Machine à états

Le module `src/state_machine.py` coordonne le comportement du robot :

- `PATROL` : surveillance ou déplacement normal ;
- `SCAN` : analyse d'un visage inconnu ;
- `IDENTIFIED` : visage connu reconnu ;
- `RETREAT` : recul ou éloignement ;
- `ALERT` : alerte visuelle et rotation défensive.

Les temporisations et le nombre de rotations sont réglables dans `.env`.

### Interface graphique

`src/gui_overlay.py` ajoute à chaque image l'état du robot, les boîtes des visages, la progression du scan, le nom reconnu, les alertes, le FPS et la licorne animée. L'image est affichée par `src/main.py` avec `cv2.imshow()`.

### Pilotage du robot

`src/robot_controller.py` communique avec le châssis par TCP. Les commandes envoyées sont `forward`, `backward`, `left`, `right` et `stop`, terminées par un saut de ligne.

Si la connexion TCP échoue, l'application continue en mode caméra seule : la détection et l'interface restent disponibles, mais les moteurs ne sont pas pilotés.

## Architecture du projet

```text
Croquette/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── known_faces/
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
- caméra OV2640/ESP32-WROVER diffusant un flux MJPEG HTTP ;
- robot Conqueror Robot Tank assemblé ;
- réseau local commun entre l'ordinateur, la caméra et le robot ;
- serveur TCP disponible sur le robot pour le pilotage.

## Installation

```bash
git clone https://github.com/Axel-Bouchery/Croquette.git
cd Croquette
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

## Entraînement du modèle

Ajoutez un sous-dossier par personne dans `known_faces/`, avec 5 à 15 photos variées et suffisamment éclairées, puis lancez :

```bash
python -m src.encode_faces
```

Le script génère `face_model.yml` et `face_labels.json`.

## Lancement

```bash
python -m src.main
```

Le programme charge la configuration, ouvre le flux vidéo, initialise la détection, tente de se connecter au robot puis affiche les images annotées.

## Contrôles clavier

| Touche | Action |
|---|---|
| `q` ou `Esc` | Quitter et arrêter proprement les moteurs |
| `s` | Prendre une capture d'écran |
| `r` | Réinitialiser la machine à états |
| `p` | Mettre en pause ou reprendre l'analyse faciale |

## Dépannage

### Le flux vidéo ne démarre pas

Vérifiez l'alimentation de l'ESP32-WROVER, la connexion Wi-Fi, `ROBOT_IP`, `ROBOT_STREAM_PORT` et l'URL `http://IP:PORT/stream`.

### La licorne ne s'affiche pas

Vérifiez que `assets/unicorn.png` existe, qu'il est lisible et que le programme est lancé depuis la racine avec `python -m src.main`.

### La licorne ne suit pas le visage

Vérifiez que les rectangles de détection apparaissent. Améliorez l'éclairage, réduisez `RESIZE_FACTOR` ou `FRAME_SKIP` si le visage est trop petit ou si le suivi est peu fréquent.

### Le robot ne répond pas

Vérifiez `ROBOT_IP`, `ROBOT_COMMAND_PORT`, l'alimentation de la carte Arduino et du pilote DRV8835, ainsi que la disponibilité du serveur TCP de l'ESP32. Le programme peut continuer en mode caméra seule.

### Les visages ne sont pas reconnus

Relancez `python -m src.encode_faces`, vérifiez `known_faces/` et ajustez `FACE_CONFIDENCE_THRESHOLD`.

### Le programme est lent

Augmentez `FRAME_SKIP` et `RESIZE_FACTOR`, ou réduisez la résolution du flux vidéo.

## Licence

Projet personnel et expérimental de robotique et de vision par ordinateur. Le code est fourni à titre éducatif et peut être adapté pour des usages personnels ou de démonstration.
