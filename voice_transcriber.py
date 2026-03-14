"""
Voice Transcriber — Press configurable hotkey to record, transcribe via cloud
APIs (AssemblyAI, OpenAI, Gemini, Rev.ai) or locally with faster-whisper.

Usage:
  1. pip install -r requirements.txt
  2. python voice_transcriber.py
  3. Press the configured hotkey (default: Ctrl+Space) to start recording,
     press again to stop.
  4. The transcription is pasted at the cursor position and copied to clipboard.
  5. Use the tray icon to switch profiles, access history, and configure settings.
"""

import os
import sys
import io
import wave
import time
import logging
import threading
import subprocess
import json
from datetime import datetime, date
import numpy as np
import sounddevice as sd
import pyperclip
import keyboard
import pystray
from PIL import Image, ImageDraw, ImageFont
from locales import t, set_language

# ─── Logging (file-based, no console needed) ─────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "voice_transcriber.log")

# Purge log if it's from a previous day
if os.path.isfile(LOG_FILE):
    log_mtime = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).date()
    if log_mtime < date.today():
        open(LOG_FILE, "w").close()  # truncate

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
log = logging.getLogger("VoiceTranscriber")

# Windows audio ducking (pycaw)
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    log.warning("pycaw not available — audio ducking disabled.")

# ─── Configuration ───────────────────────────────────────────────────────────
PROFILES_FILE = os.path.join(SCRIPT_DIR, "profiles.json")

def _load_config() -> dict:
    """Load configuration from profiles.json."""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"settings": {}, "profiles": {}, "default": "local"}

def _load_all_profiles() -> tuple[dict, str, dict]:
    """Load profiles + settings from profiles.json. Returns (profiles, default, settings)."""
    config = _load_config()
    settings = config.get("settings", {})
    profiles: dict[str, dict] = {}
    default_profile = config.get("default", "local")

    for name, pdata in config.get("profiles", {}).items():
        if pdata.get("enabled", True):
            profiles[name] = pdata

    # Always have "local"
    profiles["local"] = {"label": "Whisper Local", "url": "", "key": "", "model": "", "type": "local", "enabled": True}
    return profiles, default_profile, settings

_profiles_result = _load_all_profiles()
api_profiles = _profiles_result[0]
active_api_profile = _profiles_result[1]
_settings = _profiles_result[2]

# Apply settings
WHISPER_MODEL_SIZE = _settings.get("whisper_model", "medium")
WHISPER_DEVICE = _settings.get("whisper_device", "auto")
WHISPER_LANGUAGE = _settings.get("whisper_language", "fr")
HOTKEY = _settings.get("hotkey", "ctrl+space")

# UI language
set_language(_settings.get("ui_language", "en"))

# HuggingFace token for faster-whisper model downloads
_hf_token = _settings.get("hf_token", "")
if _hf_token:
    os.environ["HF_TOKEN"] = _hf_token

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
BLOCKSIZE = 1024

# Debug / Benchmark
DEBUG_BENCHMARK = False  # Toggled from tray

# ─── Audio ducking settings ──────────────────────────────────────────────────
DUCKING_LEVEL = 0.20
DUCKING_ENABLED = True
DUCKING_FADE_DURATION = 0.5
DUCKING_STEPS = 10

