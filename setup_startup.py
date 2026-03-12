"""
Setup / Uninstall — Adds or removes Voice Transcriber from Windows startup.

Usage:
    python setup_startup.py install     → Add to startup
    python setup_startup.py uninstall   → Remove from startup
"""

import os
import sys
import winreg

APP_NAME = "VoiceTranscriber"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYW_PATH = os.path.join(SCRIPT_DIR, "voice_transcriber.pyw")

# We use pythonw.exe so there is absolutely no console window
def _find_pythonw() -> str:
    """Find pythonw.exe — prioritize the venv if it exists."""
    # 1. Check for a .venv right next to this script
    venv_pythonw = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "pythonw.exe")
    if os.path.isfile(venv_pythonw):
        return venv_pythonw
    # 2. Fallback: pythonw next to the current interpreter
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.isfile(pythonw):
        return pythonw
    # 3. Last resort
    return "pythonw.exe"


def install():
    pythonw = _find_pythonw()
    command = f'"{pythonw}" "{PYW_PATH}"'

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    winreg.CloseKey(key)

    print(f"✅ {APP_NAME} ajouté au démarrage Windows.")
    print(f"   Commande : {command}")
    print(f"   Logs : {os.path.join(SCRIPT_DIR, 'voice_transcriber.log')}")


def uninstall():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"✅ {APP_NAME} retiré du démarrage Windows.")
    except FileNotFoundError:
        print(f"ℹ️  {APP_NAME} n'était pas dans le démarrage.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "uninstall"):
        print("Usage :")
        print("  python setup_startup.py install     → Ajouter au démarrage")
        print("  python setup_startup.py uninstall   → Retirer du démarrage")
        sys.exit(1)

    if sys.argv[1] == "install":
        install()
    else:
        uninstall()


if __name__ == "__main__":
    main()
