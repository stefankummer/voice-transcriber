"""
Internationalization module for Voice Transcriber.
Supports English (en) and French (fr).
Auto-detects language from profiles.json on import.
"""

import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROFILES_FILE = os.path.join(SCRIPT_DIR, "profiles.json")

_current_lang = "en"

# Auto-detect language from profiles.json
try:
    with open(_PROFILES_FILE, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
    _current_lang = _cfg.get("settings", {}).get("ui_language", "en")
except Exception:
    pass

# ═════════════════════════════════════════════════════════════════════════════
#  UI Strings — English / French
# ═════════════════════════════════════════════════════════════════════════════

_STRINGS = {
    "en": {
        # ── Overlay ──────────────────────────────────────────────────────
        "overlay.recording":            "Recording…",
        "overlay.transcribing":         "Transcribing…",
        "overlay.transcribing_words":   "Transcribing… {count} word{s}",
        "overlay.cancelled":            "Cancelled",
        "overlay.done":                 "✓ Done",
        "overlay.error":                "✗ Error",
        "overlay.downloading":          "Downloading model {name}…",
        "overlay.downloading_generic":  "Downloading model…",
        "overlay.auto_enter_warning":   "⏎ Auto Enter enabled",
        "overlay.auto_enter_disable":   "[disable]",

        # ── Tray menu ───────────────────────────────────────────────────
        "tray.stop":                    "⏹ Stop",
        "tray.record":                  "🎤 Record",
        "tray.auto_enter":              "⏎ Auto enter",
        "tray.autostart":               "🚀 Windows auto-start",
        "tray.recordings":              "📋 Recordings",
        "tray.recordings_none":         "📋 Recordings (none)",
        "tray.retranscribe_header":     "── Re-transcribe ──",
        "tray.copy_header":             "── Copy ──",
        "tray.open_folder":             "📂 Open folder",
        "tray.config":                  "⚙️ Settings",
        "tray.documentation":           "📖 Documentation",
        "tray.quit":                    "Quit",

        # ── Config GUI — window / headers ────────────────────────────────
        "config.title":                 "Voice Transcriber — Settings",
        "config.header":                "Voice Transcriber",
        "config.header_sub":            "Settings",
        "config.close":                 "Close",

        # ── Config GUI — general settings ────────────────────────────────
        "config.section.general":       "General Settings",
        "config.section.general_desc":  "Restart required after changes",

        "config.field.language":        "Interface Language",
        "config.field.language_desc":   "Language for menus, overlay, and messages",

        "config.field.hotkey":          "Keyboard Shortcut",
        "config.field.hotkey_desc":     "Key combination to start/stop recording",

        "config.field.whisper_model":       "Local Whisper Model",
        "config.field.whisper_model_desc":  "Local transcription engine (fallback if cloud APIs fail)",

        "config.field.device":          "Hardware Acceleration",
        "config.field.device_desc":     "Auto automatically detects GPU.\nCUDA uses NVIDIA GPU (much faster).",

        "config.field.hf_token":        "HuggingFace Token (optional)",
        "config.field.hf_token_desc":   "Increases model download quotas.\nCreate a token at huggingface.co/settings/tokens",

        "config.field.trans_lang":      "Transcription Language",
        "config.field.trans_lang_desc": "Primary language of your recordings",

        "config.field.retention":       "Recording Retention",
        "config.field.retention_desc":  "Older audio files are deleted automatically",
        "config.field.retention_unit":  " min",

        "config.btn.save_settings":     "Save Settings",
        "config.btn.benchmark":         "🔬 Benchmark",
        "config.benchmark_desc":        "Compare performance of all active API profiles",

        "config.msg.saved_title":       "Settings Saved",
        "config.msg.saved_text":        "Settings have been saved.\n\n"
                                        "The application will restart to apply changes.",

        # ── Config GUI — profiles section ────────────────────────────────
        "config.section.profiles":      "API Profiles",
        "config.section.profiles_desc": "Cloud transcription services",
        "config.btn.add_profile":       "Add Profile",
        "config.profiles_empty":        "No profiles configured.\n"
                                        "Click 'Add Profile' to connect a cloud service.",
        "config.profiles_fallback":     "The local Whisper engine is always available as a fallback, "
                                        "even without any API profile configured.",

        # ── Config GUI — profile card ────────────────────────────────────
        "config.badge.default":         " DEFAULT ",
        "config.badge.disabled":        " DISABLED ",
        "config.btn.test":              "Test",
        "config.btn.edit":              "Edit",
        "config.btn.disable":           "Disable",
        "config.btn.enable":            "Enable",
        "config.btn.default":           "Default",
        "config.btn.delete":            "Delete",

        # ── Config GUI — profile editor ──────────────────────────────────
        "config.editor.title_edit":     "Edit Profile",
        "config.editor.title_new":      "New Profile",

        "config.editor.name":           "Profile Name",
        "config.editor.name_desc":      "Name displayed in menu and tray icon",
        "config.editor.protocol":       "Communication Protocol",
        "config.editor.protocol_desc":  "Determines how audio is sent to the service",
        "config.editor.url":            "API URL",
        "config.editor.url_desc":       "Transcription service endpoint",
        "config.editor.key":            "API Key",
        "config.editor.key_desc":       "Authentication key provided by the service",
        "config.editor.model":          "Model",
        "config.editor.model_desc":     "Model identifier (leave blank if not applicable)",
        "config.editor.enabled":        "  Profile active",
        "config.editor.enabled_desc":   "— Uncheck to disable without deleting",
        "config.editor.save":           "Save",
        "config.editor.cancel":         "Cancel",

        "config.editor.error_name":     "Profile name is required.",

        # ── Config GUI — test results ────────────────────────────────────
        "config.test.no_key":           "Test unavailable",
        "config.test.no_key_msg":       "'{label}' has no API key.",
        "config.test.running":          "Testing — {label}…",
        "config.test.ok_title":         "Test passed — {label}",
        "config.test.fail_title":       "Failed — {label}",
        "config.test.error_prefix":     "Error:\n{err}",
        "config.test.assemblyai_ok":    "Connection successful.\nUpload endpoint OK.",
        "config.test.openai_ok":        "Connection successful.\nAPI key valid.",
        "config.test.gemini_ok":        "Connection successful.\nModel {model} accessible.",
        "config.test.revai_ok":         "Connection successful.\nBalance: {balance}",
        "config.test.gemini_live_ok":   "WebSocket connection successful.\nModel {model} accessible.",
        "config.test.unknown_proto":    "Protocol '{proto}' — test not available.",

        # ── Config GUI — benchmark dialog ────────────────────────────────
        "config.bench.no_files_title":  "No recordings",
        "config.bench.no_files_msg":    "No audio files available for benchmark.\n"
                                        "Perform a transcription first.",
        "config.bench.confirm_title":   "Launch Benchmark",
        "config.bench.confirm_msg":     "Benchmark will test ALL active profiles:\n\n"
                                        "{profiles}\n\n"
                                        "⚠️ Each profile will consume API tokens/credits.\n\n"
                                        "Last recording will be used:\n"
                                        "  📁 {file}\n\n"
                                        "Continue?",

        # ── Config GUI — delete confirmation ─────────────────────────────
        "config.delete.title":          "Confirm Deletion",
        "config.delete.msg":            "Delete '{label}'?\nThis action cannot be undone.",

        # ── Benchmark CLI ────────────────────────────────────────────────
        "bench.title":                  "🎤 VOICE TRANSCRIBER — BENCHMARK",
        "bench.audio":                  "Audio: {seconds:.1f}s ({bytes:,} bytes)",
        "bench.file":                   "File: {path}",
        "bench.summary":                "📊 SUMMARY (sorted by speed)",
        "bench.col_profile":            "Profile",
        "bench.col_time":               "Time",
        "bench.col_text":               "Text",
        "bench.skip_no_key":            "{label} — API key missing, skipped",
        "bench.skip_placeholder":       "{label} — API key placeholder, skipped",
        "bench.running":                "▶  {label} (type={type})…",
        "bench.result_text":            "Text: {text}",
        "bench.result_time":            "Time: {ms:,.0f} ms",
        "bench.result_error":           "ERROR: {error}",
        "bench.press_enter":            "Press Enter to close… ",

        # ── Setup startup ────────────────────────────────────────────────
        "setup.installed":              "✅ {app} added to Windows startup.",
        "setup.command":                "   Command: {cmd}",
        "setup.logs":                   "   Logs: {path}",
        "setup.uninstalled":            "✅ {app} removed from Windows startup.",
        "setup.not_found":              "ℹ️  {app} was not in startup.",
        "setup.usage":                  "Usage:",
        "setup.usage_install":          "  python setup_startup.py install     → Add to startup",
        "setup.usage_uninstall":        "  python setup_startup.py uninstall   → Remove from startup",
    },

    "fr": {
        # ── Overlay ──────────────────────────────────────────────────────
        "overlay.recording":            "Enregistrement…",
        "overlay.transcribing":         "Transcription…",
        "overlay.transcribing_words":   "Transcription… {count} mot{s}",
        "overlay.cancelled":            "Annulé",
        "overlay.done":                 "✓ Terminé",
        "overlay.error":                "✗ Erreur",
        "overlay.downloading":          "Téléchargement du modèle {name}…",
        "overlay.downloading_generic":  "Téléchargement du modèle…",
        "overlay.auto_enter_warning":   "⏎ Auto Enter activé",
        "overlay.auto_enter_disable":   "[désactiver]",

        # ── Tray menu ───────────────────────────────────────────────────
        "tray.stop":                    "⏹ Arrêter",
        "tray.record":                  "🎤 Enregistrer",
        "tray.auto_enter":              "⏎ Enter auto",
        "tray.autostart":               "🚀 Démarrage auto Windows",
        "tray.recordings":              "📋 Enregistrements",
        "tray.recordings_none":         "📋 Enregistrements (aucun)",
        "tray.retranscribe_header":     "── Retranscrire ──",
        "tray.copy_header":             "── Copier ──",
        "tray.open_folder":             "📂 Ouvrir le dossier",
        "tray.config":                  "⚙️ Configuration",
        "tray.documentation":           "📖 Documentation",
        "tray.quit":                    "Quitter",

        # ── Config GUI — window / headers ────────────────────────────────
        "config.title":                 "Voice Transcriber — Paramètres",
        "config.header":                "Voice Transcriber",
        "config.header_sub":            "Paramètres",
        "config.close":                 "Fermer",

        # ── Config GUI — general settings ────────────────────────────────
        "config.section.general":       "Paramètres généraux",
        "config.section.general_desc":  "Redémarrage nécessaire après modification",

        "config.field.language":        "Langue de l'interface",
        "config.field.language_desc":   "Langue des menus, de l'overlay et des messages",

        "config.field.hotkey":          "Raccourci clavier",
        "config.field.hotkey_desc":     "Combinaison pour démarrer / arrêter l'enregistrement",

        "config.field.whisper_model":       "Modèle Whisper local",
        "config.field.whisper_model_desc":  "Moteur de transcription local (fallback si les API cloud échouent)",

        "config.field.device":          "Accélération matérielle",
        "config.field.device_desc":     "Auto détecte automatiquement le GPU.\n"
                                        "CUDA utilise le GPU NVIDIA (beaucoup plus rapide).",

        "config.field.hf_token":        "Token HuggingFace (optionnel)",
        "config.field.hf_token_desc":   "Augmente les quotas de téléchargement des modèles Whisper.\n"
                                        "Créez un token sur huggingface.co/settings/tokens",

        "config.field.trans_lang":      "Langue de transcription",
        "config.field.trans_lang_desc": "Langue principale de vos enregistrements",

        "config.field.retention":       "Rétention des enregistrements",
        "config.field.retention_desc":  "Les fichiers audio plus anciens sont supprimés automatiquement",
        "config.field.retention_unit":  " min",

        "config.btn.save_settings":     "Enregistrer les paramètres",
        "config.btn.benchmark":         "🔬 Benchmark",
        "config.benchmark_desc":        "Compare les performances de tous les profils API actifs",

        "config.msg.saved_title":       "Paramètres enregistrés",
        "config.msg.saved_text":        "Les paramètres ont été sauvegardés.\n\n"
                                        "L'application va redémarrer pour appliquer les modifications.",

        # ── Config GUI — profiles section ────────────────────────────────
        "config.section.profiles":      "Profils API",
        "config.section.profiles_desc": "Services de transcription cloud",
        "config.btn.add_profile":       "Ajouter un profil",
        "config.profiles_empty":        "Aucun profil configuré.\n"
                                        "Cliquez « Ajouter un profil » pour connecter un service cloud.",
        "config.profiles_fallback":     "Le moteur Whisper local est toujours disponible comme fallback, "
                                        "même sans profil API configuré.",

        # ── Config GUI — profile card ────────────────────────────────────
        "config.badge.default":         " PAR DÉFAUT ",
        "config.badge.disabled":        " DÉSACTIVÉ ",
        "config.btn.test":              "Tester",
        "config.btn.edit":              "Modifier",
        "config.btn.disable":           "Désactiver",
        "config.btn.enable":            "Activer",
        "config.btn.default":           "Par défaut",
        "config.btn.delete":            "Supprimer",

        # ── Config GUI — profile editor ──────────────────────────────────
        "config.editor.title_edit":     "Modifier le profil",
        "config.editor.title_new":      "Nouveau profil",

        "config.editor.name":           "Nom du profil",
        "config.editor.name_desc":      "Nom affiché dans le menu et le tray icon",
        "config.editor.protocol":       "Protocole de communication",
        "config.editor.protocol_desc":  "Détermine comment l'audio est envoyé au service",
        "config.editor.url":            "URL de l'API",
        "config.editor.url_desc":       "Point d'entrée du service de transcription",
        "config.editor.key":            "Clé API",
        "config.editor.key_desc":       "Clé d'authentification fournie par le service",
        "config.editor.model":          "Modèle",
        "config.editor.model_desc":     "Identifiant du modèle (laisser vide si non applicable)",
        "config.editor.enabled":        "  Profil actif",
        "config.editor.enabled_desc":   "— Décocher pour désactiver sans supprimer",
        "config.editor.save":           "Sauvegarder",
        "config.editor.cancel":         "Annuler",

        "config.editor.error_name":     "Le nom du profil est obligatoire.",

        # ── Config GUI — test results ────────────────────────────────────
        "config.test.no_key":           "Test impossible",
        "config.test.no_key_msg":       "« {label} » n'a pas de clé API.",
        "config.test.running":          "Test en cours — {label}…",
        "config.test.ok_title":         "Test réussi — {label}",
        "config.test.fail_title":       "Échec — {label}",
        "config.test.error_prefix":     "Erreur :\n{err}",
        "config.test.assemblyai_ok":    "Connexion réussie.\nEndpoint upload OK.",
        "config.test.openai_ok":        "Connexion réussie.\nClé API valide.",
        "config.test.gemini_ok":        "Connexion réussie.\nModèle {model} accessible.",
        "config.test.revai_ok":         "Connexion réussie.\nCrédit : {balance}",
        "config.test.gemini_live_ok":   "Connexion WebSocket réussie.\nModèle {model} accessible.",
        "config.test.unknown_proto":    "Protocole « {proto} » — test non disponible.",

        # ── Config GUI — benchmark dialog ────────────────────────────────
        "config.bench.no_files_title":  "Aucun enregistrement",
        "config.bench.no_files_msg":    "Aucun fichier audio disponible pour le benchmark.\n"
                                        "Effectuez d'abord une transcription.",
        "config.bench.confirm_title":   "Lancer le benchmark",
        "config.bench.confirm_msg":     "Le benchmark va tester TOUS les profils actifs :\n\n"
                                        "{profiles}\n\n"
                                        "⚠️ Chaque profil consommera des tokens/crédits API.\n\n"
                                        "Le dernier enregistrement sera utilisé :\n"
                                        "  📁 {file}\n\n"
                                        "Continuer ?",

        # ── Config GUI — delete confirmation ─────────────────────────────
        "config.delete.title":          "Confirmer la suppression",
        "config.delete.msg":            "Supprimer « {label} » ?\nCette action est irréversible.",

        # ── Benchmark CLI ────────────────────────────────────────────────
        "bench.title":                  "🎤 VOICE TRANSCRIBER — BENCHMARK",
        "bench.audio":                  "Audio : {seconds:.1f}s ({bytes:,} bytes)",
        "bench.file":                   "Fichier : {path}",
        "bench.summary":                "📊 RÉCAPITULATIF (trié par vitesse)",
        "bench.col_profile":            "Profil",
        "bench.col_time":               "Temps",
        "bench.col_text":               "Texte",
        "bench.skip_no_key":            "{label} — clé API manquante, ignoré",
        "bench.skip_placeholder":       "{label} — clé API placeholder, ignoré",
        "bench.running":                "▶  {label} (type={type})…",
        "bench.result_text":            "Texte : {text}",
        "bench.result_time":            "Temps : {ms:,.0f} ms",
        "bench.result_error":           "ERREUR : {error}",
        "bench.press_enter":            "Appuyez sur Entrée pour fermer… ",

        # ── Setup startup ────────────────────────────────────────────────
        "setup.installed":              "✅ {app} ajouté au démarrage Windows.",
        "setup.command":                "   Commande : {cmd}",
        "setup.logs":                   "   Logs : {path}",
        "setup.uninstalled":            "✅ {app} retiré du démarrage Windows.",
        "setup.not_found":              "ℹ️  {app} n'était pas dans le démarrage.",
        "setup.usage":                  "Usage :",
        "setup.usage_install":          "  python setup_startup.py install     → Ajouter au démarrage",
        "setup.usage_uninstall":        "  python setup_startup.py uninstall   → Retirer du démarrage",
    },
}

# ═════════════════════════════════════════════════════════════════════════════
#  Protocol Names & Descriptions
# ═════════════════════════════════════════════════════════════════════════════

_PROTO_NAMES = {
    "en": {
        "openai":      "OpenAI Compatible",
        "assemblyai":  "AssemblyAI",
        "revai":       "Rev.ai",
        "gemini":      "Google Gemini (Multimodal)",
        "gemini_live": "Gemini Live (WebSocket)",
    },
    "fr": {
        "openai":      "OpenAI Compatible",
        "assemblyai":  "AssemblyAI",
        "revai":       "Rev.ai",
        "gemini":      "Google Gemini (Multimodal)",
        "gemini_live": "Gemini Live (WebSocket)",
    },
}

_PROTO_DESCS = {
    "en": {
        "openai":      "Direct audio file upload, immediate response.\n"
                       "Works with: OpenAI, Groq, Together AI, FastWhisper Server, "
                       "and any /v1/audio/transcriptions compatible endpoint.",
        "assemblyai":  "File upload, then async polling for result.\n"
                       "Specific to the AssemblyAI API.",
        "revai":       "Multipart upload, async polling, then transcript retrieval.\n"
                       "Specific to the Rev.ai API.",
        "gemini":      "Base64-encoded audio sent in a multimodal prompt.\n"
                       "Works with Gemini models (Flash, Pro, etc.).",
        "gemini_live": "Real-time audio streaming via WebSocket.\n"
                       "PCM 16kHz audio sent in chunks, native transcription.\n"
                       "Model: gemini-2.5-flash-native-audio-preview",
    },
    "fr": {
        "openai":      "Envoi direct du fichier audio, réponse immédiate.\n"
                       "Fonctionne avec : OpenAI, Groq, Together AI, FastWhisper Server, "
                       "et tout endpoint compatible /v1/audio/transcriptions.",
        "assemblyai":  "Upload du fichier, puis polling asynchrone pour le résultat.\n"
                       "Spécifique à l'API AssemblyAI.",
        "revai":       "Upload multipart, polling asynchrone, puis récupération du transcript.\n"
                       "Spécifique à l'API Rev.ai.",
        "gemini":      "Audio encodé en base64 envoyé dans un prompt multimodal.\n"
                       "Fonctionne avec les modèles Gemini (Flash, Pro, etc.).",
        "gemini_live": "Streaming audio en temps réel via WebSocket.\n"
                       "Audio PCM 16kHz envoyé par chunks, transcription native.\n"
                       "Modèle : gemini-2.5-flash-native-audio-preview",
    },
}

# ═════════════════════════════════════════════════════════════════════════════
#  Whisper Model Descriptions
# ═════════════════════════════════════════════════════════════════════════════

_MODEL_DESCS = {
    "en": {
        "tiny":              "Tiny — Very fast, basic quality (~1GB RAM)",
        "tiny.en":           "Tiny EN — English only, very fast",
        "base":              "Base — Fast, decent quality (~1GB RAM)",
        "base.en":           "Base EN — English only, fast",
        "small":             "Small — Good speed/quality trade-off (~2GB RAM)",
        "small.en":          "Small EN — English only",
        "medium":            "Medium — Good quality (~5GB RAM)",
        "medium.en":         "Medium EN — English only",
        "large-v1":          "Large v1 — High quality (~10GB RAM)",
        "large-v2":          "Large v2 — Excellent quality (~10GB RAM)",
        "large-v3":          "Large v3 — Best quality (~10GB RAM)",
        "turbo":             "Turbo — Accelerated Large v3, good quality/speed ratio",
        "distil-small.en":   "Distil Small EN — Fast, English only",
        "distil-medium.en":  "Distil Medium EN — Fast, English only",
        "distil-large-v2":   "Distil Large v2 — Fast, near-Large quality",
        "distil-large-v3":   "Distil Large v3 — Fast, near-Large v3 quality",
        "distil-large-v3.5": "Distil Large v3.5 — Latest distilled model",
    },
    "fr": {
        "tiny":              "Tiny — Très rapide, qualité basique (~1 Go RAM)",
        "tiny.en":           "Tiny EN — Anglais uniquement, très rapide",
        "base":              "Base — Rapide, qualité correcte (~1 Go RAM)",
        "base.en":           "Base EN — Anglais uniquement, rapide",
        "small":             "Small — Bon compromis vitesse/qualité (~2 Go RAM)",
        "small.en":          "Small EN — Anglais uniquement",
        "medium":            "Medium — Bonne qualité (~5 Go RAM)",
        "medium.en":         "Medium EN — Anglais uniquement",
        "large-v1":          "Large v1 — Haute qualité (~10 Go RAM)",
        "large-v2":          "Large v2 — Excellente qualité (~10 Go RAM)",
        "large-v3":          "Large v3 — Meilleure qualité (~10 Go RAM)",
        "turbo":             "Turbo — Large v3 accéléré, bon rapport qualité/vitesse",
        "distil-small.en":   "Distil Small EN — Rapide, anglais uniquement",
        "distil-medium.en":  "Distil Medium EN — Rapide, anglais uniquement",
        "distil-large-v2":   "Distil Large v2 — Rapide, qualité proche de Large",
        "distil-large-v3":   "Distil Large v3 — Rapide, qualité proche de Large v3",
        "distil-large-v3.5": "Distil Large v3.5 — Le plus récent des modèles distillés",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
#  Public API
# ═════════════════════════════════════════════════════════════════════════════

def set_language(lang: str):
    """Set the active UI language ('en' or 'fr')."""
    global _current_lang
    if lang in _STRINGS:
        _current_lang = lang


def get_language() -> str:
    """Return the current UI language code."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Get a translated string by key. Supports {placeholder} formatting."""
    strings = _STRINGS.get(_current_lang, _STRINGS["en"])
    text = strings.get(key, _STRINGS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def proto_name(key: str) -> str:
    """Get the localized protocol display name."""
    names = _PROTO_NAMES.get(_current_lang, _PROTO_NAMES["en"])
    return names.get(key, key)


def proto_desc(key: str) -> str:
    """Get the localized protocol description."""
    descs = _PROTO_DESCS.get(_current_lang, _PROTO_DESCS["en"])
    return descs.get(key, "")


def model_desc(key: str) -> str:
    """Get the localized Whisper model description."""
    descs = _MODEL_DESCS.get(_current_lang, _MODEL_DESCS["en"])
    return descs.get(key, key)