# ─── Recordings directory ────────────────────────────────────────────────────
RECORDINGS_DIR = os.path.join(SCRIPT_DIR, "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)

MAX_WAV_LIFETIME = _settings.get("max_wav_lifetime", 120)
MAX_RETRIES = 2
RETRY_DELAY = 2
USAGE_FILE = os.path.join(SCRIPT_DIR, "usage.json")
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

def _reload_profiles():
    """Reload profiles and settings from disk."""
    global api_profiles, active_api_profile, WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_LANGUAGE, HOTKEY, MAX_WAV_LIFETIME
    api_profiles, new_default, _s = _load_all_profiles()
    # If the active profile no longer exists, switch to the new default
    if active_api_profile not in api_profiles:
        active_api_profile = new_default
    WHISPER_MODEL_SIZE = _s.get("whisper_model", "medium")
    WHISPER_DEVICE = _s.get("whisper_device", "auto")
    WHISPER_LANGUAGE = _s.get("whisper_language", "fr")
    HOTKEY = _s.get("hotkey", "ctrl+space")
    MAX_WAV_LIFETIME = _s.get("max_wav_lifetime", 120)
    set_language(_s.get("ui_language", "en"))
    hf = _s.get("hf_token", "")
    if hf:
        os.environ["HF_TOKEN"] = hf
    log.info("Profiles reloaded: %s", ", ".join(p.get("label", n) for n, p in api_profiles.items()))

# ─── Globals ─────────────────────────────────────────────────────────────────
recording = False
recording_lock = threading.Lock()
audio_frames: list[np.ndarray] = []
sd_stream: sd.InputStream | None = None
overlay_app = None
tk_ready = threading.Event()
shutdown_event = threading.Event()
tray_icon: pystray.Icon | None = None
last_recording_path: str | None = None  # Path to the most recent saved WAV
saved_volumes: dict = {}                  # {session_id: original_volume} for ducking restore
whisper_model = None                      # Lazy-loaded faster-whisper model
MAX_CLIPBOARD_HISTORY = 10
auto_enter = False                         # Auto-press Enter after paste (toggled from tray)
_ffmpeg_available: bool | None = None      # Cached ffmpeg check

# Load clipboard history from saved .txt transcriptions (persist across restarts)
def _load_clipboard_history() -> list[str]:
    """Load recent transcription texts from .txt companion files."""
    history = []
    try:
        txt_files = sorted(
            [f for f in os.listdir(RECORDINGS_DIR) if f.endswith(".txt") and f.startswith("rec_")],
            reverse=True,
        )[:MAX_CLIPBOARD_HISTORY]
        for fname in txt_files:
            fpath = os.path.join(RECORDINGS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text and not text.startswith("❌"):
                    history.append(text)
            except OSError:
                pass
    except OSError:
        pass
    return history

clipboard_history: list[str] = _load_clipboard_history()

# ─── Usage tracking ─────────────────────────────────────────────────────────

def _load_usage() -> dict:
    """Load usage stats from file, reset if date changed."""
    today = date.today().isoformat()
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != today:
            log.info("New day (%s) — resetting usage stats", today)
            return {"date": today, "profiles": {}}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": today, "profiles": {}}

def _save_usage(data: dict):
    """Save usage stats to file."""
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.warning("Failed to save usage.json: %s", e)

def _record_usage(profile_name: str, audio_seconds: float):
    """Record one transcription usage for a profile."""
    data = _load_usage()
    profiles = data.setdefault("profiles", {})
    p = profiles.setdefault(profile_name, {"requests": 0, "seconds": 0.0})
    p["requests"] += 1
    p["seconds"] += audio_seconds
    _save_usage(data)

def _get_usage_str(profile_name: str) -> str:
    """Get usage string like '3 req, 2.1 min' for a profile."""
    data = _load_usage()
    p = data.get("profiles", {}).get(profile_name, {})
    reqs = p.get("requests", 0)
    mins = p.get("seconds", 0.0) / 60
    if reqs == 0:
        return ""
    return f" ({reqs} req, {mins:.1f} min)"

# ─── Cancellation ───────────────────────────────────────────────────────────
cancel_event = threading.Event()                    # set by Escape key to abort


# ═══════════════════════════════════════════════════════════════════════════════
#  Modern Overlay UI (tkinter) — transparent window, animated icons
# ═══════════════════════════════════════════════════════════════════════════════

class OverlayApp:
    """
    Sleek status pill at the top-center of the screen.
    Truly transparent background (no square corners).
    States: hidden → recording (radio waves) → transcribing (spinner) → done / error
    """

    # ── Muted modern palette ─────────────────────────────────────────────
    TRANSPARENT  = "#010101"          # Windows transparent-color key
    PILL_BG      = "#1c1c2e"          # Dark slate pill background
    PILL_BORDER  = "#2e2e48"          # Subtle border
    REC_COLOR    = "#e05c71"          # Muted coral-red
    TRANS_COLOR  = "#7b93db"          # Muted periwinkle-blue
    OK_COLOR     = "#6bc98a"          # Soft sage green
    ERR_COLOR    = "#d97070"          # Muted warm red
    ERR_BG       = "#2a1a24"          # Dark error notification bg
    ERR_BORDER   = "#4a2a3a"          # Error border
    TEXT_COLOR   = "#c8cad8"          # Off-white text
    FONT_FAMILY  = "Segoe UI"

    # ── Layout constants ─────────────────────────────────────────────────
    PILL_W, PILL_H = 340, 46
    ICON_CX = 28                      # Center-x of the icon area
    ICON_CY = 23                      # Center-y (PILL_H // 2)
    TEXT_X  = 54                      # Text start x
    CANCEL_COLOR = "#a0a0b8"          # Muted cancel text

    def __init__(self):
        import tkinter as tk
        self.tk = tk
        self.math = __import__("math")

        # ── Main window (transparent background) ─────────────────────────
        self.root = tk.Tk()
        self.root.title("VoiceTranscriber")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg=self.TRANSPARENT)
        self.root.attributes("-transparentcolor", self.TRANSPARENT)

        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - self.PILL_W) // 2
        self.root.geometry(f"{self.PILL_W}x{self.PILL_H}+{x}+16")

        # ── Canvas ───────────────────────────────────────────────────────
        self.canvas = tk.Canvas(
            self.root, width=self.PILL_W, height=self.PILL_H,
            bg=self.TRANSPARENT, highlightthickness=0, bd=0,
        )
        self.canvas.pack()

        # Pill shape
        self._draw_pill(self.canvas, 0, 0, self.PILL_W, self.PILL_H,
                        fill=self.PILL_BG, outline=self.PILL_BORDER)

        # Status label
        self.label = self.canvas.create_text(
            self.TEXT_X, self.ICON_CY,
            text="", anchor="w",
            font=(self.FONT_FAMILY, 11), fill=self.TEXT_COLOR,
        )

        # ── Notification banner ──────────────────────────────────────────
        notif_w, notif_h = 400, 38
        nx = (screen_w - notif_w) // 2
        ny = 16 + self.PILL_H + 6
        self.notif_root = tk.Toplevel(self.root)
        self.notif_root.overrideredirect(True)
        self.notif_root.attributes("-topmost", True)
        self.notif_root.attributes("-alpha", 0.93)
        self.notif_root.configure(bg=self.TRANSPARENT)
        self.notif_root.attributes("-transparentcolor", self.TRANSPARENT)
        self.notif_root.geometry(f"{notif_w}x{notif_h}+{nx}+{ny}")

        self.notif_canvas = tk.Canvas(
            self.notif_root, width=notif_w, height=notif_h,
            bg=self.TRANSPARENT, highlightthickness=0, bd=0,
        )
        self.notif_canvas.pack()
        self._draw_pill(self.notif_canvas, 0, 0, notif_w, notif_h,
                        fill=self.ERR_BG, outline=self.ERR_BORDER)
        self.notif_text = self.notif_canvas.create_text(
            notif_w // 2, notif_h // 2,
            text="", anchor="center",
            font=(self.FONT_FAMILY, 10), fill=self.ERR_COLOR,
        )
        self.notif_root.withdraw()

        # ── Auto-enter warning banner ─────────────────────────────────────
        # Colors for "enabled" state (warm orange — attention-grabbing)
        self.WARN_ON_BG     = "#2a2418"
        self.WARN_ON_BORDER = "#4a3a28"
        self.WARN_ON_COLOR  = "#d9a050"
        self.WARN_ON_LINK   = "#c0883a"
        # Colors for "disabled" state (muted grey — calm)
        self.WARN_OFF_BG     = "#1e2028"
        self.WARN_OFF_BORDER = "#363848"
        self.WARN_OFF_COLOR  = "#8088a0"
        self.WARN_OFF_LINK   = "#6a7090"

        warn_w, warn_h = 340, 32
        wx = (screen_w - warn_w) // 2
        wy = 16 + self.PILL_H + 6
        self.warn_root = tk.Toplevel(self.root)
        self.warn_root.overrideredirect(True)
        self.warn_root.attributes("-topmost", True)
        self.warn_root.attributes("-alpha", 0.93)
        self.warn_root.configure(bg=self.TRANSPARENT)
        self.warn_root.attributes("-transparentcolor", self.TRANSPARENT)
        self.warn_root.geometry(f"{warn_w}x{warn_h}+{wx}+{wy}")

        self.warn_canvas = tk.Canvas(
            self.warn_root, width=warn_w, height=warn_h,
            bg=self.TRANSPARENT, highlightthickness=0, bd=0,
        )
        self.warn_canvas.pack()
        self.warn_pill = self._draw_pill(self.warn_canvas, 0, 0, warn_w, warn_h,
                        fill=self.WARN_ON_BG, outline=self.WARN_ON_BORDER)
        self.warn_label = self.warn_canvas.create_text(
            warn_w // 2 - 30, warn_h // 2,
            text="", anchor="center",
            font=(self.FONT_FAMILY, 9), fill=self.WARN_ON_COLOR,
        )
        self.warn_link = self.warn_canvas.create_text(
            warn_w // 2 + 95, warn_h // 2,
            text="", anchor="center",
            font=(self.FONT_FAMILY, 9, "underline"), fill=self.WARN_ON_LINK,
        )
        self.warn_canvas.tag_bind(self.warn_link, "<Button-1>", self._on_warn_link_click)
        self.warn_canvas.tag_bind(self.warn_link, "<Enter>",
                                  lambda e: self.warn_canvas.itemconfig(self.warn_link, fill="#ffffff"))
        self.warn_canvas.tag_bind(self.warn_link, "<Leave>",
                                  lambda e: self.warn_canvas.itemconfig(
                                      self.warn_link,
                                      fill=self.WARN_ON_LINK if self._warn_link_action == "disable" else self.WARN_OFF_LINK))
        self._warn_link_action = "disable"  # current action: "disable" or "enable"
        self._warn_auto_hide = None         # pending auto-hide timer for disabled banner
        self.warn_root.withdraw()

        # ── Animation state ──────────────────────────────────────────────
        self._state = "hidden"
        self._anim_after = None
        self._notif_after = None
        self._hide_after = None       # Pending auto-hide timer (done/cancelled)
        self._anim_tick = 0
        self._anim_items = []         # Canvas items for animated icons

        # ── ESC hint + close button (shown during recording) ─────────────
        self.esc_hint = self.canvas.create_text(
            self.PILL_W - 55, self.ICON_CY,
            text="ESC", anchor="e",
            font=(self.FONT_FAMILY, 8), fill="#606078",
        )
        self.canvas.itemconfig(self.esc_hint, state="hidden")

        # Close button (✕)
        self.close_btn = self.canvas.create_text(
            self.PILL_W - 18, self.ICON_CY,
            text="✕", anchor="center",
            font=(self.FONT_FAMILY, 13, "bold"), fill="#606078",
        )
        self.canvas.itemconfig(self.close_btn, state="hidden")
        self.canvas.tag_bind(self.close_btn, "<Button-1>", self._on_close_click)
        self.canvas.tag_bind(self.close_btn, "<Enter>",
                             lambda e: self.canvas.itemconfig(self.close_btn, fill=self.ERR_COLOR))
        self.canvas.tag_bind(self.close_btn, "<Leave>",
                             lambda e: self.canvas.itemconfig(self.close_btn, fill="#606078"))

        # Start hidden
        self.root.withdraw()

    # ── Drawing helpers ──────────────────────────────────────────────────

    def _draw_pill(self, canvas, x1, y1, x2, y2, fill, outline):
        """Draw a pill (stadium) shape. Returns the canvas item ID."""
        r = (y2 - y1) // 2
        pts = [
            x1 + r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1,
        ]
        return canvas.create_polygon(pts, smooth=True, fill=fill, outline=outline, width=1)

    def _clear_anim_items(self):
        for item in self._anim_items:
            self.canvas.delete(item)
        self._anim_items.clear()

    def _blend(self, hex_color, alpha):
        """Blend hex_color toward PILL_BG by alpha (0=bg, 1=full color)."""
        r1, g1, b1 = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r2, g2, b2 = int(self.PILL_BG[1:3], 16), int(self.PILL_BG[3:5], 16), int(self.PILL_BG[5:7], 16)
        r = int(r2 + (r1 - r2) * alpha)
        g = int(g2 + (g1 - g2) * alpha)
        b = int(b2 + (b1 - b2) * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── State transitions ────────────────────────────────────────────────

    def show_recording(self):
        self.root.after(0, self._show_recording)

    def _show_recording(self):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "recording"
        self.canvas.itemconfig(self.label, text=t("overlay.recording"), fill=self.TEXT_COLOR)
        self.canvas.itemconfig(self.esc_hint, state="normal")
        self.canvas.itemconfig(self.close_btn, state="normal")
        self.root.deiconify()
        # Show auto-enter status banner
        if auto_enter:
            self._cancel_warn_auto_hide()
            self.warn_canvas.itemconfig(self.warn_pill, fill=self.WARN_ON_BG, outline=self.WARN_ON_BORDER)
            self.warn_canvas.itemconfig(self.warn_label, text=t("overlay.auto_enter_warning"), fill=self.WARN_ON_COLOR)
            self.warn_canvas.itemconfig(self.warn_link, text=t("overlay.auto_enter_disable"), fill=self.WARN_ON_LINK)
            self._warn_link_action = "disable"
            self.warn_root.deiconify()
        else:
            self._show_warn_disabled()
        self._anim_tick = 0
        self._animate_waves()

    def show_transcribing(self, word_count: int = 0):
        self.root.after(0, lambda: self._show_transcribing(word_count))

    def _show_transcribing(self, word_count: int = 0):
        if self._state != "transcribing":
            self._stop_anim()
            self._cancel_hide_timer()
            self._clear_anim_items()
            self._state = "transcribing"
            self.warn_root.withdraw()
            self.root.deiconify()
            self._anim_tick = 0
            self._animate_spinner()
        if word_count > 0:
            s = "s" if word_count > 1 else ""
            txt = t("overlay.transcribing_words", count=word_count, s=s)
        else:
            txt = t("overlay.transcribing")
        self.canvas.itemconfig(self.label, text=txt, fill=self.TEXT_COLOR)

    def show_cancelled(self):
        self.root.after(0, self._show_cancelled)

    def _show_cancelled(self):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "done"
        self.canvas.itemconfig(self.label, text=t("overlay.cancelled"), fill=self.CANCEL_COLOR)
        self.canvas.itemconfig(self.esc_hint, state="hidden")
        self.canvas.itemconfig(self.close_btn, state="hidden")
        cx, cy = self.ICON_CX, self.ICON_CY
        item = self.canvas.create_line(cx - 4, cy - 4, cx + 4, cy + 4,
                                       fill=self.CANCEL_COLOR, width=2)
        self._anim_items.append(item)
        item2 = self.canvas.create_line(cx + 4, cy - 4, cx - 4, cy + 4,
                                        fill=self.CANCEL_COLOR, width=2)
        self._anim_items.append(item2)
        self.root.deiconify()
        self._hide_after = self.root.after(1500, self._auto_hide)

    def show_done(self):
        self.root.after(0, self._show_done)

    def _show_done(self):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "done"
        self.canvas.itemconfig(self.label, text=t("overlay.done"), fill=self.OK_COLOR)
        self.canvas.itemconfig(self.esc_hint, state="hidden")
        self.canvas.itemconfig(self.close_btn, state="hidden")
        cx, cy = self.ICON_CX, self.ICON_CY
        item = self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                       fill=self.OK_COLOR, outline=self.OK_COLOR)
        self._anim_items.append(item)
        self.root.deiconify()
        self._hide_after = self.root.after(1800, self._auto_hide)

    def show_error(self, message: str):
        self.root.after(0, lambda: self._show_error(message))

    def _show_error(self, message: str):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "error"
        self.canvas.itemconfig(self.label, text=t("overlay.error"), fill=self.ERR_COLOR)
        cx, cy = self.ICON_CX, self.ICON_CY
        item = self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                       fill=self.ERR_COLOR, outline=self.ERR_COLOR)
        self._anim_items.append(item)
        self.root.deiconify()

        short_msg = (message[:65] + "…") if len(message) > 65 else message
        self.notif_canvas.itemconfig(self.notif_text, text=short_msg)
        self.notif_root.deiconify()
        if self._notif_after:
            self.root.after_cancel(self._notif_after)
        self._notif_after = self.root.after(5000, self._hide_all)

    def hide(self):
        self.root.after(0, self._hide)

    def _auto_hide(self):
        """Called by auto-hide timers — only hides if still in done/error state."""
        self._hide_after = None
        if self._state in ("done", "error"):
            self._hide()

    def _cancel_hide_timer(self):
        """Cancel any pending auto-hide timer."""
        if self._hide_after:
            self.root.after_cancel(self._hide_after)
            self._hide_after = None

    def _hide(self):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "hidden"
        self.canvas.itemconfig(self.esc_hint, state="hidden")
        self.canvas.itemconfig(self.close_btn, state="hidden")
        self.warn_root.withdraw()
        self.root.withdraw()

    def _hide_all(self):
        self._hide()
        self.notif_root.withdraw()

    # ── Recording: expanding radio waves ─────────────────────────────────

    def _animate_waves(self):
        if self._state != "recording":
            return

        self._clear_anim_items()
        cx, cy = self.ICON_CX, self.ICON_CY
        self._anim_tick += 1
        num_waves = 3
        max_r = 16
        period = 45

        for i in range(num_waves):
            phase = (self._anim_tick + i * (period // num_waves)) % period
            t = phase / period
            radius = 4 + t * (max_r - 4)
            alpha = max(0.0, 1.0 - t)
            color = self._blend(self.REC_COLOR, alpha * 0.75)
            width = max(1.2, 2.2 * (1 - t))

            arc = self.canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=-45, extent=90, style="arc",
                outline=color, width=width,
            )
            self._anim_items.append(arc)

        # Center dot
        dot = self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                                      fill=self.REC_COLOR, outline=self.REC_COLOR)
        self._anim_items.append(dot)

        self._anim_after = self.root.after(45, self._animate_waves)

    # ── Transcribing: orbiting dots spinner ──────────────────────────────

    def _animate_spinner(self):
        if self._state != "transcribing":
            return

        self._clear_anim_items()
        cx, cy = self.ICON_CX, self.ICON_CY
        self._anim_tick += 1
        math = self.math
        num_dots = 4
        orbit_r = 9
        dot_r = 2.2
        speed = 0.09

        for i in range(num_dots):
            angle = self._anim_tick * speed + i * (2 * math.pi / num_dots)
            dx = cx + orbit_r * math.cos(angle)
            dy = cy + orbit_r * math.sin(angle)
            alpha = 1.0 - i * 0.25
            color = self._blend(self.TRANS_COLOR, alpha)

            dot = self.canvas.create_oval(
                dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r,
                fill=color, outline=color,
            )
            self._anim_items.append(dot)

        self._anim_after = self.root.after(35, self._animate_spinner)

    # ── Animation control ────────────────────────────────────────────────

    def _stop_anim(self):
        if self._anim_after:
            self.root.after_cancel(self._anim_after)
            self._anim_after = None

    def _on_close_click(self, event=None):
        """Called when the ✕ button is clicked."""
        on_cancel()

    def _on_warn_link_click(self, event=None):
        """Dispatch click on the warn banner link to enable/disable."""
        if self._warn_link_action == "disable":
            self._on_disable_auto_enter()
        else:
            self._on_enable_auto_enter()

    def _on_disable_auto_enter(self, event=None):
        """Called when the [disable] link is clicked on the auto-enter banner."""
        global auto_enter
        auto_enter = False
        log.info("Auto enter disabled from overlay")
        self._show_warn_disabled()
        # Refresh tray menu so the checkbox stays in sync
        if tray_icon:
            tray_icon.update_menu()

    def _on_enable_auto_enter(self, event=None):
        """Called when the [enable] link is clicked on the disabled banner."""
        global auto_enter
        auto_enter = True
        log.info("Auto enter enabled from overlay")
        self._cancel_warn_auto_hide()
        # Show the enabled warning banner (persistent while recording)
        self.warn_canvas.itemconfig(self.warn_pill, fill=self.WARN_ON_BG, outline=self.WARN_ON_BORDER)
        self.warn_canvas.itemconfig(self.warn_label, text=t("overlay.auto_enter_warning"), fill=self.WARN_ON_COLOR)
        self.warn_canvas.itemconfig(self.warn_link, text=t("overlay.auto_enter_disable"), fill=self.WARN_ON_LINK)
        self._warn_link_action = "disable"
        self.warn_root.deiconify()
        # Refresh tray menu so the checkbox stays in sync
        if tray_icon:
            tray_icon.update_menu()

    def _show_warn_disabled(self):
        """Show the 'auto-enter disabled' banner with [enable] link, auto-hides after 2s unless recording."""
        self._cancel_warn_auto_hide()
        self.warn_canvas.itemconfig(self.warn_pill, fill=self.WARN_OFF_BG, outline=self.WARN_OFF_BORDER)
        self.warn_canvas.itemconfig(self.warn_label, text=t("overlay.auto_enter_off"), fill=self.WARN_OFF_COLOR)
        self.warn_canvas.itemconfig(self.warn_link, text=t("overlay.auto_enter_enable"), fill=self.WARN_OFF_LINK)
        self._warn_link_action = "enable"
        self.warn_root.deiconify()
        # Only auto-hide if not currently recording (keep visible during recording)
        if self._state != "recording":
            self._warn_auto_hide = self.root.after(2000, self._auto_hide_warn)

    def _auto_hide_warn(self):
        """Auto-hide the disabled banner after timeout."""
        self._warn_auto_hide = None
        self.warn_root.withdraw()

    def _cancel_warn_auto_hide(self):
        """Cancel any pending auto-hide timer for the warn banner."""
        if self._warn_auto_hide:
            self.root.after_cancel(self._warn_auto_hide)
            self._warn_auto_hide = None

    # ── Download indicator ───────────────────────────────────────────────

    def show_downloading(self, model_name: str = ""):
        self.root.after(0, lambda: self._show_downloading(model_name))

    def _show_downloading(self, model_name: str):
        self._stop_anim()
        self._cancel_hide_timer()
        self._clear_anim_items()
        self._state = "transcribing"
        txt = t("overlay.downloading", name=model_name) if model_name else t("overlay.downloading_generic")
        self.canvas.itemconfig(self.label, text=txt, fill=self.TRANS_COLOR)
        self.canvas.itemconfig(self.esc_hint, state="hidden")
        self.canvas.itemconfig(self.close_btn, state="hidden")
        self.root.deiconify()
        self._anim_tick = 0
        self._animate_spinner()

    # ── Lifecycle ────────────────────────────────────────────────────────

    def run(self):
        tk_ready.set()
        self.root.mainloop()

    def destroy(self):
        self.root.after(0, self.root.destroy)


