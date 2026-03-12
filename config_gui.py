"""
Voice Transcriber — Settings GUI
Manages all configuration: general settings + API profiles.
Stored in profiles.json.
"""

import json
import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageTk

# Set AppUserModelID so Windows uses our icon in the taskbar (not Python's)
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VoiceTranscriber.ConfigGUI")
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(SCRIPT_DIR, "profiles.json")

# ═════════════════════════════════════════════════════════════════════════════
#  Protocol definitions — how the API communicates, not which service it is
# ═════════════════════════════════════════════════════════════════════════════

PROTOCOLS = [
    ("openai", "OpenAI Compatible",
     "Envoi direct du fichier audio, réponse immédiate.\n"
     "Fonctionne avec : OpenAI, Groq, Together AI, FastWhisper Server, "
     "et tout endpoint compatible /v1/audio/transcriptions."),

    ("assemblyai", "AssemblyAI",
     "Upload du fichier, puis polling asynchrone pour le résultat.\n"
     "Spécifique à l'API AssemblyAI."),

    ("revai", "Rev.ai",
     "Upload multipart, polling asynchrone, puis récupération du transcript.\n"
     "Spécifique à l'API Rev.ai."),

    ("gemini", "Google Gemini (Multimodal)",
     "Audio encodé en base64 envoyé dans un prompt multimodal.\n"
     "Fonctionne avec les modèles Gemini (Flash, Pro, etc.)."),

    ("gemini_live", "Gemini Live (WebSocket)",
     "Streaming audio en temps réel via WebSocket.\n"
     "Audio PCM 16kHz envoyé par chunks, transcription native.\n"
     "Modèle : gemini-2.5-flash-native-audio-preview"),
]

PROTOCOL_KEYS   = [k for k, _, _ in PROTOCOLS]
PROTOCOL_NAMES  = {k: n for k, n, _ in PROTOCOLS}
PROTOCOL_DESCS  = {k: d for k, _, d in PROTOCOLS}

PROTOCOL_DEFAULTS = {
    "openai":      {"url": "https://api.openai.com",                      "model": "whisper-1"},
    "assemblyai":  {"url": "https://api.assemblyai.com",                  "model": "universal-3-pro"},
    "revai":       {"url": "https://api.rev.ai/speechtotext/v1",          "model": ""},
    "gemini":      {"url": "https://generativelanguage.googleapis.com",   "model": "gemini-2.0-flash"},
    "gemini_live": {"url": "wss://generativelanguage.googleapis.com",     "model": "gemini-2.5-flash-native-audio-preview-12-2025"},
}

WHISPER_MODELS = [
    ("tiny",              "Tiny — Très rapide, qualité basique (~1 Go RAM)"),
    ("tiny.en",           "Tiny EN — Anglais uniquement, très rapide"),
    ("base",              "Base — Rapide, qualité correcte (~1 Go RAM)"),
    ("base.en",           "Base EN — Anglais uniquement, rapide"),
    ("small",             "Small — Bon compromis vitesse/qualité (~2 Go RAM)"),
    ("small.en",          "Small EN — Anglais uniquement"),
    ("medium",            "Medium — Bonne qualité (~5 Go RAM)"),
    ("medium.en",         "Medium EN — Anglais uniquement"),
    ("large-v1",          "Large v1 — Haute qualité (~10 Go RAM)"),
    ("large-v2",          "Large v2 — Excellente qualité (~10 Go RAM)"),
    ("large-v3",          "Large v3 — Meilleure qualité (~10 Go RAM)"),
    ("turbo",             "Turbo — Large v3 accéléré, bon rapport qualité/vitesse"),
    ("distil-small.en",   "Distil Small EN — Rapide, anglais uniquement"),
    ("distil-medium.en",  "Distil Medium EN — Rapide, anglais uniquement"),
    ("distil-large-v2",   "Distil Large v2 — Rapide, qualité proche de Large"),
    ("distil-large-v3",   "Distil Large v3 — Rapide, qualité proche de Large v3"),
    ("distil-large-v3.5", "Distil Large v3.5 — Le plus récent des modèles distillés"),
]

LANGUAGES = [
    ("fr", "Français"), ("en", "English"), ("de", "Deutsch"),
    ("es", "Español"), ("it", "Italiano"), ("pt", "Português"),
    ("nl", "Nederlands"), ("ja", "日本語"), ("zh", "中文"),
    ("ko", "한국어"), ("ar", "العربية"), ("ru", "Русский"),
]


