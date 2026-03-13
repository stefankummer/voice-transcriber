# 🎤 Voice Transcriber — v0.2 Beta

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
- **Auto-enter overlay warning** — Visual indicator when auto-enter is active, with one-click disable
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

## Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch
python voice_transcriber.py
```

> 📖 **Full documentation** — See [doc.en.md](doc.en.md) (English) or [doc.fr.md](doc.fr.md) (French) for detailed installation instructions (including Python setup), configuration guide, and troubleshooting.

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

---

*Voice Transcriber v0.2 Beta — Stefan Kummer*