# ═══════════════════════════════════════════════════════════════════════════════
#  Audio Ducking — Progressive fade for other apps’ volume
# ═══════════════════════════════════════════════════════════════════════════════

def _get_audio_sessions():
    """Return a list of (pid, process_name, volume_interface) for all active audio sessions."""
    results = []
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process is None:
            continue
        try:
            vol = session._ctl.QueryInterface(ISimpleAudioVolume)
            results.append((session.Process.pid, session.Process.name(), vol))
        except Exception:
            pass
    return results


def _duck_other_apps():
    """Progressively lower the volume of all other audio sessions."""
    global saved_volumes
    saved_volumes = {}

    if not PYCAW_AVAILABLE or not DUCKING_ENABLED:
        log.info("Ducking skipped (available=%s, enabled=%s)", PYCAW_AVAILABLE, DUCKING_ENABLED)
        return

    import comtypes
    comtypes.CoInitialize()
    try:
        sessions = _get_audio_sessions()
        log.info("Ducking: %d audio sessions found", len(sessions))

        # Collect sessions that have volume > 0
        targets = []  # [(vol_interface, current_volume, target_volume, pid, name)]
        for pid, name, vol in sessions:
            try:
                current = vol.GetMasterVolume()
                if current > 0.0:
                    target = current * DUCKING_LEVEL
                    saved_volumes[pid] = current
                    targets.append((vol, current, target, pid, name))
            except Exception:
                pass

        if not targets:
            return

        # Progressive fade-out in DUCKING_STEPS steps
        step_delay = DUCKING_FADE_DURATION / DUCKING_STEPS
        for step in range(1, DUCKING_STEPS + 1):
            t = step / DUCKING_STEPS  # 0.1 → 1.0
            for vol, current, target, pid, name in targets:
                try:
                    intermediate = current + (target - current) * t
                    vol.SetMasterVolume(intermediate, None)
                except Exception:
                    pass
            time.sleep(step_delay)

        for vol, current, target, pid, name in targets:
            log.info("Ducking %s (PID %d) : %.0f%% → %.0f%%",
                     name, pid, current * 100, target * 100)
    except Exception as e:
        log.warning("Audio ducking error: %s", e)
    finally:
        comtypes.CoUninitialize()


