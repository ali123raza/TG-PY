import json
import os
from pathlib import Path

BASE_DIR = Path(os.environ['TG_BASE_DIR']) if 'TG_BASE_DIR' in os.environ else Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = BASE_DIR / "sessions"
MEDIA_DIR = BASE_DIR / "media"
TGDATA_DIR = BASE_DIR / "tgdata"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'tgpy.db'}"

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8767

# Default settings
_defaults = {
    "api_id": 2040,
    "api_hash": "b18441a1ff607e10a989891a5462e627",
    "default_delay_min": 30,
    "default_delay_max": 60,
    "max_per_account": 50,
    "flood_wait_cap": 120,
}


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return {**_defaults, **json.loads(SETTINGS_FILE.read_text())}
        except Exception:
            pass
    return dict(_defaults)


def _save_settings(data: dict):
    merged = {**_load_settings(), **data}
    SETTINGS_FILE.write_text(json.dumps(merged, indent=2))


def get_settings() -> dict:
    return _load_settings()


settings = _load_settings()

# Telegram API credentials — from settings file, env, or default
API_ID = int(os.getenv("TG_API_ID", str(settings.get("api_id", 0))))
API_HASH = os.getenv("TG_API_HASH", settings.get("api_hash", ""))
