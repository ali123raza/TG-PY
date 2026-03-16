"""
License checker — validates credentials + hardware against Supabase.

Check flow:
  1. Offline cache check (valid for 24h) — no internet needed for daily use
  2. Online Supabase check — runs at startup and every 6h
  3. Results written back to encrypted local cache
"""
import json
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Local cache file (encrypted JSON) ───────────────────────────────────────
_CACHE_FILE = Path(os.getenv("APPDATA", Path.home())) / "TgPy" / ".lic"
_CACHE_TTL  = 24 * 3600   # 24 hours offline grace


def _cache_key(username: str) -> bytes:
    """Derive encryption key from username (deterministic)."""
    return hashlib.sha256(f"tgpy_lic_{username}_v1".encode()).digest()


def _encrypt(data: str, key: bytes) -> bytes:
    from cryptography.fernet import Fernet
    import base64
    fkey = base64.urlsafe_b64encode(key)
    return Fernet(fkey).encrypt(data.encode())


def _decrypt(data: bytes, key: bytes) -> str:
    from cryptography.fernet import Fernet
    import base64
    fkey = base64.urlsafe_b64encode(key)
    return Fernet(fkey).decrypt(data).decode()


def _read_cache(username: str) -> Optional[dict]:
    try:
        if not _CACHE_FILE.exists():
            return None
        raw = _CACHE_FILE.read_bytes()
        key  = _cache_key(username)
        text = _decrypt(raw, key)
        data = json.loads(text)
        # Verify cache is for this user
        if data.get("username") != username:
            return None
        return data
    except Exception:
        return None


def _write_cache(data: dict, username: str):
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        key  = _cache_key(username)
        text = json.dumps(data)
        encrypted = _encrypt(text, key)
        _CACHE_FILE.write_bytes(encrypted)
    except Exception as e:
        logger.warning("Could not write license cache: %s", e)


def _clear_cache():
    try:
        if _CACHE_FILE.exists():
            _CACHE_FILE.unlink()
    except Exception:
        pass


# ── Result object ─────────────────────────────────────────────────────────────

class LicenseResult:
    def __init__(self, ok: bool, message: str = "",
                 username: str = "", plan: str = "",
                 expires_at: Optional[str] = None,
                 days_remaining: Optional[int] = None,
                 from_cache: bool = False):
        self.ok             = ok
        self.message        = message
        self.username       = username
        self.plan           = plan
        self.expires_at     = expires_at
        self.days_remaining = days_remaining
        self.from_cache     = from_cache

    def __repr__(self):
        return (f"LicenseResult(ok={self.ok}, plan={self.plan}, "
                f"days={self.days_remaining}, cache={self.from_cache})")


# ── Main checker ─────────────────────────────────────────────────────────────

def check_license(username: str, password: str,
                  hardware_id: str) -> LicenseResult:
    """
    Full license check:
    1. Try Supabase (online)
    2. On network failure, fall back to 24h cache

    Returns LicenseResult with ok=True if all checks pass.
    """
    # ── Try online check ──────────────────────────────────────────────────────
    try:
        return _online_check(username, password, hardware_id)
    except ConnectionError as e:
        logger.warning("Online check failed: %s — trying cache", e)
        # Show detailed connection error
        error_msg = str(e)
        if "could not connect" in error_msg.lower():
            logger.error("LICENSE ERROR: Cannot reach license server")
            logger.error("  - Check internet connection")
            logger.error("  - Check firewall/antivirus settings")
            logger.error("  - Port 5432 must be open for Supabase")
    except Exception as e:
        logger.error("License check error: %s", e)

    # ── Offline fallback ──────────────────────────────────────────────────────
    cache = _read_cache(username)
    if cache:
        cached_at = cache.get("cached_at", 0)
        if time.time() - cached_at < _CACHE_TTL:
            # Verify hardware_id matches cache
            if cache.get("hardware_id") != hardware_id:
                return LicenseResult(False,
                    "This license is registered to a different device.")
            # Check expiry from cache
            expires_str = cache.get("expires_at")
            if expires_str:
                expires = datetime.fromisoformat(expires_str)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires:
                    _clear_cache()
                    return LicenseResult(False,
                        "Your license has expired. Please renew.")
            hours_left = int((_CACHE_TTL - (time.time() - cached_at)) / 3600)
            return LicenseResult(
                ok=True,
                message=f"Offline mode — {hours_left}h cache remaining",
                username=cache["username"],
                plan=cache.get("plan", ""),
                expires_at=cache.get("expires_at"),
                days_remaining=cache.get("days_remaining"),
                from_cache=True,
            )
        else:
            _clear_cache()
            return LicenseResult(False,
                "Cannot connect to license server.\n"
                "Offline cache expired. Please connect to internet.")

    return LicenseResult(False,
        "Cannot connect to license server.\n"
        "Please check your internet connection.")