def _restore_other_apps():
    """Progressively restore all ducked audio sessions to their original volume."""
    global saved_volumes

    if not PYCAW_AVAILABLE or not DUCKING_ENABLED or not saved_volumes:
        return

    import comtypes
    comtypes.CoInitialize()
    try:
        sessions = _get_audio_sessions()

        # Build list of sessions to restore
        targets = []  # [(vol_interface, current_volume, original_volume, pid, name)]
        for pid, name, vol in sessions:
            if pid in saved_volumes:
                try:
                    current = vol.GetMasterVolume()
                    original = saved_volumes[pid]
                    targets.append((vol, current, original, pid, name))
                except Exception:
                    pass

        if not targets:
            return

        # Progressive fade-in in DUCKING_STEPS steps
        step_delay = DUCKING_FADE_DURATION / DUCKING_STEPS
        for step in range(1, DUCKING_STEPS + 1):
            t = step / DUCKING_STEPS
            for vol, current, original, pid, name in targets:
                try:
                    intermediate = current + (original - current) * t
                    vol.SetMasterVolume(intermediate, None)
                except Exception:
                    pass
            time.sleep(step_delay)

        for vol, current, original, pid, name in targets:
            log.info("Restored %s (PID %d) → %.0f%%", name, pid, original * 100)
    except Exception as e:
        log.warning("Audio restore error: %s", e)
    finally:
        saved_volumes = {}
        comtypes.CoUninitialize()


# ═══════════════════════════════════════════════════════════════════════════════
#  Audio Recording
# ═══════════════════════════════════════════════════════════════════════════════

def _audio_callback(indata, frames, time_info, status):
    if recording:
        audio_frames.append(indata.copy())


def start_recording():
    global recording, audio_frames, sd_stream

    audio_frames = []

    sd_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=BLOCKSIZE,
        callback=_audio_callback,
    )
    sd_stream.start()
    recording = True

    # Duck other audio sources
    _duck_other_apps()

    if overlay_app:
        overlay_app.show_recording()
    log.info("Recording…")


def stop_recording() -> bytes:
    """Stop recording and return wav_bytes."""
    global recording, sd_stream, last_recording_path

    recording = False
    log.info("Recording stopped.")

    # Restore other audio sources
    _restore_other_apps()

    time.sleep(0.1)
    if sd_stream:
        sd_stream.stop()
        sd_stream.close()
        sd_stream = None

    if not audio_frames:
        return b""

    audio_data = np.concatenate(audio_frames, axis=0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    wav_bytes = buf.getvalue()

    # Save recording to disk
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rec_{ts}.wav"
    filepath = os.path.join(RECORDINGS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(wav_bytes)
    last_recording_path = filepath
    log.info("Recording saved: %s", filepath)

    return wav_bytes


# ═══════════════════════════════════════════════════════════════════════════════
#  Faster-Whisper Transcription (local fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_whisper_model():
    """Lazy-load the faster-whisper model (100% local if already cached)."""
    global whisper_model
    if whisper_model is None:
        from faster_whisper import WhisperModel
        log.info("Loading faster-whisper model '%s' (device=%s)…",
                 WHISPER_MODEL_SIZE, WHISPER_DEVICE)
        device = WHISPER_DEVICE
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "")
        if not compute_type:
            compute_type = "float16" if device == "cuda" else "int8"

        # Try local cache first (no network request)
        try:
            whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=device,
                                         compute_type=compute_type,
                                         local_files_only=True)
        except Exception:
            # Model not cached yet — show download indicator and download
            log.info("Model not cached, downloading…")
            if overlay_app:
                overlay_app.show_downloading(WHISPER_MODEL_SIZE)
            whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=device,
                                         compute_type=compute_type)

        log.info("faster-whisper model loaded (device=%s, compute=%s)",
                 device, compute_type)
    return whisper_model

def _quick_cleanup(text: str) -> str:
    """Fast local text cleanup — capitalize, fix spacing, ensure trailing punctuation."""
    import re
    if not text:
        return text
    text = re.sub(r'[ \t]+', ' ', text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    text = re.sub(r'([.!?])\s+([a-zàâéèêëïîôùûüÿçœæ])',
                  lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    if text and text[-1] not in '.!?…':
        text += '.'
    return text


# ═══════════════════════════════════════════════════════════════════════════════
#  Audio compression (WAV → OGG via ffmpeg)
# ═══════════════════════════════════════════════════════════════════════════════

def _has_ffmpeg() -> bool:
    """Check if ffmpeg is available on the system."""
    global _ffmpeg_available
    if _ffmpeg_available is None:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True,
                           timeout=5, creationflags=_NO_WINDOW)
            _ffmpeg_available = True
            log.info("ffmpeg detected — audio compression enabled")
        except (FileNotFoundError, Exception):
            _ffmpeg_available = False
            log.info("ffmpeg not found — uncompressed WAV upload")
    return _ffmpeg_available


def _compress_audio(wav_bytes: bytes) -> bytes:
    """Compress WAV to OGG Opus via ffmpeg. Falls back to WAV if ffmpeg unavailable."""
    if not _has_ffmpeg():
        return wav_bytes
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", "pipe:0",
             "-c:a", "libopus", "-b:a", "32k",
             "-f", "ogg", "pipe:1"],
            input=wav_bytes, capture_output=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout:
            ratio = len(result.stdout) / len(wav_bytes) * 100
            log.info("Audio compressed: %d → %d bytes (%.0f%%)",
                     len(wav_bytes), len(result.stdout), ratio)
            return result.stdout
    except Exception as e:
        log.warning("Compression failed: %s", e)
    return wav_bytes


# ═══════════════════════════════════════════════════════════════════════════════
#  Cloud API Transcription (multi-provider dispatcher)
# ═══════════════════════════════════════════════════════════════════════════════

def _transcribe_with_api(profile: dict, audio_wav: bytes) -> str:
    """Dispatch to the correct provider based on profile type."""
    api_type = profile.get("type", "assemblyai")
    label = profile.get("label", "API")

    if not profile.get("key"):
        raise RuntimeError(f"API key missing for '{label}'")

    log.info("%s: transcribing (type=%s)…", label, api_type)

    if api_type == "openai":
        return _transcribe_openai(profile, audio_wav)
    elif api_type in ("google", "gemini"):
        return _transcribe_google(profile, audio_wav)
    elif api_type == "gemini_live":
        return _transcribe_gemini_live(profile, audio_wav)
    elif api_type == "revai":
        return _transcribe_revai(profile, audio_wav)
    else:  # assemblyai (default)
        return _transcribe_assemblyai(profile, audio_wav)


