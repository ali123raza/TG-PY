# 🚀 TG-PY Fresh Build Summary

## ✅ Changes Made

### 1. License System (REQUIRED)
- ✅ License check **enabled** (mandatory for user)
- ✅ Internet connection required for verification
- ✅ Supabase server connection
- ✅ 24-hour offline cache (grace period)

### 2. Configuration File
- ✅ `license_config.env` created
- ✅ User can edit Supabase credentials
- ✅ Environment variable support added
- ✅ Better error messages for connection issues

### 3. Files Updated
```
app.py                  ← License config loader added
license/checker.py      ← Better error handling
license_config.env      ← NEW: Config file for license server
fresh_tgpy.spec         ← Updated to include license folder
fresh_setup.iss         ← Updated installer script
build_fresh.bat         ← Updated build script
```

### 4. Fresh Build Structure
```
fresh_build/
├── TG-PY.exe                      ← Main app (with license)
├── TG-PY-Fresh-Setup-v1.0.0.exe   ← Installer
├── license_config.env             ← License server config
├── README_LICENSE.md              ← User instructions
├── data/                          ← Empty (fresh DB on first run)
├── sessions/                      ← Empty
├── media/                         ← Empty
├── tgdata/                        ← Empty
└── logs/                          ← Empty
```

---

## 📋 User Instructions

### Requirements:
1. ✅ **Internet Connection** (required for license verification)
2. ✅ **Firewall/Antivirus** - Port 5432 open for Supabase
3. ✅ **License Credentials** (username + password from admin)

### Installation:
1. Run `TG-PY-Fresh-Setup-v1.0.0.exe`
2. Install to default location
3. Launch TG-PY
4. Enter username + password
5. Activate (internet required)

### Troubleshooting:
- **Error: "Cannot connect to license server"**
  - Check internet connection
  - Disable firewall/antivirus temporarily
  - Verify port 5432 is open
  - Edit `license_config.env` if using custom server

---

## 🔧 Admin Notes

### License Server (Supabase)
```
Host: aws-1-ap-northeast-1.pooler.supabase.com
Port: 5432
Database: postgres
User: postgres.ftsnclmgiqgmnjvouvig
```

### Change License Server
Edit `license_config.env`:
```env
TGPY_DB_HOST=your-server.com
TGPY_DB_PORT=5432
TGPY_DB_USER=your-username
TGPY_DB_PASS=your-password
```

---

## 📦 Distribution Files

**Send to users:**
- `fresh_build/TG-PY-Fresh-Setup-v1.0.0.exe` (56.7 MB)

**Keep for yourself:**
- `dist/TG-PY-Setup-v1.0.0.exe` (old installer with license)
- `dist/TG-PY-Admin.exe` (admin panel - separate)

---

## ⚠️ Important Notes

1. **License is MANDATORY** - User cannot bypass
2. **Internet Required** - First launch needs internet
3. **24h Cache** - Works offline for 24 hours after successful activation
4. **Hardware Locked** - License tied to user's device (hardware ID)

---

**Build Status:** In Progress ⏳
