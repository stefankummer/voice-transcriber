# 🎤 Voice Transcriber — v0.1 Beta

Windows voice dictation with multi-provider cloud transcription and local fallback.
Record your voice with a hotkey, the transcribed text is automatically pasted at your cursor position.

> [!WARNING]
> **Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The author is not responsible for any damages, data loss, API costs, or any other issues arising from the use of this software. Use at your own risk.

## Features

- **Language support** — English (en) and French (fr)
- **Multi-API cloud** — AssemblyAI, OpenAI, Google Gemini, Gemini Live (WebSocket), Rev.ai
- **Local fallback** — Automatic faster-whisper if cloud fails
- **Configurable profiles** — Switch between services from the tray icon
- **Visual overlay** — Animated status indicator at the top of the screen (recording, transcribing, done, error)
- **Audio ducking** — Progressive volume reduction of other apps during recording
- **Auto-paste** — Transcribed text is pasted at cursor + copied to clipboard
- **Auto-enter** — Option to automatically press Enter after paste (chat, messaging)
- **History** — Clipboard history + re-transcribe from tray menu
- **Audio compression** — WAV → OGG Opus conversion via ffmpeg (if available)
- **Benchmark** — Compare all API profiles' performance in one click
- **Auto-purge** — `.wav`/`.txt` files and logs are cleaned up automatically
- **Windows startup** — Add/remove from automatic startup
- **Cancellation** — Escape cancels recording or transcription in progress

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Space` (default, configurable) | Start / stop recording |
| `Escape` | Cancel recording or transcription in progress |

## Supported Protocols

| Protocol | Description | Compatible Services |
|---|---|---|
| **OpenAI Compatible** | Direct audio file upload, immediate response | OpenAI, Groq, Together AI, FastWhisper Server |
| **AssemblyAI** | Upload + async polling | AssemblyAI |
| **Rev.ai** | Multipart upload + polling + transcript retrieval | Rev.ai |
| **Google Gemini** | Base64-encoded audio in a multimodal prompt | Gemini Flash, Gemini Pro |
| **Gemini Live** | Real-time audio streaming via WebSocket | Gemini 2.5 Flash Native Audio |

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Automatic Startup (optional)

```bash
# Add to Windows startup
python setup_startup.py install

# Remove from Windows startup
python setup_startup.py uninstall
```

This option is also available from the tray icon menu (🚀 Windows auto-start).

## Configuration

All configuration is done via the graphical interface, accessible from the tray icon:
**Right-click the icon → ⚙️ Configuration**

### General Settings

| Setting | Description | Default |
|---|---|---|
| Keyboard shortcut | Key combination to start/stop recording | `ctrl+space` |
| Local Whisper model | Local transcription engine (fallback) | `medium` |
| Hardware acceleration | CPU, CUDA, or Auto | `auto` |
| Language | Primary recording language | `fr` |
| Retention | How long audio files are kept (minutes) | `120` |
| HuggingFace token | For model downloads (optional) | — |

### API Profiles

Each profile defines a cloud transcription service with:
- **Name** displayed in the menu
- **Communication protocol** (see table above)
- **API endpoint URL**
- **API key** for authentication
- **Model** identifier

Profiles are managed from the GUI: add, edit, enable/disable, test, delete.
The local Whisper engine is always available as a fallback.

Configuration is stored in `profiles.json` (not versioned, contains API keys).

## Usage

```bash
# Normal launch
python voice_transcriber.py

# Silent launch (no console)
pythonw voice_transcriber.pyw
```

### Workflow

1. **Hotkey** → Recording starts (red overlay + audio ducking)
2. Speak normally
3. **Hotkey** → Recording stops, transcription begins (blue overlay)
4. Text is automatically pasted at cursor and copied to clipboard
5. **Escape** → Cancel at any time

### Tray Menu (right-click the icon)

| Entry | Action |
|---|---|
| 🎤 Record / ⏹ Stop | Start or stop recording |
| API Profiles | Switch between services (radio buttons) |
| ⏎ Auto enter | Automatically press Enter after paste |
| 🚀 Windows auto-start | Enable/disable launch at startup |
| 📋 Recordings | Re-transcribe a file or copy from history |
| 📂 Open folder | Open the recordings folder |
| ⚙️ Configuration | Open the configuration GUI |
| 📖 Documentation | Open this README file |
| Quit | Close the application |

## Architecture

```
Keyboard shortcut (start)
  └─ Microphone (16kHz, int16, mono) + audio ducking

Keyboard shortcut (stop)
  ├─ Active cloud profile?
  │   ├─ OpenAI  → POST multipart /v1/audio/transcriptions
  │   ├─ AssemblyAI → upload + poll /v2/transcript
  │   ├─ Rev.ai  → upload + poll + GET transcript
  │   ├─ Gemini  → POST base64 multimodal generateContent
  │   └─ Gemini Live → WebSocket streaming PCM 16kHz
  │
  ├─ On failure → fallback to local faster-whisper
  │   └─ Quick cleanup (capitalization, punctuation, spacing)
  │
  ├─ Automatic retry (max 2 attempts)
  ├─ Result → Ctrl+V at cursor + clipboard
  └─ Save .wav + .txt in recordings/
```

## File Structure

| File | Role |
|---|---|
| `voice_transcriber.py` | Main application (recording, transcription, tray, overlay) |
| `voice_transcriber.pyw` | Silent launcher (no console) |
| `config_gui.py` | Configuration graphical interface |
| `setup_startup.py` | Windows auto-start install/uninstall |
| `profiles.json` | API profiles and settings (not versioned, contains API keys) |
| `usage.json` | Daily usage statistics (not versioned) |
| `requirements.txt` | Python dependencies |
| `audio.png` / `audio.ico` | Application icon |
| `recordings/` | Audio recordings and transcriptions folder |

## Dependencies

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
| `comtypes` | Required by pycaw for COM |

### Optional

| Tool | Role |
|---|---|
| `ffmpeg` | WAV → OGG Opus compression (reduces upload size) |
| `torch` (CUDA) | GPU acceleration for faster-whisper |

## Benchmark

Benchmark compares all active API profiles' performance on the same audio file.

**From the GUI**: ⚙️ Configuration → 🔬 Benchmark
**From the command line**:
```bash
python voice_transcriber.py --benchmark path/to/file.wav
```

---

*Voice Transcriber v0.1 Beta — Stefan Kummer*