# ─── AssemblyAI: upload → create transcript → poll ───────────────────────────

def _transcribe_assemblyai(profile: dict, audio_wav: bytes) -> str:
    import requests as req
    api_url, api_key, model, label = profile["url"], profile["key"], profile["model"], profile["label"]
    headers = {"authorization": api_key}

    upload_data = _compress_audio(audio_wav)

    # Upload
    log.info("%s: uploading (%d bytes)…", label, len(upload_data))
    upload_resp = req.post(f"{api_url}/v2/upload", headers=headers, data=upload_data, timeout=30)
    upload_resp.raise_for_status()
    audio_url = upload_resp.json()["upload_url"]

    # Create transcript
    data = {"audio_url": audio_url, "language_detection": True}
    if model:
        data["speech_models"] = [model]
    resp = req.post(f"{api_url}/v2/transcript", headers=headers, json=data, timeout=15)
    resp.raise_for_status()
    transcript_id = resp.json()["id"]
    log.info("%s: created (id=%s, model=%s)", label, transcript_id, model or "default")

    # Poll
    poll_url = f"{api_url}/v2/transcript/{transcript_id}"
    while True:
        if cancel_event.is_set():
            raise RuntimeError("Cancelled by user")
        result = req.get(poll_url, headers=headers, timeout=10).json()
        if result["status"] == "completed":
            text = result.get("text", "").strip()
            log.info("%s done: %s", label, text[:200])
            return text
        elif result["status"] == "error":
            raise RuntimeError(f"{label} error: {result.get('error', 'unknown')}")
        time.sleep(0.5)


# ─── OpenAI: single POST with multipart form data ───────────────────────

def _transcribe_openai(profile: dict, audio_wav: bytes) -> str:
    import requests as req
    api_url = profile["url"] or "https://api.openai.com"
    api_key = profile["key"]
    model = profile["model"] or "whisper-1"
    label = profile["label"]

    headers = {"Authorization": f"Bearer {api_key}"}

    # Compress audio
    upload_data = _compress_audio(audio_wav)
    ext = "ogg" if upload_data[:4] == b"OggS" else "wav"

    files = {"file": (f"audio.{ext}", upload_data, f"audio/{ext}")}
    data = {"model": model}

    log.info("%s: sending (%d bytes, model=%s)…", label, len(upload_data), model)
    resp = req.post(
        f"{api_url}/v1/audio/transcriptions",
        headers=headers,
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json().get("text", "").strip()
    log.info("%s done: %s", label, text[:200])
    return text


# ─── Google Gemini API: inline audio + generateContent ───────────────────

def _transcribe_google(profile: dict, audio_wav: bytes) -> str:
    import requests as req
    import base64

    api_key = profile["key"]
    model = profile["model"] or "gemini-2.0-flash"
    label = profile["label"]
    api_url = profile.get("url") or "https://generativelanguage.googleapis.com"

    # Compress audio for faster upload
    upload_data = _compress_audio(audio_wav)
    is_ogg = upload_data[:4] == b"OggS"
    mime_type = "audio/ogg" if is_ogg else "audio/wav"
    audio_b64 = base64.b64encode(upload_data).decode()

    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_b64,
                    }
                },
                {
                    "text": (
                        "Transcris cet audio mot pour mot, avec la ponctuation "
                        "et les majuscules. Réponds UNIQUEMENT avec la transcription, "
                        "sans commentaire ni explication."
                    )
                },
            ]
        }],
        "generationConfig": {
            "temperature": 0.0,
        },
    }

    url = f"{api_url}/v1beta/models/{model}:generateContent?key={api_key}"
    log.info("%s : envoi (%d bytes, model=%s)…", label, len(upload_data), model)

    resp = req.post(url, json=payload, timeout=60)
    resp.raise_for_status()

    result = resp.json()
    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"{label}: no candidates in response")

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    log.info("%s done: %s", label, text[:200])
    return text


# ─── Gemini Live API: WebSocket streaming audio → text transcription ──────

def _transcribe_gemini_live(profile: dict, audio_wav: bytes) -> str:
    """Transcribe via Gemini Live API (WebSocket streaming).
    Sends raw PCM 16-bit 16kHz audio, receives text transcription.
    """
    import asyncio
    import base64
    import websockets

    api_key = profile["key"]
    model = profile.get("model") or "gemini-2.5-flash-native-audio-preview-12-2025"
    label = profile["label"]

    ws_url = (
        f"wss://generativelanguage.googleapis.com/ws/"
        f"google.ai.generativelanguage.v1beta.GenerativeService."
        f"BidiGenerateContent?key={api_key}"
    )

    # Convert WAV to raw PCM 16-bit 16kHz mono
    pcm_data = _wav_to_pcm16k(audio_wav)
    log.info("%s: sending via WebSocket (%d bytes PCM, model=%s)…",
             label, len(pcm_data), model)

    async def _stream():
        async with websockets.connect(ws_url) as ws:
            # Native audio models need AUDIO modality; regular models use TEXT
            is_native_audio = "native-audio" in model
            gen_config = {}
            if is_native_audio:
                gen_config["responseModalities"] = ["AUDIO"]
                gen_config["speechConfig"] = {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}
                }
            else:
                gen_config["responseModalities"] = ["TEXT"]

            setup_msg = {
                "setup": {
                    "model": f"models/{model}",
                    "generationConfig": gen_config,
                    "inputAudioTranscription": {},
                    "systemInstruction": {
                        "parts": [{"text": "OK"}]
                    }
                }
            }
            await ws.send(json.dumps(setup_msg))
            await ws.recv()  # setup ack

            # Send audio in chunks
            CHUNK_SIZE = 4096
            CHUNK_DURATION = 0.05
            for i in range(0, len(pcm_data), CHUNK_SIZE):
                chunk = pcm_data[i:i + CHUNK_SIZE]
                encoded = base64.b64encode(chunk).decode('utf-8')
                msg = {
                    "realtimeInput": {
                        "audio": {
                            "data": encoded,
                            "mimeType": "audio/pcm;rate=16000"
                        }
                    }
                }
                await ws.send(json.dumps(msg))
                await asyncio.sleep(CHUNK_DURATION)

            # Send silence to trigger VAD end-of-speech detection
            silence = b'\x00' * (16000 * 2)  # 1s of silence
            for i in range(0, len(silence), CHUNK_SIZE):
                chunk = silence[i:i + CHUNK_SIZE]
                encoded = base64.b64encode(chunk).decode('utf-8')
                await ws.send(json.dumps({
                    "realtimeInput": {"audio": {"data": encoded, "mimeType": "audio/pcm;rate=16000"}}
                }))
            await asyncio.sleep(0.5)

            # Collect transcription from responses
            full_text = ""
            try:
                deadline = asyncio.get_event_loop().time() + 30
                async for raw in ws:
                    if asyncio.get_event_loop().time() > deadline:
                        log.warning("%s: timeout waiting for response", label)
                        break
                    resp = json.loads(raw)
                    sc = resp.get("serverContent", {})

                    # Input transcription (server-side STT)
                    it = sc.get("inputTranscription", {})
                    if it and "text" in it:
                        full_text += it["text"]

                    # Model turn text parts (skip thought/reasoning)
                    mt = sc.get("modelTurn", {})
                    for part in mt.get("parts", []):
                        if "text" in part and not part.get("thought"):
                            full_text += part["text"]

                    if sc.get("turnComplete"):
                        break
            except websockets.exceptions.ConnectionClosed as e:
                log.warning("Gemini Live: connection closed (%s)", e)

            return full_text.strip()

    # Run async in sync context
    try:
        loop = asyncio.new_event_loop()
        text = loop.run_until_complete(_stream())
    finally:
        loop.close()

    if not text:
        raise RuntimeError(f"{label}: no transcription received")

    log.info("%s done: %s", label, text[:200])
    return text


def _wav_to_pcm16k(wav_bytes: bytes) -> bytes:
    """Convert WAV bytes to raw PCM 16-bit 16kHz mono for Gemini Live."""
    import wave
    import io
    import struct

    with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    # Convert to mono if stereo
    if n_channels == 2:
        samples = struct.unpack(f'<{len(frames)//2}h', frames)
        mono = [(samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)]
        frames = struct.pack(f'<{len(mono)}h', *mono)
        n_channels = 1

    # Resample to 16kHz if needed
    if framerate != 16000:
        import array
        src = array.array('h', frames)
        ratio = 16000 / framerate
        new_len = int(len(src) * ratio)
        resampled = array.array('h', [0] * new_len)
        for i in range(new_len):
            src_idx = min(int(i / ratio), len(src) - 1)
            resampled[i] = src[src_idx]
        frames = resampled.tobytes()

    return frames


