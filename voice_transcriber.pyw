"""
Silent launcher — runs voice_transcriber.py without a console window.
Rename or associate with pythonw.exe (.pyw extension) to hide the terminal.
"""
import os
import sys
import subprocess

# Ensure the script directory is the working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# If we're NOT already running from the venv, re-launch with the venv's pythonw
venv_pythonw = os.path.join(script_dir, ".venv", "Scripts", "pythonw.exe")
if os.path.isfile(venv_pythonw) and os.path.normcase(sys.executable) != os.path.normcase(venv_pythonw):
    # Re-exec with the venv interpreter (replaces this process)
    os.execv(venv_pythonw, [venv_pythonw, __file__])

# Import and run (only reached when running inside the venv)
sys.path.insert(0, script_dir)
from voice_transcriber import main

main()
