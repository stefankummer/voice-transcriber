# 📖 Voice Transcriber — Documentation

Guide complet d'installation et d'utilisation pour Voice Transcriber.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Installer Python](#installer-python)
3. [Installer Voice Transcriber](#installer-voice-transcriber)
4. [Lancer l'application](#lancer-lapplication)
5. [Configuration](#configuration)
6. [Utilisation au quotidien](#utilisation-au-quotidien)
7. [Menu système (tray icon)](#menu-système-tray-icon)
8. [Démarrage automatique Windows](#démarrage-automatique-windows)
9. [Benchmark des APIs](#benchmark-des-apis)
10. [Fichiers de l'application](#fichiers-de-lapplication)
11. [Dépendances](#dépendances)
12. [Résolution de problèmes](#résolution-de-problèmes)

---

## Prérequis

- **Windows 10 ou 11**
- **Python 3.10+** (voir section ci-dessous si Python n'est pas encore installé)
- **Un microphone** fonctionnel
- **Optionnel** : [ffmpeg](https://ffmpeg.org/download.html) pour la compression audio (réduit la taille des envois vers les APIs cloud)
- **Optionnel** : un GPU NVIDIA avec CUDA pour accélérer la transcription locale

---

## Installer Python

> Si Python est déjà installé sur votre machine, passez à la section suivante.

### Étape 1 : Télécharger Python

1. Rendez-vous sur [python.org/downloads](https://www.python.org/downloads/)
2. Cliquez sur le bouton **"Download Python 3.x.x"** (la dernière version stable)
3. Téléchargez l'installateur Windows (fichier `.exe`)

### Étape 2 : Installer Python

1. Lancez le fichier `.exe` téléchargé
2. **⚠️ IMPORTANT** : Cochez la case **"Add Python to PATH"** en bas de la fenêtre d'installation
3. Cliquez sur **"Install Now"**
4. Attendez la fin de l'installation

### Étape 3 : Vérifier l'installation

Ouvrez un terminal (touche `Win` → tapez `cmd` → Entrée) et tapez :

```bash
python --version
```

Vous devriez voir quelque chose comme `Python 3.12.x`. Si ce n'est pas le cas, redémarrez votre ordinateur et réessayez.

---

## Installer Voice Transcriber

### Étape 1 : Télécharger le projet

**Option A — avec Git :**
```bash
git clone https://github.com/stefankummer/voice-transcriber.git
cd voice-transcriber
```

**Option B — sans Git :**
1. Allez sur la [page GitHub du projet](https://github.com/stefankummer/voice-transcriber)
2. Cliquez sur le bouton vert **"Code"** → **"Download ZIP"**
3. Décompressez l'archive dans un dossier de votre choix

### Étape 2 : Créer un environnement virtuel

Ouvrez un terminal dans le dossier du projet et tapez :

```bash
python -m venv .venv
```

### Étape 3 : Activer l'environnement virtuel

```bash
.venv\Scripts\activate
```

> Vous devriez voir `(.venv)` apparaître au début de la ligne de commande.

### Étape 4 : Installer les dépendances

```bash
pip install -r requirements.txt
```

> L'installation peut prendre quelques minutes selon votre connexion internet.

### Installation de ffmpeg (optionnel)

ffmpeg permet de compresser l'audio (WAV → OGG Opus) avant l'envoi aux APIs cloud, réduisant la taille des fichiers et la latence.

1. Téléchargez ffmpeg depuis [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extrayez l'archive et placez le dossier `bin` contenant `ffmpeg.exe` dans votre PATH système
3. Vérifiez avec : `ffmpeg -version`

---

## Lancer l'application

### Lancement normal (avec console)

```bash
python voice_transcriber.py
```

Une fenêtre console restera ouverte (utile pour débugger).

### Lancement silencieux (sans console)

```bash
pythonw voice_transcriber.pyw
```

L'application démarre en arrière-plan, visible uniquement par l'icône 🎤 dans la zone de notification (tray) de Windows.

---

## Configuration

Toute la configuration se fait via l'interface graphique.

**Pour y accéder** : Clic droit sur l'icône tray → **⚙️ Configuration**

### Paramètres généraux

| Paramètre | Description | Valeur par défaut |
|---|---|---|
| Raccourci clavier | Combinaison pour démarrer / arrêter l'enregistrement | `ctrl+space` |
| Modèle Whisper local | Moteur de transcription local (utilisé en fallback) | `medium` |
| Accélération matérielle | CPU, CUDA (GPU NVIDIA), ou Auto | `auto` |
| Langue de transcription | Langue principale de vos enregistrements | `fr` |
| Rétention des enregistrements | Durée de conservation des fichiers audio (en minutes) | `120` |
| Token HuggingFace | Pour les téléchargements de modèles (optionnel) | — |

### Profils API (services cloud)

Chaque profil définit un service de transcription cloud :

| Champ | Description |
|---|---|
| **Nom** | Nom affiché dans le menu |
| **Protocole** | OpenAI, AssemblyAI, Rev.ai, Gemini, ou Gemini Live |
| **URL de l'API** | Point d'entrée du service |
| **Clé API** | Clé d'authentification fournie par le service |
| **Modèle** | Identifiant du modèle (laisser vide si non applicable) |

Les profils se gèrent depuis l'interface : ajouter, modifier, activer/désactiver, tester, supprimer.

Le moteur Whisper local est **toujours disponible** comme fallback, même sans aucun profil API configuré.

> La configuration est stockée dans `profiles.json` (contient vos clés API, ne pas partager).

---

## Utilisation au quotidien

### Workflow de base

1. **Appuyez sur le raccourci** (par défaut `Ctrl+Space`) → L'enregistrement démarre
   - Un overlay rouge animé apparaît en haut de l'écran
   - Le volume des autres applications est réduit automatiquement
2. **Parlez normalement**
3. **Appuyez à nouveau sur le raccourci** → L'enregistrement s'arrête
   - Un overlay bleu indique que la transcription est en cours
   - Le nombre de mots transcrits s'affiche en temps réel (mode local)
4. **Le texte est automatiquement** :
   - Collé à la position du curseur (Ctrl+V)
   - Copié dans le presse-papiers
5. Un overlay vert **✓ Terminé** confirme le succès

### Raccourcis clavier

| Raccourci | Action |
|---|---|
| `Ctrl+Space` (configurable) | Démarrer / arrêter l'enregistrement |
| `Escape` | Annuler l'enregistrement ou la transcription en cours |

### Auto-enter

L'option **Auto-enter** (activable depuis le menu tray) appuie automatiquement sur Entrée après le collage du texte. Utile pour les chats et messageries.

Quand cette option est activée, un avertissement ambré s'affiche sous l'overlay d'enregistrement avec un lien **[désactiver]** pour la couper rapidement.

### Historique

Les dernières transcriptions sont accessibles depuis le menu tray :
- **Re-transcrire** un enregistrement avec un profil différent
- **Copier** une transcription précédente dans le presse-papiers

---

## Menu système (tray icon)

Clic droit sur l'icône 🎤 dans la zone de notification :

| Entrée | Action |
|---|---|
| 🎤 Enregistrer / ⏹ Arrêter | Démarrer ou arrêter l'enregistrement |
| Profils API | Changer de service (boutons radio) |
| ⏎ Auto enter | Appuyer automatiquement sur Entrée après le collage |
| 🚀 Démarrage auto Windows | Activer/désactiver le lancement au démarrage |
| 📋 Enregistrements | Re-transcrire ou copier depuis l'historique |
| 📂 Ouvrir le dossier | Ouvrir le dossier des enregistrements |
| ⚙️ Configuration | Ouvrir l'interface de configuration |
| 📖 Documentation | Ouvrir ce fichier |
| Quitter | Fermer l'application |

---

## Démarrage automatique Windows

### Depuis le menu tray

Clic droit sur l'icône → **🚀 Démarrage auto Windows** → cocher/décocher.

### Depuis la ligne de commande

```bash
# Ajouter au démarrage Windows
python setup_startup.py install

# Retirer du démarrage Windows
python setup_startup.py uninstall
```

---

## Benchmark des APIs

Compare les performances de tous les profils API actifs sur un même fichier audio.

### Depuis l'interface graphique

⚙️ Configuration → **🔬 Benchmark**

### Depuis la ligne de commande

```bash
python voice_transcriber.py --benchmark chemin/vers/fichier.wav
```

> ⚠️ Chaque profil consommera des tokens/crédits API pendant le benchmark.

---

## Fichiers de l'application

| Fichier | Rôle |
|---|---|
| `voice_transcriber.py` | Application principale (enregistrement, transcription, tray, overlay) |
| `voice_transcriber.pyw` | Lanceur silencieux (sans console) |
| `config_gui.py` | Interface graphique de configuration |
| `locales.py` | Traductions (anglais / français) |
| `setup_startup.py` | Installation / suppression du démarrage auto Windows |
| `profiles.json` | Profils API et paramètres (non versionné, contient les clés API) |
| `usage.json` | Statistiques d'utilisation quotidienne (non versionné) |
| `requirements.txt` | Dépendances Python |
| `audio.png` / `audio.ico` | Icône de l'application |
| `recordings/` | Dossier des enregistrements et transcriptions |

---

## Dépendances

### Requises (installées via pip)

| Package | Rôle |
|---|---|
| `faster-whisper` | Transcription locale (fallback) |
| `requests` | Appels HTTP vers les APIs cloud |
| `websockets` | Streaming audio Gemini Live |
| `sounddevice` | Capture audio du microphone |
| `numpy` | Gestion des buffers audio |
| `pyperclip` | Copie dans le presse-papiers |
| `keyboard` | Raccourcis clavier globaux |
| `pystray` | Icône dans la zone de notification |
| `Pillow` | Chargement de l'icône tray |
| `pycaw` | Réduction du volume des autres apps (Windows) |
| `comtypes` | Requis par pycaw pour l'interface COM |

### Optionnels

| Outil | Rôle |
|---|---|
| `ffmpeg` | Compression audio WAV → OGG Opus (réduit la taille des envois) |
| `torch` (CUDA) | Accélération GPU pour faster-whisper |

---

## Résolution de problèmes

### "Python n'est pas reconnu comme commande"

Python n'a pas été ajouté au PATH lors de l'installation. Solutions :
1. Réinstaller Python en cochant **"Add Python to PATH"**
2. Ou ajouter manuellement le dossier Python au PATH système

### Le raccourci clavier ne fonctionne pas

- Vérifiez qu'un autre logiciel n'utilise pas le même raccourci
- Changez le raccourci depuis ⚙️ Configuration → Raccourci clavier
- L'application nécessite les droits d'administrateur pour certains raccourcis

### Erreur "No module named ..."

L'environnement virtuel n'est probablement pas activé :
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### La transcription locale est lente

- Utilisez un modèle plus petit (tiny, base, small) depuis la configuration
- Activez CUDA si vous avez un GPU NVIDIA compatible
- Le premier lancement télécharge le modèle, ce qui peut prendre du temps

### Le texte n'est pas collé au bon endroit

- Assurez-vous que la fenêtre cible est bien au premier plan au moment où la transcription se termine
- Certaines applications peuvent bloquer le collage automatique (Ctrl+V)

---

*Voice Transcriber v0.2 Beta — Stefan Kummer*