# ─── Rev.ai: multipart upload → poll → get transcript ───────────────────

def _transcribe_revai(profile: dict, audio_wav: bytes) -> str:
    import requests as req
    api_url = profile.get("url") or "https://api.rev.ai/speechtotext/v1"
    api_key = profile["key"]
    label = profile["label"]

    headers = {"Authorization": f"Bearer {api_key}"}

    # Compress audio
    upload_data = _compress_audio(audio_wav)
    ext = "ogg" if upload_data[:4] == b"OggS" else "wav"
    mime = f"audio/{ext}"

    # Step 1: Submit job (multipart upload)
    log.info("%s: uploading (%d bytes)…", label, len(upload_data))
    files = {"media": (f"audio.{ext}", upload_data, mime)}
    options = json.dumps({"language": WHISPER_LANGUAGE or "fr"})

    resp = req.post(
        f"{api_url}/jobs",
        headers=headers,
        files=files,
        data={"options": options},
        timeout=30,
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]
    log.info("%s: job created (id=%s)", label, job_id)

    # Step 2: Poll until transcribed
    poll_url = f"{api_url}/jobs/{job_id}"
    while True:
        if cancel_event.is_set():
            raise RuntimeError("Cancelled by user")
        result = req.get(poll_url, headers=headers, timeout=10).json()
        status = result["status"]
        if status == "transcribed":
            break
        elif status == "failed":
            raise RuntimeError(f"{label} error: {result.get('failure_detail', 'unknown')}")
        time.sleep(0.5)

    # Step 3: Get transcript as plain text
    transcript_resp = req.get(
        f"{api_url}/jobs/{job_id}/transcript",
        headers={**headers, "Accept": "text/plain"},
        timeout=15,
    )
    transcript_resp.raise_for_status()
    text = transcript_resp.text.strip()
    if not text:
        raise RuntimeError(f"{label}: empty transcription returned")
    log.info("%s done: %s", label, text[:200])
    return text

def transcribe(audio_wav: bytes, on_progress=None) -> str:
    """Transcribe audio via the active API profile, with local fallback."""
    profile = api_profiles.get(active_api_profile, {})
    is_cloud = bool(profile.get("url"))
    audio_seconds = len(audio_wav) / (SAMPLE_RATE * 2 * CHANNELS)

    # ── Cloud API mode ───────────────────────────────────────────────
    if is_cloud:
        try:
            log.info("Active profile: %s", profile.get('label', active_api_profile))
            text = _transcribe_with_api(profile, audio_wav)
            _record_usage(active_api_profile, audio_seconds)
            return text
        except Exception as e:
            if cancel_event.is_set():
                log.info("Transcription cancelled, no fallback")
                return ""
            log.warning("API failed (%s) — local whisper fallback", str(e)[:120])

    # ── Local mode: faster-whisper + quick cleanup ────────────────────
    # Check cancellation before starting heavy whisper work
    if cancel_event.is_set():
        log.info("Transcription cancelled, no fallback")
        return ""

    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_wav)
            tmp_path = tmp.name

        model = _get_whisper_model()

        # Check cancellation after model loading (can take several seconds)
        if cancel_event.is_set():
            log.info("Transcription cancelled after model loading")
            return ""

        segments, info = model.transcribe(tmp_path, language=WHISPER_LANGUAGE,
                                           beam_size=5)
        log.info("Detected language: %s (prob=%.2f)", info.language,
                 info.language_probability)

        full_text = ""
        for segment in segments:
            # Check cancellation between segments
            if cancel_event.is_set():
                log.info("Transcription cancelled during processing")
                return ""
            full_text += segment.text
            if on_progress:
                word_count = len(full_text.split())
                on_progress(word_count)

        raw_text = full_text.strip()
        log.info("Raw transcription: %s", raw_text)
        _record_usage("local", audio_seconds)
        return _quick_cleanup(raw_text)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════════
#  Paste at cursor
# ═══════════════════════════════════════════════════════════════════════════════

def paste_text(text: str):
    """Copy text to clipboard and paste via Ctrl+V. Optionally press Enter if auto_enter is enabled."""
    import ctypes

    # Save to clipboard history
    clipboard_history.insert(0, text)
    if len(clipboard_history) > MAX_CLIPBOARD_HISTORY:
        clipboard_history.pop()
    # Force tray menu refresh so new recording appears immediately
    if tray_icon:
        try:
            tray_icon.update_menu()
        except Exception:
            pass

    pyperclip.copy(text)
    time.sleep(0.05)

    # Windows virtual key codes
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002

    keybd_event = ctypes.windll.user32.keybd_event

    # Release all modifiers first to avoid stuck keys
    for vk in (0x10, 0x11, 0x12):  # Shift, Ctrl, Alt
        keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

    # Press Ctrl+V
    keybd_event(VK_CONTROL, 0, 0, 0)         # Ctrl down
    keybd_event(VK_V, 0, 0, 0)               # V down
    time.sleep(0.02)
    keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0) # V up
    keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)  # Ctrl up
    time.sleep(0.05)

    # Press Enter to send (if enabled)
    if auto_enter:
        keybd_event(VK_RETURN, 0, 0, 0)              # Enter down
        time.sleep(0.02)
        keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)  # Enter up


# ═══════════════════════════════════════════════════════════════════════════════
#  Transcription with auto-retry
# ═══════════════════════════════════════════════════════════════════════════════

