"""
TG-PY Configuration
Works in 3 modes:
  1. Dev:             python app.py           → paths relative to app.py
  2. PyInstaller EXE: TG-PY.exe              → paths next to EXE file
  3. Env override:    TG_BASE_DIR=/path      → custom path
"""
import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    """
    Detect correct base directory for runtime data (db, sessions, media).
    
    PyInstaller EXE:
      sys.frozen = True
      sys.executable = C:\\Users\\...\\TG-PY.exe
      → BASE_DIR = folder containing the EXE  (e.g. C:\\Users\\...\\)
      
    Dev mode (python app.py):
      __file__ = E:\\TG-PY\\core\\config.py
      → BASE_DIR = E:\\TG-PY\\  (2 levels up from config.py)
    """
    # 1. Explicit env override
    if 'TG_BASE_DIR' in os.environ:
        return Path(os.environ['TG_BASE_DIR'])

    # 2. PyInstaller frozen EXE
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent

    # 3. Dev mode — go up from core/config.py → project root
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()

# ── Runtime directories (created automatically on startup) ───────────────────
DATA_DIR     = BASE_DIR / "data"
SESSIONS_DIR = BASE_DIR / "sessions"
MEDIA_DIR    = BASE_DIR / "media"
TGDATA_DIR   = BASE_DIR / "tgdata"
LOGS_DIR      = BASE_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"   # app settings storage

# Create all dirs at import time — safe even if already exist
for _d in [DATA_DIR, SESSIONS_DIR, MEDIA_DIR, TGDATA_DIR, LOGS_DIR, SETTINGS_FILE.parent]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'tgpy.db'}"

# ── Telegram API ──────────────────────────────────────────────────────────────
API_ID   = int(os.getenv("TG_API_ID",   "2040"))
API_HASH = os.getenv("TG_API_HASH", "b18441a1ff607e10a989891a5462e627")

# ── App info ──────────────────────────────────────────────────────────────────
APP_NAME    = "TG-PY"
APP_VERSION = "1.0.0"