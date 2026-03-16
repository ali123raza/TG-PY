"""
PyInstaller Runtime Hook — runs FIRST before any app code.
Creates required directories next to the EXE.
"""
import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    base = Path(sys.executable).parent
    for folder in ['data', 'sessions', 'media', 'tgdata', 'logs']:
        (base / folder).mkdir(parents=True, exist_ok=True)