def transcribe_with_retry(wav_data: bytes, paste: bool = True):
    """
    Transcribe audio with automatic retry on failure.
    Runs in the calling thread (meant to be called from a background thread).
    """
    def _on_progress(word_count):
        if overlay_app:
            overlay_app.show_transcribing(word_count)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        if cancel_event.is_set():
            log.info("Transcription cancelled by user")
            if overlay_app:
                overlay_app.hide()
            return None
        try:
            if overlay_app:
                overlay_app.show_transcribing()
            text = transcribe(wav_data, on_progress=_on_progress)

            # Re-check cancellation after transcribe returned
            if cancel_event.is_set():
                log.info("Transcription cancelled by user (after transcribe)")
                if overlay_app:
                    overlay_app.show_cancelled()
                return None

            if text:
                log.info("Transcription (attempt %d): %s", attempt, text)
                _save_transcription_result(text)
                if paste:
                    paste_text(text)
                if overlay_app:
                    overlay_app.show_done()
                _purge_old_recordings()
                return text
            else:
                # Empty text could be from cancellation
                if cancel_event.is_set():
                    log.info("Transcription cancelled by user")
                    if overlay_app:
                        overlay_app.show_cancelled()
                    return None
                last_error = "No transcription returned"
                log.warning("%s (attempt %d/%d)", last_error, attempt, MAX_RETRIES)
        except Exception as e:
            # Cancel during API call often raises RuntimeError
            if cancel_event.is_set():
                log.info("Transcription cancelled by user (exception: %s)", e)
                if overlay_app:
                    overlay_app.show_cancelled()
                return None
            last_error = str(e)
            log.error("API error (attempt %d/%d): %s", attempt, MAX_RETRIES, last_error)

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES:
            if cancel_event.is_set():
                log.info("Transcription cancelled, skipping retry")
                if overlay_app:
                    overlay_app.show_cancelled()
                return None
            log.info("Retrying in %ds…", RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    # All retries exhausted
    log.error("Failed after %d attempts: %s", MAX_RETRIES, last_error)
    _save_transcription_result(f"❌ {last_error}" if last_error else "❌ Failed")
    if overlay_app:
        overlay_app.show_error(last_error or "Transcription failed")
    return None


def _save_transcription_result(text: str):
    """Save transcription result as .txt next to the last recording."""
    if last_recording_path and os.path.isfile(last_recording_path):
        txt_path = last_recording_path.rsplit(".", 1)[0] + ".txt"
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Toggle & Cancel logic
# ═══════════════════════════════════════════════════════════════════════════════

def on_cancel():
    """Escape key handler — cancel recording or transcription in progress."""
    global recording, sd_stream

    # Only act if we're recording or the overlay is visible (transcription in progress)
    is_active = recording or (overlay_app and overlay_app._state != "hidden")
    if not is_active:
        return

    cancel_event.set()

    # If currently recording, stop everything immediately
    if recording:
        recording = False
        log.info("Recording cancelled (Escape)")

        # Stop microphone
        if sd_stream:
            try:
                sd_stream.stop()
                sd_stream.close()
            except Exception:
                pass
            sd_stream = None

        # Restore audio
        _restore_other_apps()

    # Show cancel feedback (calm, not an error)
    if overlay_app:
        overlay_app.show_cancelled()

    log.info("Operation cancelled by user")


def on_toggle():
    global recording

    # Clear any previous cancellation
    cancel_event.clear()

    with recording_lock:
        if not recording:
            start_recording()
        else:
            wav_data = stop_recording()

            if cancel_event.is_set():
                log.info("Transcription cancelled (Escape)")
                if overlay_app:
                    overlay_app.hide()
                return

            duration = len(wav_data) / (SAMPLE_RATE * 2 * CHANNELS) if wav_data else 0
            if duration < 0.5:
                log.warning("Recording too short, ignored.")
                if overlay_app:
                    overlay_app.hide()
                return

            # Transcribe in background thread
            if overlay_app:
                overlay_app.show_transcribing()
            threading.Thread(
                target=transcribe_with_retry,
                args=(wav_data,),
                daemon=True,
            ).start()


# ═══════════════════════════════════════════════════════════════════════════════
#  System Tray Icon
# ═══════════════════════════════════════════════════════════════════════════════

def _create_tray_icon_image() -> Image.Image:
    """Load tray icon from audio.png (or generate fallback)."""
    icon_path = os.path.join(SCRIPT_DIR, "audio.png")
    try:
        img = Image.open(icon_path).convert("RGBA")
        img = img.resize((64, 64), Image.LANCZOS)
        return img
    except Exception:
        # Fallback: generate simple mic icon
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        mic_x, mic_top, mic_w, mic_h = 22, 8, 20, 28
        draw.rounded_rectangle(
            [mic_x, mic_top, mic_x + mic_w, mic_top + mic_h],
            radius=10, fill="#6ea8fe")
        cx = mic_x + mic_w // 2
        draw.arc(
            [mic_x - 4, mic_top + 10, mic_x + mic_w + 4, mic_top + mic_h + 12],
            start=0, end=180, fill="#6ea8fe", width=3)
        draw.line([(cx, mic_top + mic_h + 12), (cx, mic_top + mic_h + 20)], fill="#6ea8fe", width=3)
        draw.line([(cx - 8, mic_top + mic_h + 20), (cx + 8, mic_top + mic_h + 20)], fill="#6ea8fe", width=3)
        return img


def _quit_from_tray(icon: pystray.Icon, item):
    log.info("Quit requested from tray.")
    shutdown_event.set()
    icon.stop()


def _retranscribe_file(filepath: str):
    """Retranscribe a specific WAV file (or benchmark it)."""
    if not os.path.isfile(filepath):
        log.warning("File not found: %s", filepath)
        return

    log.info("Re-transcribing %s", filepath)
    with open(filepath, "rb") as f:
        wav_data = f.read()

    if overlay_app:
        overlay_app.show_transcribing()
    threading.Thread(
        target=transcribe_with_retry,
        args=(wav_data,),
        daemon=True,
    ).start()


def _open_recordings_folder(icon: pystray.Icon, item):
    """Open the recordings folder in Explorer."""
    subprocess.Popen(["explorer", RECORDINGS_DIR])


def _run_tray():
    global tray_icon
    icon_image = _create_tray_icon_image()
    def _build_menu():
        """Build the tray menu dynamically (profiles, options, history)."""
        def _toggle_enter(icon, item):
            global auto_enter
            auto_enter = not auto_enter
            log.info("Auto enter: %s", "enabled" if auto_enter else "disabled")
            # Sync overlay banner
            if overlay_app:
                if auto_enter:
                    overlay_app.root.after(0, lambda: (
                        overlay_app._cancel_warn_auto_hide(),
                        overlay_app.warn_canvas.itemconfig(overlay_app.warn_label, text=t("overlay.auto_enter_warning")),
                        overlay_app.warn_canvas.itemconfig(overlay_app.warn_link, text=t("overlay.auto_enter_disable")),
                        setattr(overlay_app, '_warn_link_action', 'disable'),
                        overlay_app.warn_root.deiconify(),
                    ))
                else:
                    overlay_app.root.after(0, overlay_app._show_warn_disabled)

        def _switch_profile(name):
            def handler(icon, item):
                global active_api_profile
                active_api_profile = name
                p = api_profiles[name]
                log.info("API profile changed: %s", p.get("label", name))
            return handler

        def _toggle_from_tray(icon, item):
            on_toggle()

        recording_label = t("tray.stop") if recording else t("tray.record")
        items = [
            pystray.MenuItem(recording_label, _toggle_from_tray, default=True),
            pystray.Menu.SEPARATOR,
        ]

        # API profile radio group
        for pname, pdata in api_profiles.items():
            plabel = pdata.get("label", pname) + _get_usage_str(pname)
            items.append(pystray.MenuItem(
                plabel,
                _switch_profile(pname),
                checked=lambda item, n=pname: active_api_profile == n,
                radio=True,
            ))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(t("tray.auto_enter"), _toggle_enter, checked=lambda item: auto_enter))

        def _is_autostart_enabled():
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ)
                try:
                    winreg.QueryValueEx(key, "VoiceTranscriber")
                    winreg.CloseKey(key)
                    return True
                except FileNotFoundError:
                    winreg.CloseKey(key)
                    return False
            except Exception:
                return False

        def _toggle_autostart(icon, item):
            import sys
            python_exe = sys.executable
            if python_exe.lower().endswith("pythonw.exe"):
                python_exe = python_exe[:-5] + ".exe"
            startup_script = os.path.join(SCRIPT_DIR, "setup_startup.py")
            if _is_autostart_enabled():
                subprocess.run([python_exe, startup_script, "uninstall"],
                               creationflags=_NO_WINDOW)
                log.info("Auto-start: disabled")
            else:
                subprocess.run([python_exe, startup_script, "install"],
                               creationflags=_NO_WINDOW)
                log.info("Auto-start: enabled")

        items.append(pystray.MenuItem(
            t("tray.autostart"), _toggle_autostart,
            checked=lambda item: _is_autostart_enabled()))
        items.append(pystray.Menu.SEPARATOR)

        # ── Combined recordings/history submenu ──────────────────────
        try:
            rec_files = sorted(
                [f for f in os.listdir(RECORDINGS_DIR) if f.lower().endswith(".wav") and f.startswith("rec_")],
                reverse=True,
            )[:15]
            log.debug("Recordings menu: %d wav files found", len(rec_files))

            combined_items = []

            if rec_files:
                def _retranscribe_handler(fpath):
                    def handler(icon, item):
                        _retranscribe_file(fpath)
                    return handler

                show_date = MAX_WAV_LIFETIME > 1440  # > 24h
                combined_items.append(pystray.MenuItem(t("tray.retranscribe_header"), None, enabled=False))
                for fname in rec_files:
                    fpath = os.path.join(RECORDINGS_DIR, fname)
                    try:
                        parts = fname.replace("rec_", "").replace(".wav", "")
                        dt = datetime.strptime(parts, "%Y%m%d_%H%M%S")
                        label = dt.strftime("%d/%m %H:%M") if show_date else dt.strftime("%H:%M:%S")
                    except ValueError:
                        label = fname
                    txt_path = fpath.rsplit(".", 1)[0] + ".txt"
                    preview = ""
                    if os.path.isfile(txt_path):
                        try:
                            with open(txt_path, "r", encoding="utf-8") as ftxt:
                                preview = ftxt.read(40).strip().replace("\n", " ")
                        except OSError:
                            pass
                    if preview:
                        label += f"  {preview[:25]}" + ("…" if len(preview) > 25 else "")
                    else:
                        try:
                            duration_s = os.path.getsize(fpath) / (SAMPLE_RATE * 2 * CHANNELS)
                            label += f" ({duration_s:.0f}s)"
                        except OSError:
                            pass
                    combined_items.append(pystray.MenuItem(label, _retranscribe_handler(fpath)))

            if clipboard_history:
                def _copy_item(idx):
                    def handler(icon, item):
                        pyperclip.copy(clipboard_history[idx])
                        log.info("Copied from history: %s", clipboard_history[idx][:60])
                    return handler

                combined_items.append(pystray.Menu.SEPARATOR)
                combined_items.append(pystray.MenuItem(t("tray.copy_header"), None, enabled=False))
                for i, entry in enumerate(clipboard_history[:8]):
                    label = (entry[:40] + "…") if len(entry) > 40 else entry
                    combined_items.append(pystray.MenuItem(label, _copy_item(i)))

            if combined_items:
                items.append(pystray.MenuItem(
                    t("tray.recordings"),
                    pystray.Menu(*combined_items),
                ))
            else:
                items.append(pystray.MenuItem(t("tray.recordings_none"), None, enabled=False))
        except Exception:
            log.exception("Error building recordings submenu")
            items.append(pystray.MenuItem(t("tray.recordings_none"), None, enabled=False))

        items.append(pystray.MenuItem(t("tray.open_folder"), _open_recordings_folder))

        items.append(pystray.Menu.SEPARATOR)

        def _open_documentation(icon, item):
            """Open doc.{lang}.md with the system default application."""
            from locales import get_language
            lang = get_language()
            doc_path = os.path.join(SCRIPT_DIR, f"doc.{lang}.md")
            if not os.path.isfile(doc_path):
                doc_path = os.path.join(SCRIPT_DIR, "doc.en.md")
            if os.path.isfile(doc_path):
                os.startfile(doc_path)
            else:
                log.warning("Documentation not found: %s", doc_path)

        items.append(pystray.MenuItem(t("tray.config"), _open_config))
        items.append(pystray.MenuItem(t("tray.documentation"), _open_documentation))
        items.append(pystray.MenuItem(t("tray.quit"), _quit_from_tray))
        return items

    def _open_config(icon, item):
        """Open config GUI in a subprocess and reload profiles when done."""
        import sys
        python_exe = sys.executable
        if python_exe.lower().endswith("pythonw.exe"):
            python_exe = python_exe[:-5] + ".exe"
        config_script = os.path.join(SCRIPT_DIR, "config_gui.py")
        proc = subprocess.Popen([python_exe, config_script], creationflags=_NO_WINDOW)
        def _wait_and_reload():
            proc.wait()
            _reload_profiles()
            # Force tray menu refresh on Windows
            if tray_icon:
                try:
                    tray_icon.update_menu()
                except Exception:
                    pass
            log.info("Configuration closed, profiles reloaded")
        threading.Thread(target=_wait_and_reload, daemon=True).start()

    tray_icon = pystray.Icon(
        name="VoiceTranscriber",
        icon=icon_image,
        title=f"Voice Transcriber — {HOTKEY.replace('+', '+').title()}",
        menu=pystray.Menu(lambda: _build_menu()),
    )
    tray_icon.run()