# ═════════════════════════════════════════════════════════════════════════════
#  Design tokens
# ═════════════════════════════════════════════════════════════════════════════

class C:
    BG          = "#1a1a2e"
    SURFACE     = "#222240"
    SURFACE_ALT = "#2a2a4a"
    INPUT       = "#303050"
    BORDER      = "#3a3a5c"

    TEXT        = "#e8e8f0"
    TEXT_SEC    = "#a0a0b8"
    TEXT_DIM    = "#6a6a80"

    ACCENT      = "#7c6ef0"
    GREEN       = "#4caf7c"
    GREEN_BG    = "#1a3a2a"
    RED         = "#e05555"
    RED_BG      = "#3a1a1a"
    ORANGE      = "#e0a040"

F_TITLE   = ("Segoe UI", 14, "bold")
F_H2      = ("Segoe UI", 12, "bold")
F_H3      = ("Segoe UI", 10, "bold")
F_BODY    = ("Segoe UI", 10)
F_SMALL   = ("Segoe UI", 9)
F_TINY    = ("Segoe UI", 8)
F_MONO    = ("Consolas", 10)


# ═════════════════════════════════════════════════════════════════════════════
#  Data helpers
# ═════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"settings": {}, "profiles": {}, "default": "local"}


def save_config(data: dict):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text: str) -> str:
    """Generate a profile key from a label."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s[:30] or "profile"


def _set_window_icon(window):
    """Set the window icon from audio.ico / audio.png."""
    try:
        # Prefer .ico for crisp Windows titlebar icon
        ico_path = os.path.join(SCRIPT_DIR, "audio.ico")
        if os.path.isfile(ico_path):
            window.iconbitmap(ico_path)
            return
        # Fallback to .png
        png_path = os.path.join(SCRIPT_DIR, "audio.png")
        if os.path.isfile(png_path):
            icon = Image.open(png_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
            photo = ImageTk.PhotoImage(icon)
            window.iconphoto(False, photo)
            window._icon_ref = photo  # prevent garbage collection
    except Exception:
        pass


def _center_on_parent(child, parent, width, height):
    """Position a child window centered on its parent."""
    parent.update_idletasks()
    px = parent.winfo_x()
    py = parent.winfo_y()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    x = px + (pw - width) // 2
    y = py + (ph - height) // 2
    child.geometry(f"{width}x{height}+{x}+{y}")


# ═════════════════════════════════════════════════════════════════════════════
#  Widgets
# ═════════════════════════════════════════════════════════════════════════════

def btn(parent, text, bg, fg, cmd, font=None, padx=14, pady=5, **kw):
    return tk.Button(parent, text=text, bg=bg, fg=fg, font=font or F_BODY,
                     relief="flat", bd=0, padx=padx, pady=pady, cursor="hand2",
                     activebackground=bg, activeforeground=fg, command=cmd, **kw)


def field_row(parent, title, desc, widget_factory, bg=None):
    """Create a settings row: left = title+desc, right = widget."""
    bg = bg or C.SURFACE
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=3)

    left = tk.Frame(row, bg=bg)
    left.pack(side="left", fill="x", expand=True, padx=(0, 12))
    tk.Label(left, text=title, font=F_H3, bg=bg, fg=C.TEXT, anchor="w").pack(fill="x")
    if desc:
        tk.Label(left, text=desc, font=F_TINY, bg=bg, fg=C.TEXT_DIM,
                 anchor="w", justify="left", wraplength=320).pack(fill="x")

    right = tk.Frame(row, bg=bg)
    right.pack(side="right")
    widget_factory(right)

    return row


def section_title(parent, text, desc=None):
    f = tk.Frame(parent, bg=C.BG)
    f.pack(fill="x", padx=24, pady=(18, 4))
    tk.Label(f, text=text.upper(), font=F_SMALL, bg=C.BG, fg=C.ACCENT).pack(side="left")
    if desc:
        tk.Label(f, text=f"  —  {desc}", font=F_TINY, bg=C.BG, fg=C.TEXT_DIM).pack(side="left")
    return f


# ═════════════════════════════════════════════════════════════════════════════
#  Profile Editor
# ═════════════════════════════════════════════════════════════════════════════

class ProfileEditor(tk.Toplevel):
    def __init__(self, parent, profile_name="", profile_data=None, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.original_name = profile_name
        data = profile_data or {}

        is_edit = bool(profile_name)
        self.title("Modifier le profil" if is_edit else "Nouveau profil")
        self.resizable(False, False)
        self.configure(bg=C.BG)
        self.transient(parent)
        self.grab_set()
        _center_on_parent(self, parent, 560, 560)
        _set_window_icon(self)

        # Header
        hdr = tk.Frame(self, bg=C.SURFACE, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Modifier le profil" if is_edit else "Nouveau profil",
                 font=F_H2, bg=C.SURFACE, fg=C.TEXT, padx=20).pack(side="left", fill="y")

        # Card
        card = tk.Frame(self, bg=C.SURFACE)
        card.pack(fill="both", expand=True, padx=20, pady=12)
        inner = tk.Frame(card, bg=C.SURFACE)
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Nom affiché ──────────────────────────────────────────────
        self.label_var = tk.StringVar(value=data.get("label", ""))
        field_row(inner, "Nom du profil",
                  "Nom affiché dans le menu et le tray icon",
                  lambda p: tk.Entry(p, textvariable=self.label_var, font=F_BODY, width=28,
                                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                                     relief="flat", bd=5).pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=6)

        # ── Protocole ────────────────────────────────────────────────
        self.type_var = tk.StringVar(value=data.get("type", "openai"))

        def _make_proto(p):
            display_values = [PROTOCOL_NAMES[k] for k in PROTOCOL_KEYS]
            cb = ttk.Combobox(p, values=display_values, state="readonly",
                              width=26, font=F_BODY)
            # Set current value
            cur = self.type_var.get()
            if cur in PROTOCOL_NAMES:
                cb.set(PROTOCOL_NAMES[cur])
            cb.pack()
            cb.bind("<<ComboboxSelected>>", lambda e: self._on_proto_changed(cb))
            self._proto_combo = cb

        field_row(inner, "Protocole de communication",
                  "Détermine comment l'audio est envoyé au service",
                  _make_proto)

        # Protocol description
        self.proto_desc = tk.Label(inner, text=PROTOCOL_DESCS.get(self.type_var.get(), ""),
                                   font=F_TINY, bg=C.SURFACE, fg=C.TEXT_DIM,
                                   anchor="w", justify="left", wraplength=480)
        self.proto_desc.pack(fill="x", pady=(0, 4))

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=6)

        # ── URL ──────────────────────────────────────────────────────
        defaults = PROTOCOL_DEFAULTS.get(data.get("type", "openai"), {})
        self.url_var = tk.StringVar(value=data.get("url", defaults.get("url", "")))
        field_row(inner, "URL de l'API",
                  "Point d'entrée du service de transcription",
                  lambda p: tk.Entry(p, textvariable=self.url_var, font=F_MONO, width=28,
                                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                                     relief="flat", bd=5).pack())

        # ── Clé API ──────────────────────────────────────────────────
        self.key_var = tk.StringVar(value=data.get("key", ""))
        field_row(inner, "Clé API",
                  "Clé d'authentification fournie par le service",
                  lambda p: tk.Entry(p, textvariable=self.key_var, font=F_MONO, width=28,
                                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                                     relief="flat", bd=5, show="●").pack())

        # ── Modèle ───────────────────────────────────────────────────
        self.model_var = tk.StringVar(value=data.get("model", defaults.get("model", "")))
        field_row(inner, "Modèle",
                  "Identifiant du modèle (laisser vide si non applicable)",
                  lambda p: tk.Entry(p, textvariable=self.model_var, font=F_MONO, width=28,
                                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                                     relief="flat", bd=5).pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=6)

        # ── Enabled ──────────────────────────────────────────────────
        self.enabled_var = tk.BooleanVar(value=data.get("enabled", True))
        en_f = tk.Frame(inner, bg=C.SURFACE)
        en_f.pack(fill="x", pady=4)
        tk.Checkbutton(en_f, text="  Profil actif", variable=self.enabled_var,
                       bg=C.SURFACE, fg=C.TEXT, selectcolor=C.INPUT,
                       activebackground=C.SURFACE, activeforeground=C.TEXT,
                       font=F_BODY).pack(side="left")
        tk.Label(en_f, text="— Décocher pour désactiver sans supprimer",
                 font=F_TINY, bg=C.SURFACE, fg=C.TEXT_DIM).pack(side="left", padx=6)

        # Buttons
        bar = tk.Frame(self, bg=C.BG)
        bar.pack(fill="x", padx=20, pady=(0, 14))
        btn(bar, "Sauvegarder", C.ACCENT, "#fff", self._save,
            font=F_H3, padx=20, pady=7).pack(side="left", padx=(0, 8))
        btn(bar, "Annuler", C.SURFACE_ALT, C.TEXT_SEC, self.destroy,
            padx=20, pady=7).pack(side="left")

    def _on_proto_changed(self, combo):
        selected_name = combo.get()
        for key, name in PROTOCOL_NAMES.items():
            if name == selected_name:
                self.type_var.set(key)
                break
        t = self.type_var.get()
        self.proto_desc.config(text=PROTOCOL_DESCS.get(t, ""))
        defaults = PROTOCOL_DEFAULTS.get(t, {})
        all_default_urls = [d["url"] for d in PROTOCOL_DEFAULTS.values()]
        if not self.url_var.get() or self.url_var.get() in all_default_urls:
            self.url_var.set(defaults.get("url", ""))
        all_default_models = [d["model"] for d in PROTOCOL_DEFAULTS.values()]
        if not self.model_var.get() or self.model_var.get() in all_default_models:
            self.model_var.set(defaults.get("model", ""))

    def _save(self):
        label = self.label_var.get().strip()
        if not label:
            messagebox.showerror("Erreur", "Le nom du profil est obligatoire.", parent=self)
            return
        name = self.original_name or slugify(label)
        self.result = {
            "name": name,
            "data": {
                "label": label,
                "url": self.url_var.get().strip(),
                "key": self.key_var.get().strip(),
                "model": self.model_var.get().strip(),
                "type": self.type_var.get(),
                "enabled": self.enabled_var.get(),
            }
        }
        if self.on_save:
            self.on_save(self.original_name, self.result)
        self.destroy()


# ═════════════════════════════════════════════════════════════════════════════
#  Main Window
# ═════════════════════════════════════════════════════════════════════════════

class ConfigWindow(tk.Tk):
    def __init__(self, on_close=None):
        super().__init__()
        self.on_close_callback = on_close
        self.title("Voice Transcriber — Paramètres")
        self.geometry("640x720")
        self.minsize(540, 500)
        _set_window_icon(self)
        self.configure(bg=C.BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.data = load_config()

        # Title bar
        hdr = tk.Frame(self, bg=C.SURFACE)
        hdr.pack(fill="x")
        hdr_in = tk.Frame(hdr, bg=C.SURFACE)
        hdr_in.pack(fill="x", padx=20, pady=12)
        tk.Label(hdr_in, text="Voice Transcriber", font=F_TITLE,
                 bg=C.SURFACE, fg=C.TEXT).pack(side="left")
        tk.Label(hdr_in, text="Paramètres", font=F_BODY,
                 bg=C.SURFACE, fg=C.TEXT_DIM).pack(side="left", padx=(8, 0))

        # Scrollable body
        container = tk.Frame(self, bg=C.BG)
        container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(container, bg=C.BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=C.BG)
        self._cw = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._cw, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(-(e.delta // 120), "units"))

        self._build_settings()
        self._build_profiles()

        # Bottom bar
        bar = tk.Frame(self, bg=C.SURFACE)
        bar.pack(fill="x", side="bottom")
        bar_in = tk.Frame(bar, bg=C.SURFACE)
        bar_in.pack(fill="x", padx=20, pady=10)
        btn(bar_in, "Fermer", C.SURFACE_ALT, C.TEXT_SEC, self._on_close,
            padx=20, pady=7).pack(side="right")

    # ── Settings ────────────────────────────────────────────────────────

    def _build_settings(self):
        settings = self.data.get("settings", {})

        section_title(self.body, "Paramètres généraux",
                      "Redémarrage nécessaire après modification")

        card = tk.Frame(self.body, bg=C.SURFACE)
        card.pack(fill="x", padx=24, pady=(4, 0))
        inner = tk.Frame(card, bg=C.SURFACE)
        inner.pack(fill="x", padx=16, pady=14)

        # Hotkey
        self.hotkey_var = tk.StringVar(value=settings.get("hotkey", "ctrl+space"))
        field_row(inner, "Raccourci clavier",
                  "Combinaison pour démarrer / arrêter l'enregistrement",
                  lambda p: tk.Entry(p, textvariable=self.hotkey_var, font=F_MONO, width=18,
                                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                                     relief="flat", bd=5).pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # Whisper model
        self.model_var = tk.StringVar(value=settings.get("whisper_model", "medium"))
        self.model_desc_label = None

        def _make_model(p):
            cb = ttk.Combobox(p, textvariable=self.model_var,
                              values=[k for k, _ in WHISPER_MODELS],
                              state="readonly", width=14, font=F_BODY)
            cb.pack()
            cb.bind("<<ComboboxSelected>>", lambda e: self._update_model_desc())

        field_row(inner, "Modèle Whisper local",
                  "Moteur de transcription local (fallback si les API cloud échouent)",
                  _make_model)

        self.model_desc_label = tk.Label(inner, text="", font=F_TINY,
                                         bg=C.SURFACE, fg=C.TEXT_DIM,
                                         anchor="w", justify="left")
        self.model_desc_label.pack(fill="x")
        self._update_model_desc()

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # Device (CPU / CUDA)
        self.device_var = tk.StringVar(value=settings.get("whisper_device", "auto"))
        field_row(inner, "Accélération matérielle",
                  "Auto détecte automatiquement le GPU.\n"
                  "CUDA utilise le GPU NVIDIA (beaucoup plus rapide).",
                  lambda p: ttk.Combobox(p, textvariable=self.device_var,
                                         values=["auto", "cpu", "cuda"],
                                         state="readonly", width=14, font=F_BODY).pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # HuggingFace token
        self.hf_token_var = tk.StringVar(value=settings.get("hf_token", ""))
        field_row(inner, "Token HuggingFace (optionnel)",
                  "Augmente les quotas de téléchargement des modèles Whisper.\n"
                  "Créez un token sur huggingface.co/settings/tokens",
                  lambda p: tk.Entry(p, textvariable=self.hf_token_var, font=F_MONO,
                                     width=22, bg=C.INPUT, fg=C.TEXT,
                                     insertbackground=C.TEXT, relief="flat",
                                     bd=5, show="•").pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # Language
        self.lang_var = tk.StringVar(value=settings.get("whisper_language", "fr"))
        field_row(inner, "Langue de transcription",
                  "Langue principale de vos enregistrements",
                  lambda p: ttk.Combobox(p, textvariable=self.lang_var,
                                         values=[k for k, _ in LANGUAGES],
                                         state="readonly", width=14, font=F_BODY).pack())

        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=4)

        # WAV lifetime
        self.lifetime_var = tk.StringVar(value=str(settings.get("max_wav_lifetime", 120)))
        def _make_lifetime(p):
            f = tk.Frame(p, bg=C.SURFACE)
            f.pack()
            tk.Entry(f, textvariable=self.lifetime_var, font=F_MONO, width=5,
                     bg=C.INPUT, fg=C.TEXT, insertbackground=C.TEXT,
                     relief="flat", bd=5).pack(side="left")
            tk.Label(f, text=" min", font=F_SMALL, bg=C.SURFACE, fg=C.TEXT_SEC).pack(side="left")

        field_row(inner, "Rétention des enregistrements",
                  "Les fichiers audio plus anciens sont supprimés automatiquement",
                  _make_lifetime)

        # Save
        save_row = tk.Frame(inner, bg=C.SURFACE)
        save_row.pack(fill="x", pady=(14, 2))
        btn(save_row, "Enregistrer les paramètres", C.ACCENT, "#fff",
            self._save_settings, font=F_H3, padx=18, pady=6).pack(side="right")

        # Benchmark
        tk.Frame(inner, bg=C.BORDER, height=1).pack(fill="x", pady=(12, 4))
        bench_row = tk.Frame(inner, bg=C.SURFACE)
        bench_row.pack(fill="x", pady=(2, 2))
        tk.Label(bench_row, text="Compare les performances de tous les profils API actifs",
                 font=F_TINY, bg=C.SURFACE, fg=C.TEXT_DIM, anchor="w",
                 justify="left").pack(side="left", fill="x", expand=True)
        btn(bench_row, "🔬 Benchmark", "#5e35b1", "#fff",
            self._launch_benchmark, font=F_BODY, padx=14, pady=4).pack(side="right")

    def _update_model_desc(self):
        if not self.model_desc_label:
            return
        m = self.model_var.get()
        for k, d in WHISPER_MODELS:
            if k == m:
                self.model_desc_label.config(text=d)
                return
        self.model_desc_label.config(text="")

    def _save_settings(self):
        s = self.data.setdefault("settings", {})
        s["hotkey"] = self.hotkey_var.get().strip() or "ctrl+space"
        s["whisper_language"] = self.lang_var.get()
        s["whisper_model"] = self.model_var.get()
        s["whisper_device"] = self.device_var.get()
        hf = self.hf_token_var.get().strip()
        if hf:
            s["hf_token"] = hf
        elif "hf_token" in s:
            del s["hf_token"]
        try:
            s["max_wav_lifetime"] = int(self.lifetime_var.get())
        except ValueError:
            s["max_wav_lifetime"] = 120
        save_config(self.data)
        if messagebox.askokcancel(
                "Paramètres enregistrés",
                "Les paramètres ont été sauvegardés.\n\n"
                "L'application va redémarrer pour appliquer les modifications.",
                parent=self):
            self._restart_app()

    def _restart_app(self):
        """Restart Voice Transcriber by launching a new instance then closing."""
        import sys
        import subprocess
        import time as _time
        # Find the main script
        pyw = os.path.join(SCRIPT_DIR, "voice_transcriber.pyw")
        py = os.path.join(SCRIPT_DIR, "voice_transcriber.py")
        script = pyw if os.path.isfile(pyw) else py
        # Find pythonw for silent launch
        venv_pythonw = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "pythonw.exe")
        if os.path.isfile(venv_pythonw):
            exe = venv_pythonw
        else:
            exe = sys.executable
            if exe.lower().endswith("python.exe"):
                pw = exe[:-10] + "pythonw.exe"
                if os.path.isfile(pw):
                    exe = pw
        # Write restart flag so the running instance knows to quit
        flag = os.path.join(SCRIPT_DIR, ".restart")
        with open(flag, "w") as f:
            f.write("restart")
        # Wait for old instance to consume flag (max 5s)
        for _ in range(50):
            if not os.path.isfile(flag):
                break
            _time.sleep(0.1)
        # Small delay to let old instance fully shut down
        _time.sleep(1)
        # Launch new instance
        subprocess.Popen([exe, script])
        self._on_close()

    def _launch_benchmark(self):
        """Launch benchmark after warning the user about token consumption."""
        import subprocess

        # List enabled profiles
        profiles = self.data.get("profiles", {})
        active = [p.get("label", n) for n, p in profiles.items()
                  if p.get("enabled", True) and p.get("key")]
        active.append("Whisper Local")

        # Find recent recordings
        rec_dir = os.path.join(SCRIPT_DIR, "recordings")
        rec_files = []
        if os.path.isdir(rec_dir):
            rec_files = sorted(
                [f for f in os.listdir(rec_dir) if f.endswith(".wav") and f.startswith("rec_")],
                reverse=True
            )[:10]

        if not rec_files:
            messagebox.showwarning("Aucun enregistrement",
                                   "Aucun fichier audio disponible pour le benchmark.\n"
                                   "Effectuez d'abord une transcription.",
                                   parent=self)
            return

        # Build warning message
        api_list = "\n".join(f"  • {a}" for a in active)
        msg = (
            f"Le benchmark va tester TOUS les profils actifs :\n\n"
            f"{api_list}\n\n"
            f"⚠️ Chaque profil consommera des tokens/crédits API.\n\n"
            f"Le dernier enregistrement sera utilisé :\n"
            f"  📁 {rec_files[0]}\n\n"
            f"Continuer ?"
        )

        if not messagebox.askokcancel("Lancer le benchmark", msg, parent=self):
            return

        # Launch benchmark
        wav_path = os.path.join(rec_dir, rec_files[0])
        import sys
        python_exe = sys.executable
        if python_exe.lower().endswith("pythonw.exe"):
            python_exe = python_exe[:-5] + ".exe"
        script = os.path.join(SCRIPT_DIR, "voice_transcriber.py")
        subprocess.Popen(
            [python_exe, script, "--benchmark", wav_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    # ── Profiles ────────────────────────────────────────────────────────

    def _build_profiles(self):
        if hasattr(self, "_prof_section"):
            self._prof_section.destroy()
        self._prof_section = tk.Frame(self.body, bg=C.BG)
        self._prof_section.pack(fill="x")

        hdr = section_title(self._prof_section, "Profils API",
                            "Services de transcription cloud")
        btn(hdr, "Ajouter un profil", C.ACCENT, "#fff", self._add_profile,
            font=F_SMALL, padx=12, pady=3).pack(side="right")

        profiles = self.data.get("profiles", {})
        default = self.data.get("default", "")

        if not profiles:
            empty = tk.Frame(self._prof_section, bg=C.SURFACE)
            empty.pack(fill="x", padx=24, pady=(6, 0))
            tk.Label(empty,
                     text="Aucun profil configuré.\n"
                          "Cliquez « Ajouter un profil » pour connecter un service cloud.",
                     font=F_BODY, bg=C.SURFACE, fg=C.TEXT_DIM, justify="center",
                     pady=24).pack()
        else:
            for name, pdata in profiles.items():
                self._profile_card(name, pdata, name == default)

        # Fallback info
        info = tk.Frame(self._prof_section, bg=C.BG)
        info.pack(fill="x", padx=24, pady=(12, 20))
        tk.Label(info,
                 text="Le moteur Whisper local est toujours disponible comme fallback, "
                      "même sans profil API configuré.",
                 font=F_TINY, bg=C.BG, fg=C.TEXT_DIM, wraplength=500,
                 anchor="w", justify="left").pack(fill="x")

    def _profile_card(self, name, pdata, is_default):
        enabled = pdata.get("enabled", True)
        bg = C.SURFACE if enabled else C.SURFACE_ALT

        card = tk.Frame(self._prof_section, bg=bg)
        card.pack(fill="x", padx=24, pady=(6, 0))
        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="x", padx=16, pady=12)

        # Title + badges
        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")

        label = pdata.get("label", name)
        tk.Label(top, text=label, font=F_H3, bg=bg,
                 fg=C.TEXT if enabled else C.TEXT_DIM).pack(side="left")

        if is_default:
            tk.Label(top, text=" PAR DÉFAUT ", font=F_TINY,
                     bg=C.GREEN_BG, fg=C.GREEN, padx=6, pady=1).pack(side="left", padx=(8, 0))
        if not enabled:
            tk.Label(top, text=" DÉSACTIVÉ ", font=F_TINY,
                     bg=C.RED_BG, fg=C.RED, padx=6, pady=1).pack(side="left", padx=(8, 0))

        # Protocol + model
        proto = pdata.get("type", "?")
        proto_name = PROTOCOL_NAMES.get(proto, proto)
        model = pdata.get("model", "")
        detail = f"{proto_name}  ·  Modèle : {model}" if model else proto_name
        tk.Label(inner, text=detail, font=F_SMALL, bg=bg,
                 fg=C.TEXT_DIM, anchor="w").pack(fill="x", pady=(2, 0))

        # Masked key
        key = pdata.get("key", "")
        if key:
            if len(key) > 14:
                masked = key[:6] + "●" * min(8, len(key) - 10) + key[-4:]
            else:
                masked = "●" * len(key)
            tk.Label(inner, text=f"Clé : {masked}", font=F_TINY, bg=bg,
                     fg=C.TEXT_DIM, anchor="w").pack(fill="x")

        # Action buttons — clear text, no ambiguous icons
        btns = tk.Frame(inner, bg=bg)
        btns.pack(fill="x", pady=(8, 0))
        _b = dict(font=F_SMALL, padx=10, pady=3)

        btn(btns, "Tester", C.GREEN_BG, C.GREEN,
            lambda n=name, d=pdata: self._test_profile(n, d), **_b).pack(side="left", padx=(0, 4))

        btn(btns, "Modifier", C.ACCENT, "#fff",
            lambda n=name, d=pdata: self._edit_profile(n, d), **_b).pack(side="left", padx=(0, 4))

        if enabled:
            btn(btns, "Désactiver", C.SURFACE_ALT, C.ORANGE,
                lambda n=name: self._toggle(n), **_b).pack(side="left", padx=(0, 4))
        else:
            btn(btns, "Activer", C.GREEN_BG, C.GREEN,
                lambda n=name: self._toggle(n), **_b).pack(side="left", padx=(0, 4))

        if not is_default and enabled:
            btn(btns, "Par défaut", C.SURFACE_ALT, C.TEXT_SEC,
                lambda n=name: self._set_default(n), **_b).pack(side="left", padx=(0, 4))

        btn(btns, "Supprimer", C.RED_BG, C.RED,
            lambda n=name: self._delete(n), **_b).pack(side="right")

    # ── Actions ─────────────────────────────────────────────────────────

    def _toggle(self, name):
        self.data["profiles"][name]["enabled"] = not self.data["profiles"][name].get("enabled", True)
        save_config(self.data)
        self._build_profiles()

    def _set_default(self, name):
        self.data["default"] = name
        save_config(self.data)
        self._build_profiles()

    def _add_profile(self):
        ProfileEditor(self, on_save=self._on_saved)

    def _edit_profile(self, name, data):
        ProfileEditor(self, profile_name=name, profile_data=data, on_save=self._on_saved)

    def _on_saved(self, original_name, result):
        profiles = self.data.setdefault("profiles", {})
        if original_name and original_name != result["name"] and original_name in profiles:
            del profiles[original_name]
            if self.data.get("default") == original_name:
                self.data["default"] = result["name"]
        profiles[result["name"]] = result["data"]
        save_config(self.data)
        self._build_profiles()

    def _delete(self, name):
        label = self.data["profiles"][name].get("label", name)
        if messagebox.askyesno("Confirmer la suppression",
                               f"Supprimer « {label} » ?\nCette action est irréversible.",
                               parent=self):
            del self.data["profiles"][name]
            if self.data.get("default") == name:
                remaining = [n for n, p in self.data["profiles"].items() if p.get("enabled", True)]
                self.data["default"] = remaining[0] if remaining else "local"
            save_config(self.data)
            self._build_profiles()

    def _test_profile(self, name, pdata):
        label = pdata.get("label", name)
        if not pdata.get("key"):
            messagebox.showwarning("Test impossible",
                                   f"« {label} » n'a pas de clé API.", parent=self)
            return
        self.title(f"Test en cours — {label}…")
        self.update()

        def _run():
            api_type = pdata.get("type", "")
            try:
                import requests
                if api_type == "assemblyai":
                    url = pdata.get("url") or PROTOCOL_DEFAULTS["assemblyai"]["url"]
                    r = requests.post(f"{url}/v2/upload", data=b"\x00" * 100,
                                      headers={"authorization": pdata["key"],
                                               "content-type": "application/octet-stream"},
                                      timeout=10)
                    r.raise_for_status()
                    msg = "Connexion réussie.\nEndpoint upload OK."

                elif api_type == "openai":
                    url = pdata.get("url") or PROTOCOL_DEFAULTS["openai"]["url"]
                    r = requests.get(f"{url}/v1/models",
                                     headers={"Authorization": f"Bearer {pdata['key']}"},
                                     timeout=10)
                    r.raise_for_status()
                    msg = "Connexion réussie.\nClé API valide."

                elif api_type in ("gemini", "google"):
                    url = pdata.get("url") or PROTOCOL_DEFAULTS["gemini"]["url"]
                    model = pdata.get("model") or "gemini-2.0-flash"
                    r = requests.post(
                        f"{url}/v1beta/models/{model}:generateContent?key={pdata['key']}",
                        json={"contents": [{"parts": [{"text": "OK"}]}]}, timeout=10)
                    r.raise_for_status()
                    msg = f"Connexion réussie.\nModèle {model} accessible."

                elif api_type == "revai":
                    url = pdata.get("url") or PROTOCOL_DEFAULTS["revai"]["url"]
                    r = requests.get(f"{url}/account",
                                     headers={"Authorization": f"Bearer {pdata['key']}"},
                                     timeout=10)
                    r.raise_for_status()
                    bal = r.json().get("balance_seconds", "?")
                    if isinstance(bal, (int, float)):
                        bal = f"{bal / 60:.0f} minutes"
                    msg = f"Connexion réussie.\nCrédit : {bal}"

                elif api_type == "gemini_live":
                    import asyncio
                    import websockets
                    model = pdata.get("model") or "gemini-2.5-flash-native-audio-preview-12-2025"
                    ws_url = (
                        f"wss://generativelanguage.googleapis.com/ws/"
                        f"google.ai.generativelanguage.v1beta.GenerativeService."
                        f"BidiGenerateContent?key={pdata['key']}"
                    )
                    async def _test_ws():
                        async with websockets.connect(ws_url) as ws:
                            cfg = {"setup": {"model": f"models/{model}",
                                             "generationConfig": {"responseModalities": ["AUDIO"]}}}
                            await ws.send(json.dumps(cfg))
                            await asyncio.wait_for(ws.recv(), timeout=10)
                            return True
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(_test_ws())
                    finally:
                        loop.close()
                    msg = f"Connexion WebSocket réussie.\nModèle {model} accessible."

                else:
                    msg = f"Protocole « {api_type} » — test non disponible."

                result = ("ok", f"Test réussi — {label}", msg)
            except Exception as e:
                err = str(e)[:300]
                if hasattr(e, "response") and e.response is not None:
                    err = f"HTTP {e.response.status_code}\n{err}"
                result = ("err", f"Échec — {label}", f"Erreur :\n{err}")

            self.after(0, lambda: self._show_result(*result))

        threading.Thread(target=_run, daemon=True).start()

    def _show_result(self, level, title, msg):
        self.title("Voice Transcriber — Paramètres")
        (messagebox.showinfo if level == "ok" else messagebox.showerror)(title, msg, parent=self)

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


def open_config(on_close=None):
    ConfigWindow(on_close=on_close).mainloop()


if __name__ == "__main__":
    open_config()