def _online_check(username: str, password: str,
                  hardware_id: str) -> LicenseResult:
    """Check license against Supabase — raises ConnectionError on network fail."""
    from license.db import db_cursor
    import bcrypt as _bc, hashlib as _hl

    with db_cursor() as cur:
        # ── 1. Verify user credentials ────────────────────────────────────────
        cur.execute(
            "SELECT id, password_hash, is_active "
            "FROM tgpy_users WHERE username = %s",
            (username,))
        row = cur.fetchone()

        if not row:
            return LicenseResult(False, "Invalid username or password.")

        user_id, pw_hash, is_active = row

        if not is_active:
            return LicenseResult(False, "Your account has been suspended.")

        # Pre-hash with sha256, then verify with bcrypt directly
        import hashlib as _hl, bcrypt as _bc
        pre_hashed = _hl.sha256(password.encode()).hexdigest().encode()
        try:
            pw_match = _bc.checkpw(pre_hashed, pw_hash.encode() if isinstance(pw_hash, str) else pw_hash)
        except Exception:
            pw_match = False
        if not pw_match:
            return LicenseResult(False, "Invalid username or password.")

        # ── 2. Check active license ───────────────────────────────────────────
        cur.execute("""
            SELECT id, plan_name, max_devices, expires_at, is_active
            FROM tgpy_licenses
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """, (str(user_id),))
        lic = cur.fetchone()

        if not lic:
            return LicenseResult(False,
                "No active license found.\n"
                "Please contact support to activate your plan.")

        lic_id, plan_name, max_devices, expires_at, lic_active = lic

        if not lic_active:
            return LicenseResult(False, "Your license has been deactivated.")

        # ── 3. Check expiry ───────────────────────────────────────────────────
        days_remaining = None
        expires_str    = None
        if expires_at:
            expires_str = expires_at.isoformat()
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > expires_at:
                # Mark license as expired
                cur.execute(
                    "UPDATE tgpy_licenses SET is_active=FALSE WHERE id=%s",
                    (str(lic_id),))
                _clear_cache()
                return LicenseResult(False,
                    f"Your {plan_name} license expired on "
                    f"{expires_at.strftime('%Y-%m-%d')}.\n"
                    "Please renew your plan.")
            days_remaining = max(0, (expires_at - now).days)

        # ── 4. Check / register device ────────────────────────────────────────
        cur.execute("""
            SELECT id, is_active FROM tgpy_devices
            WHERE license_id = %s AND hardware_id = %s
        """, (str(lic_id), hardware_id))
        device = cur.fetchone()

        if device:
            # Known device — update last_seen
            dev_id, dev_active = device
            if not dev_active:
                return LicenseResult(False,
                    "This device has been deactivated for your license.")
            cur.execute(
                "UPDATE tgpy_devices SET last_seen=NOW() WHERE id=%s",
                (str(dev_id),))
        else:
            # New device — check slot count
            cur.execute("""
                SELECT COUNT(*) FROM tgpy_devices
                WHERE license_id = %s AND is_active = TRUE
            """, (str(lic_id),))
            active_devices = cur.fetchone()[0]

            if active_devices >= max_devices:
                return LicenseResult(False,
                    f"Device limit reached ({max_devices} device(s) allowed).\n"
                    "Deactivate another device or upgrade your plan.")

            # Register new device
            from license.hardware import get_platform_info
            info = get_platform_info()
            cur.execute("""
                INSERT INTO tgpy_devices
                    (license_id, hardware_id, hostname, platform)
                VALUES (%s, %s, %s, %s)
            """, (str(lic_id), hardware_id,
                  info["hostname"], info["platform"]))

        # ── 5. All checks passed — write cache ───────────────────────────────
        cache_data = {
            "username":      username,
            "plan":          plan_name,
            "expires_at":    expires_str,
            "days_remaining": days_remaining,
            "hardware_id":   hardware_id,
            "cached_at":     time.time(),
        }
        _write_cache(cache_data, username)

        return LicenseResult(
            ok=True,
            message="License verified",
            username=username,
            plan=plan_name,
            expires_at=expires_str,
            days_remaining=days_remaining,
        )


def periodic_check(username: str, hardware_id: str) -> LicenseResult:
    """
    Background check (every 6h after startup).
    Uses cached credentials — no password re-entry needed.
    """
    cache = _read_cache(username)
    if not cache:
        return LicenseResult(False, "Session expired — please restart.")

    # Re-validate with Supabase using cached data
    expires_str = cache.get("expires_at")
    if expires_str:
        expires = datetime.fromisoformat(expires_str)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            _clear_cache()
            return LicenseResult(False, "Your license has expired.")

    if cache.get("hardware_id") != hardware_id:
        return LicenseResult(False, "Hardware mismatch.")

    return LicenseResult(
        ok=True,
        username=username,
        plan=cache.get("plan", ""),
        expires_at=expires_str,
        days_remaining=cache.get("days_remaining"),
        from_cache=True,
    )


def logout():
    """Clear local license cache (force re-activation on next start)."""
    _clear_cache()