# ═══════════════════════════════════════════════════════════════════════════════
#  Recordings purge — delete WAV files older than MAX_WAV_LIFETIME
# ═══════════════════════════════════════════════════════════════════════════════

def _purge_old_recordings():
    """Delete WAV (and companion .txt) files in RECORDINGS_DIR older than MAX_WAV_LIFETIME minutes."""
    if MAX_WAV_LIFETIME <= 0:
        return
    now = time.time()
    cutoff = now - MAX_WAV_LIFETIME * 60
    purged = 0
    for filename in os.listdir(RECORDINGS_DIR):
        if not filename.lower().endswith((".wav", ".txt")):
            continue
        filepath = os.path.join(RECORDINGS_DIR, filename)
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                purged += 1
        except OSError:
            pass
    if purged:
        log.info("Purge : %d fichier(s) supprimé(s) (> %d min)", purged, MAX_WAV_LIFETIME)


# ═══════════════════════════════════════════════════════════════════════════════
#  Benchmark Mode (DEBUG_BENCHMARK)
# ═══════════════════════════════════════════════════════════════════════════════

def _launch_benchmark(wav_data: bytes):
    """Save WAV and launch benchmark in a new console window."""
    import sys
    import tempfile

    # Save WAV to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=RECORDINGS_DIR) as tmp:
        tmp.write(wav_data)
        tmp_path = tmp.name

    log.info("Benchmark launched in new window: %s", tmp_path)

    # Use python.exe (not pythonw.exe) to get a visible console
    python_exe = sys.executable
    if python_exe.lower().endswith("pythonw.exe"):
        python_exe = python_exe[:-5] + ".exe"  # pythonw.exe -> python.exe

    subprocess.Popen(
        [python_exe, os.path.abspath(__file__), "--benchmark", tmp_path],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def _run_benchmark_cli(wav_path: str):
    """CLI entry point: benchmark all API profiles against a WAV file."""
    import time as _time

    with open(wav_path, "rb") as f:
        wav_data = f.read()

    audio_seconds = len(wav_data) / (SAMPLE_RATE * 2 * CHANNELS)

    print()
    print("═" * 72)
    print(f"  {t('bench.title')}")
    print("═" * 72)
    print(f"  {t('bench.audio', seconds=audio_seconds, bytes=len(wav_data))}")
    print(f"  {t('bench.file', path=wav_path)}")
    print("═" * 72)

    results = []

    for pname, pdata in api_profiles.items():
        label = pdata.get("label", pname)
        api_type = pdata.get("type", "")

        # Skip profiles without valid keys (except local)
        if pname != "local" and not pdata.get("key"):
            print(f"\n  ⏭  {t('bench.skip_no_key', label=label)}")
            continue
        if pname != "local":
            key = pdata.get("key", "")
            if key.startswith("votre-") or key.startswith("sk-votre-"):
                print(f"\n  ⏭  {t('bench.skip_placeholder', label=label)}")
                continue

        print(f"\n  {t('bench.running', label=label, type=api_type)}")
        start = _time.perf_counter()
        try:
            if pname == "local":
                # Local transcription
                import tempfile as _tmp
                with _tmp.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(wav_data)
                    tmp_p = tmp.name
                try:
                    model = _get_whisper_model()
                    segments, info = model.transcribe(tmp_p, language=WHISPER_LANGUAGE, beam_size=5)
                    text = "".join(s.text for s in segments).strip()
                    text = _quick_cleanup(text)
                finally:
                    os.unlink(tmp_p)
            else:
                text = _transcribe_with_api(pdata, wav_data)

            elapsed_ms = (_time.perf_counter() - start) * 1000
            print(f"     {t('bench.result_text', text=text)}")
            print(f"     {t('bench.result_time', ms=elapsed_ms)}")
            results.append((label, elapsed_ms, "✓", text[:60]))
            _record_usage(pname, audio_seconds)

        except Exception as e:
            elapsed_ms = (_time.perf_counter() - start) * 1000
            print(f"     {t('bench.result_error', error=e)}")
            print(f"     {t('bench.result_time', ms=elapsed_ms)}")
            results.append((label, elapsed_ms, "✗", str(e)[:60]))

    # Summary table
    print()
    print("═" * 72)
    print(f"  {t('bench.summary')}")
    print("─" * 72)
    print(f"  {t('bench.col_profile'):<28} {t('bench.col_time'):>9}  {'':>3}  {t('bench.col_text')}")
    print("─" * 72)
    for label, ms, status, text in sorted(results, key=lambda x: x[1]):
        print(f"  {label:<28} {ms:>8,.0f}ms  {status:>3}  {text}")
    print("─" * 72)

    # Clean up temp file
    try:
        os.unlink(wav_path)
    except OSError:
        pass

    print()
    input(f"  {t('bench.press_enter')}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    global overlay_app

    profile = api_profiles.get(active_api_profile, {})
    profile_label = profile.get("label", active_api_profile)
    profile_list = ", ".join(p.get("label", n) for n, p in api_profiles.items())
    log.info("Voice Transcriber started (profile=%s, available=[%s])",
             profile_label, profile_list)

    # Start overlay (tkinter) in its own thread
    def _run_overlay():
        global overlay_app
        overlay_app = OverlayApp()
        overlay_app.run()

    threading.Thread(target=_run_overlay, daemon=True).start()
    tk_ready.wait(timeout=5)

    # Parse configurable hotkey
    _hotkey_parts = [p.strip().lower() for p in HOTKEY.split("+")]
    _hotkey_trigger = _hotkey_parts[-1] if _hotkey_parts else "space"
    _hotkey_modifiers = _hotkey_parts[:-1] if len(_hotkey_parts) > 1 else ["ctrl"]

    log.info("Hotkey configured: %s", HOTKEY)
    _last_toggle_time = [0.0]

    def _key_handler(event):
        if event.event_type != "down":
            return

        # Configurable hotkey → toggle recording
        if event.name == _hotkey_trigger and all(keyboard.is_pressed(m) for m in _hotkey_modifiers):
            now = time.time()
            if now - _last_toggle_time[0] < 0.5:  # debounce
                return
            _last_toggle_time[0] = now
            threading.Thread(target=on_toggle, daemon=True).start()

        # Escape → cancel (only when app is active)
        elif event.name == "esc":
            is_active = recording or (overlay_app and overlay_app._state != "hidden")
            if is_active:
                on_cancel()

    keyboard.hook(_key_handler)

    # Run system tray in a background thread
    tray_thread = threading.Thread(target=_run_tray, daemon=True)
    tray_thread.start()

    # Watch for restart flag (set by config GUI)
    restart_flag = os.path.join(SCRIPT_DIR, ".restart")
    def _watch_restart():
        # Small delay at startup to avoid reacting to our own restart flag
        shutdown_event.wait(timeout=3)
        while not shutdown_event.is_set():
            if os.path.isfile(restart_flag):
                try:
                    os.remove(restart_flag)
                except OSError:
                    pass
                log.info("Restart requested from configuration.")
                shutdown_event.set()
                if tray_icon:
                    tray_icon.stop()
                return
            shutdown_event.wait(timeout=1)
    threading.Thread(target=_watch_restart, daemon=True).start()

    # Wait for shutdown signal (from tray quit, Esc key, or Ctrl+C)
    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        pass

    log.info("Voice Transcriber stopped.")
    keyboard.unhook_all()
    if overlay_app:
        overlay_app.destroy()


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--benchmark":
        _run_benchmark_cli(sys.argv[2])
    else:
        main()
