# TG-PY Installer Builder

## 📦 Overview

Ye folder TG-PY ka **professional Windows installer** banata hai jo end-users ko distribute karne ke liye hai.

**Note:** Admin panel is separate - ye sirf user application hai.

---

## 📋 Requirements

### 1. Python 3.8+
Download: https://www.python.org/downloads/

### 2. Inno Setup (Required for installer)
Download: https://jrsoftware.org/isdl.php

**Installation Steps:**
1. Download `innosetup-6.x.x.exe`
2. Run installer
3. Default installation path: `C:\Program Files (x86)\Inno Setup 6`

---

## 🚀 Quick Start

### One-Click Build (Recommended)
```batch
cd installer
build_installer.bat
```

### Manual Build
```batch
cd installer
python installer_builder.py
```

---

## 📁 Output Files

After successful build:

```
dist/
├── TG-PY.exe                 ← Main application (standalone)
└── TG-PY-Setup-v1.0.0.exe    ← Installer (send to users)
```

---

## 📤 Distribution

### For End Users:
**Bhejein:** `TG-PY-Setup-v1.0.0.exe`

**User Installation Process:**
1. User download kare `TG-PY-Setup-v1.0.0.exe`
2. Run kare (Administrator rights required)
3. Installation folder select kare (default: `C:\Program Files (x86)\TG-PY`)
4. Desktop shortcut create ho jayega
5. App launch ho jayega

### User ke paas kya hoga after installation:
```
C:\Program Files (x86)\TG-PY\
├── TG-PY.exe           ← Main application
├── README.md           ← Documentation
├── requirements.txt    ← Dependencies list
├── data/               ← Database (auto-created)
├── sessions/           ← Telegram sessions (auto-created)
├── media/              ← Media files (auto-created)
├── tgdata/             ← Imported tdata (auto-created)
└── logs/               ← Logs (auto-created)

Desktop:
└── TG-PY.lnk          ← Shortcut
```

---

## 🔧 Admin Panel (Separate)

Admin panel alag se build hota hai:

```batch
admin_build.bat
```

**Output:** `dist\TG-PY-Admin.exe` (aapke paas rahega, user ko nahi milega)

---

## ⚠️ Troubleshooting

### Problem: "Inno Setup not found"
**Solution:** 
- Inno Setup install karein: https://jrsoftware.org/isdl.php
- Default path pe install ho: `C:\Program Files (x86)\Inno Setup 6`
- Script ko administrator run karein

### Problem: "TG-PY.exe not created"
**Solution:**
1. Check karein `build.bat` run ho raha hai
2. `requirements.txt` install ho: `pip install -r requirements.txt`
3. Clean build karein:
   ```batch
   rmdir /s /q build dist
   build_installer.bat
   ```

### Problem: Build fails with Python error
**Solution:**
- Python 3.8+ use karein
- Virtual environment try karein:
  ```batch
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  build_installer.bat
  ```

---

## 📝 Customization

### Change Version Number
Edit `setup.iss`:
```ini
#define MyAppVersion "1.0.0"  ← Apna version yahan change karein
```

### Change App Name
Edit `setup.iss`:
```ini
#define MyAppName "TG-PY"  ← Apna app name yahan change karein
```

### Add Password Protection
Edit `setup.iss` (uncomment):
```ini
Password=your_password_here
```

### Change Installation Directory
Edit `setup.iss`:
```ini
DefaultDirName={autopf}\{#MyAppName}  ← Change this line
```

---

## 📊 Build Process Details

```
┌─────────────────────────────────────────────────────────────┐
│  build_installer.bat                                        │
│  ↓                                                          │
│  1. Clean old builds (dist/, build/, __pycache__)          │
│  ↓                                                          │
│  2. Install dependencies (pip install -r requirements.txt) │
│  ↓                                                          │
│  3. Run build.bat → dist/TG-PY.exe                         │
│  ↓                                                          │
│  4. Compile setup.iss → dist/TG-PY-Setup-v1.0.0.exe       │
│  ↓                                                          │
│  5. Show summary + open dist folder                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 File Sizes (Expected)

| File | Size |
|------|------|
| TG-PY.exe | ~50-60 MB |
| TG-PY-Setup-v1.0.0.exe | ~50-60 MB (compressed) |

---

## 📞 Support

Agar koi issue ho toh:

1. Check Python version: `python --version`
2. Check Inno Setup: `where ISCC`
3. Run with verbose: `python installer_builder.py`
4. Check logs: `dist\*.log` (if available)

---

## 📄 License

TG-PY - Telegram Automation Application

---

**Happy Building! 🎉**
