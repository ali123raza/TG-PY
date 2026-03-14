# TG-PY Unified Application

Backend aur Frontend dono ek hi folder mein combined - FastAPI ki zaroorat nahi, direct calls se realtime data sharing.

## Structure

```
full_app/
├── app.py                 # Main entry point
├── main.py               # UI components (PyQt6)
├── data_service.py       # Direct backend access (replaces API client)
├── models.py             # Data models
├── toast.py              # Toast notifications
├── campaign_dialog.py    # Campaign dialog
├── login_dialog.py       # Login dialog
├── core/                 # Backend modules
│   ├── __init__.py
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── models.py         # SQLAlchemy models
│   └── service_manager.py # Business logic
├── services/             # Telegram services
│   ├── __init__.py
│   ├── telegram.py       # Pyrogram client manager
│   ├── tdata_import.py   # tdata import
│   └── ...
└── requirements.txt
```

## Run Kaise Karein

```bash
cd full_app
pip install -r requirements.txt
python app.py
```

## Features

- ✅ Direct backend access (no FastAPI needed)
- ✅ Realtime data sharing between UI and backend
- ✅ PyQt6 modern dark theme UI
- ✅ SQLite database with async support
- ✅ Telegram account management
- ✅ Campaign management
- ✅ Proxy support
- ✅ Message templates

## Kya Kya Change Hua

1. **FastAPI removed**: Ab API calls ki zaroorat nahi, direct function calls use hote hain
2. **Combined folder**: Backend aur frontend ek hi `full_app` folder mein hain
3. **data_service.py**: New file jo API client ki jagah use hota hai
4. **service_manager.py**: Backend logic ko directly access karne ke liye
