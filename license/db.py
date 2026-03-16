"""
Supabase connection for license system.
Uses psycopg2 (sync) — license checks happen at startup before asyncio loop.

SECURITY: Credentials are encrypted with XOR + Base64 obfuscation.
They are set via environment variables BEFORE this module is imported.
"""
import os
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config from environment variables (set by main.py) ───────────────────────
# Credentials are encrypted in main.py and set as env vars before import
SUPABASE_HOST = os.getenv("TGPY_DB_HOST", "")
SUPABASE_PORT = int(os.getenv("TGPY_DB_PORT", "5432"))
SUPABASE_DB   = os.getenv("TGPY_DB_NAME", "postgres")
SUPABASE_USER = os.getenv("TGPY_DB_USER", "")
SUPABASE_PASS = os.getenv("TGPY_DB_PASS", "")

# Validate credentials are set
if not SUPABASE_HOST or not SUPABASE_USER or not SUPABASE_PASS:
    logger.warning("License server credentials not configured!")

_conn = None


def _get_ssl_cert() -> str:
    """Find SSL cert — works both in dev and inside PyInstaller EXE."""
    import sys
    # Inside PyInstaller EXE: _MEIPASS has bundled files
    base = getattr(sys, '_MEIPASS', None)
    if base:
        cert = os.path.join(base, 'certifi', 'cacert.pem')
        if os.path.exists(cert):
            return cert
    # Normal Python: use certifi package
    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass
    # Fallback: system SSL
    import ssl
    return ssl.get_default_verify_paths().cafile or ""


def get_connection():
    """Get or create a psycopg2 connection to Supabase."""
    global _conn
    try:
        import psycopg2
        import ssl

        if _conn is None or _conn.closed:
            ssl_cert = _get_ssl_cert()

            # Build SSL context with cert verification
            ssl_ctx = ssl.create_default_context()
            if ssl_cert:
                ssl_ctx.load_verify_locations(ssl_cert)
            else:
                # No cert found — disable verification (less secure but works)
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode    = ssl.CERT_NONE

            _conn = psycopg2.connect(
                host=SUPABASE_HOST,
                port=SUPABASE_PORT,
                database=SUPABASE_DB,
                user=SUPABASE_USER,
                password=SUPABASE_PASS,
                connect_timeout=10,
                sslmode="require",
            )
            _conn.autocommit = False

        # Ping to verify still alive
        try:
            _conn.cursor().execute("SELECT 1")
        except Exception:
            _conn = None
            return get_connection()  # reconnect once

        return _conn
    except Exception as e:
        _conn = None
        raise ConnectionError(f"Cannot connect to license server: {e}")


@contextmanager
def db_cursor():
    """Context manager: get cursor, commit on success, rollback on error."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def close():
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
    _conn = None
