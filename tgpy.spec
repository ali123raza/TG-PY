# -*- mode: python ; coding: utf-8 -*-
# TG-PY PyInstaller Spec
# Build: pyinstaller tgpy.spec --clean --noconfirm

import sys, os
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)   # folder containing this .spec file = TG-PY/

# ── Locate psycopg2 binaries ──────────────────────────────────────────────────
import psycopg2
PSYCO_DIR = Path(psycopg2.__file__).parent

# ── Locate SSL cert ───────────────────────────────────────────────────────────
try:
    import certifi
    CACERT = certifi.where()
except ImportError:
    import ssl
    CACERT = ssl.get_default_verify_paths().cafile or ""

# ── Collect datas ─────────────────────────────────────────────────────────────
datas = [
    # License system
    (str(ROOT / 'license'),            'license'),
    # Core backend
    (str(ROOT / 'core'),               'core'),
    (str(ROOT / 'services'),           'services'),
    (str(ROOT / 'routers'),            'routers'),
    # UI modules
    (str(ROOT / 'data_service.py'),    '.'),
    (str(ROOT / 'contacts_page.py'),   '.'),
    (str(ROOT / 'templates_page.py'),  '.'),
    (str(ROOT / 'campaign_dialog.py'), '.'),
    (str(ROOT / 'login_dialog.py'),    '.'),
    (str(ROOT / 'toast.py'),           '.'),
    # SSL cert for Supabase
    (CACERT,                           'certifi'),
]

# ── Collect binaries ──────────────────────────────────────────────────────────
import glob
binaries = []
for pattern in ['*.pyd', '*.dll']:
    for f in glob.glob(str(PSYCO_DIR / pattern)):
        binaries.append((f, 'psycopg2'))

a = Analysis(
    [str(ROOT / 'main.py')],   # single entry point
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # SQLAlchemy
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.dialects.sqlite',
        'aiosqlite',
        # Pyrogram
        'pyrogram', 'pyrogram.raw', 'pyrogram.raw.all',
        # psycopg2
        'psycopg2', 'psycopg2._psycopg', 'psycopg2.extensions',
        'psycopg2.extras', 'psycopg2._json', 'psycopg2._range', 'psycopg2.tz',
        # bcrypt / crypto
        'bcrypt', '_bcrypt',
        'cryptography', 'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.backends.openssl',
        # SSL
        'certifi', 'ssl',
        # APScheduler
        'apscheduler', 'apscheduler.schedulers.asyncio',
        # PyQt6
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
        # hashlib
        'hashlib', '_hashlib', '_sha256',
        # core modules (explicit)
        'core.config', 'core.database', 'core.models', 'core.service_manager',
    ],
    hookspath=[],
    runtime_hooks=[str(ROOT / 'pyi_rthook.py')],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TG-PY',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3*.dll'],
    runtime_tmpdir=None,
    console=False,      # no black window
    # icon='assets\\icon.ico',   # uncomment if you have icon
)
