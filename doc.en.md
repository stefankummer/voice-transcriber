# 📖 Voice Transcriber — Documentation

Complete installation and usage guide for Voice Transcriber.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installing Python](#installing-python)
3. [Installing Voice Transcriber](#installing-voice-transcriber)
4. [Launching the Application](#launching-the-application)
5. [Configuration](#configuration)
6. [Daily Usage](#daily-usage)
7. [System Tray Menu](#system-tray-menu)
8. [Windows Automatic Startup](#windows-automatic-startup)
9. [API Benchmark](#api-benchmark)
10. [Application Files](#application-files)
11. [Dependencies](#dependencies)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Windows 10 or 11**
- **Python 3.10+** (see section below if Python is not yet installed)
- **A working microphone**
- **Optional**: [ffmpeg](https://ffmpeg.org/download.html) for audio compression (reduces upload size to cloud APIs)
- **Optional**: an NVIDIA GPU with CUDA to accelerate local transcription

---

## Installing Python

> If Python is already installed on your machine, skip to the next section.

### Step 1: Download Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the **"Download Python 3.x.x"** button (the latest stable version)
3. Download the Windows installer (`.exe` file)

### Step 2: Install Python

1. Run the downloaded `.exe` file
2. **⚠️ IMPORTANT**: Check the **"Add Python to PATH"** checkbox at the bottom of the installation window
3. Click **"Install Now"**
4. Wait for the installation to complete

### Step 3: Verify the installation

Open a terminal (`Win` key → type `cmd` → Enter) and type:

```bash
python --version
```

You should see something like `Python 3.12.x`. If not, restart your computer and try again.

---

## Installing Voice Transcriber

### Step 1: Download the project

**Option A — with Git:**
```bash
git clone https://github.com/stefankummer/voice-transcriber.git
cd voice-transcriber
```

**Option B — without Git:**
1. Go to the [project's GitHub page](https://github.com/stefankummer/voice-transcriber)
2. Click the green **"Code"** button → **"Download ZIP"**
3. Extract the archive to a folder of your choice

### Step 2: Create a virtual environment

Open a terminal in the project folder and type:

```bash
python -m venv .venv
```

### Step 3: Activate the virtual environment

```bash
.venv\Scripts\activate
```

> You should see `(.venv)` at the beginning of the command line.

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

> Installation may take a few minutes depending on your internet connection.

### Installing ffmpeg (optional)

ffmpeg compresses audio (WAV → OGG Opus) before sending it to cloud APIs, reducing file size and latency.

1. Download ffmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract the archive and add the `bin` folder containing `ffmpeg.exe` to your system PATH
3. Verify with: `ffmpeg -version`

---

## Launching the Application

### Normal launch (with console)

```bash
python voice_transcriber.py
```

A console window will remain open (useful for debugging).

### Silent launch (no console)

```bash
pythonw voice_transcriber.pyw
```

The application starts in the background, visible only via the 🎤 icon in the Windows notification area (system tray).

---

## Configuration

All configuration is done via the graphical interface.

**To access it**: Right-click the tray icon → **⚙️ Settings**

### General Settings

| Setting | Description | Default |
|---|---|---|
| Keyboard shortcut | Key combination to start/stop recording | `ctrl+space` |
| Local Whisper model | Local transcription engine (used as fallback) | `medium` |
| Hardware acceleration | CPU, CUDA (NVIDIA GPU), or Auto | `auto` |
| Transcription language | Primary language of your recordings | `fr` |
| Recording retention | How long audio files are kept (in minutes) | `120` |
| HuggingFace token | For model downloads (optional) | — |

### API Profiles (cloud services)

Each profile defines a cloud transcription service:

| Field | Description |
|---|---|
| **Name** | Name displayed in the menu |
| **Protocol** | OpenAI, AssemblyAI, Rev.ai, Gemini, or Gemini Live |
| **API URL** | Service endpoint |
| **API Key** | Authentication key provided by the service |
| **Model** | Model identifier (leave blank if not applicable) |

Profiles are managed from the interface: add, edit, enable/disable, test, delete.

The local Whisper engine is **always available** as a fallback, even without any API profile configured.

> Configuration is stored in `profiles.json` (contains your API keys, do not share).

---

## Daily Usage

### Basic Workflow

1. **Press the shortcut** (default `Ctrl+Space`) → Recording starts
   - An animated red overlay appears at the top of the screen
   - Other applications' volume is automatically reduced
2. **Speak normally**
3. **Press the shortcut again** → Recording stops
   - A blue overlay indicates transcription is in progress
   - Word count updates in real-time (local mode)
4. **The text is automatically**:
   - Pasted at the cursor position (Ctrl+V)
   - Copied to the clipboard
5. A green **✓ Done** overlay confirms success

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Space` (configurable) | Start / stop recording |
| `Escape` | Cancel recording or transcription in progress |

### Auto-enter

The **Auto-enter** option (toggleable from the tray menu) automatically presses Enter after pasting text. Useful for chats and messaging apps.

When this option is enabled, an amber warning banner appears below the recording overlay with a **[disable]** link for quick toggle-off.

### History

Recent transcriptions are accessible from the tray menu:
- **Re-transcribe** a recording with a different profile
- **Copy** a previous transcription to the clipboard

---

## System Tray Menu

Right-click the 🎤 icon in the notification area:

| Entry | Action |
|---|---|
| 🎤 Record / ⏹ Stop | Start or stop recording |
| API Profiles | Switch between services (radio buttons) |
| ⏎ Auto enter | Automatically press Enter after paste |
| 🚀 Windows auto-start | Enable/disable launch at startup |
| 📋 Recordings | Re-transcribe or copy from history |
| 📂 Open folder | Open the recordings folder |
| ⚙️ Settings | Open the configuration interface |
| 📖 Documentation | Open this file |
| Quit | Close the application |

---

## Windows Automatic Startup

### From the tray menu

Right-click the icon → **🚀 Windows auto-start** → check/uncheck.

### From the command line

```bash
# Add to Windows startup
python setup_startup.py install

# Remove from Windows startup
python setup_startup.py uninstall
```

---

## API Benchmark

Compares the performance of all active API profiles on the same audio file.

### From the graphical interface

⚙️ Settings → **🔬 Benchmark**

### From the command line

```bash
python voice_transcriber.py --benchmark path/to/file.wav
```

> ⚠️ Each profile will consume API tokens/credits during the benchmark.

---

## Application Files

| File | Role |
|---|---|
| `voice_transcriber.py` | Main application (recording, transcription, tray, overlay) |
| `voice_transcriber.pyw` | Silent launcher (no console) |
| `config_gui.py` | Configuration graphical interface |
| `locales.py` | Translations (English / French) |
| `setup_startup.py` | Windows auto-start install/uninstall |
| `profiles.json` | API profiles and settings (not versioned, contains API keys) |
| `usage.json` | Daily usage statistics (not versioned) |
| `requirements.txt` | Python dependencies |
| `audio.png` / `audio.ico` | Application icon |
| `recordings/` | Audio recordings and transcriptions folder |

---

## Dependencies

### Required (installed via pip)

| Package | Role |
|---|---|
| `faster-whisper` | Local transcription (fallback) |
| `requests` | HTTP calls to cloud APIs |
| `websockets` | Gemini Live audio streaming |
| `sounddevice` | Microphone audio capture |
| `numpy` | Audio buffer management |
| `pyperclip` | Clipboard copy |
| `keyboard` | Global keyboard shortcuts |
| `pystray` | System tray icon |
| `Pillow` | Tray icon loading |
| `pycaw` | Audio ducking (Windows) |
| `comtypes` | Required by pycaw for COM interface |

### Optional

| Tool | Role |
|---|---|
| `ffmpeg` | WAV → OGG Opus audio compression (reduces upload size) |
| `torch` (CUDA) | GPU acceleration for faster-whisper |

---

## Troubleshooting

### "Python is not recognized as a command"

Python was not added to PATH during installation. Solutions:
1. Reinstall Python and check **"Add Python to PATH"**
2. Or manually add the Python folder to your system PATH

### The keyboard shortcut doesn't work

- Check that another application isn't using the same shortcut
- Change the shortcut from ⚙️ Settings → Keyboard shortcut
- The application may require administrator privileges for certain shortcuts

### Error "No module named ..."

The virtual environment is probably not activated:
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Local transcription is slow

- Use a smaller model (tiny, base, small) from the settings
- Enable CUDA if you have a compatible NVIDIA GPU
- The first launch downloads the model, which may take some time

### Text is not pasted in the right place

- Make sure the target window is in the foreground when the transcription completes
- Some applications may block automatic paste (Ctrl+V)

---

*Voice Transcriber v0.2 Beta — Stefan Kummer*
