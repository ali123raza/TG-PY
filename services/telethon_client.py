"""
Telethon Client Manager with Proxy Support
Handles multiple Telegram accounts with SOCKS5/HTTP proxy support.

FIXES applied:
  - send_code()      → send_code_request()   (correct Telethon API)
  - sign_in() arg order fixed: (phone, code, phone_code_hash=hash)
  - check_password() → sign_in(password=pwd) (Telethon 1.x style)
  - is_connected     → is_connected()        (Telethon is a method, not property)
"""
import asyncio
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged

from core.config import API_ID, API_HASH, TGDATA_DIR, SESSIONS_DIR

logger = logging.getLogger(__name__)


class ClientManager:
    """Manages multiple Telethon client instances with proxy support."""

    def __init__(self):
        self._clients:        dict[int, TelegramClient] = {}
        self._client_proxies: dict[int, dict | None]    = {}
        self._pending_logins: dict[str, TelegramClient] = {}

    # ── Proxy helper ─────────────────────────────────────────────────────────

    def _make_proxy(self, proxy) -> dict | None:
        if not proxy:
            return None
        if isinstance(proxy, dict):
            p = {
                "proxy_type": proxy.get("scheme", "socks5"),
                "addr":       proxy.get("host", ""),
                "port":       proxy.get("port", 0),
            }
            if proxy.get("username"):
                p["username"] = proxy["username"]
                p["password"] = proxy.get("password", "")
        else:
            p = {
                "proxy_type": proxy.scheme,
                "addr":       proxy.host,
                "port":       proxy.port,
            }
            if proxy.username:
                p["username"] = proxy.username
                p["password"] = proxy.password or ""
        return p

    # ── Session path ──────────────────────────────────────────────────────────

    def _get_session_path(self, phone: str) -> str:
        session_name = phone.replace("+", "").replace(" ", "")
        tdata_path   = TGDATA_DIR / session_name / "tdata"
        session_file = SESSIONS_DIR / f"{session_name}.session"
        if tdata_path.exists():
            return str(tdata_path)
        if session_file.exists():
            return str(session_file)
        return str(tdata_path)   # will fail gracefully

    # ── Login flow ────────────────────────────────────────────────────────────

    async def start_login(self, phone: str, proxy=None) -> str:
        """Send OTP code. Returns phone_code_hash."""
        session_path = self._get_session_path(phone)
        client = TelegramClient(
            session_path, API_ID, API_HASH,
            proxy=self._make_proxy(proxy),
            connection=ConnectionTcpAbridged,
        )
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            raise ValueError("Already authorized")

        # FIX: Telethon uses send_code_request(), NOT send_code()
        sent = await client.send_code_request(phone)
        self._pending_logins[phone] = client
        return sent.phone_code_hash

    async def complete_login(self, phone: str, code: str,
                             phone_code_hash: str,
                             password: str | None = None) -> dict:
        """Verify OTP (and optional 2FA). Returns user info dict."""
        client = self._pending_logins.get(phone)
        if not client:
            raise ValueError("No pending login for this phone. Call start_login first.")

        try:
            # FIX: Telethon sign_in(phone, code, phone_code_hash=hash)
            # NOT sign_in(phone, phone_code_hash, code)  ← wrong order
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

        except SessionPasswordNeededError:
            if not password:
                raise ValueError("2FA password required")
            # FIX: Telethon 1.x — sign_in(password=pwd), not check_password(pwd)
            await client.sign_in(password=password)

        me = await client.get_me()
        await client.disconnect()
        del self._pending_logins[phone]

        return {
            "id":         me.id,
            "first_name": me.first_name or "",
            "last_name":  me.last_name  or "",
            "username":   me.username   or "",
            "phone":      me.phone      or phone,
        }

    # ── Client management ─────────────────────────────────────────────────────

    async def get_client(self, account_id: int, phone: str,
                         proxy=None,
                         session_path: str = None) -> TelegramClient:
        """Get or create a connected client for an account."""
        if account_id in self._clients:
            client    = self._clients[account_id]
            old_proxy = self._client_proxies.get(account_id)
            # FIX: Telethon is_connected() is a METHOD, not a property
            if client.is_connected() and proxy == old_proxy:
                return client
            if client.is_connected():
                await client.disconnect()

        if not session_path:
            session_path = self._get_session_path(phone)

        proxy_dict = self._make_proxy(proxy)
        client = TelegramClient(
            session_path, API_ID, API_HASH,
            proxy=proxy_dict,
            connection=ConnectionTcpAbridged,
        )
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            raise AuthKeyUnregisteredError("Session not authorized")

        self._clients[account_id]        = client
        self._client_proxies[account_id] = proxy_dict
        return client

    async def verify_session(self, phone: str, proxy=None) -> dict:
        """Connect, get user info, disconnect. Used for session health checks."""
        session_path = self._get_session_path(phone)
        client = TelegramClient(
            session_path, API_ID, API_HASH,
            proxy=self._make_proxy(proxy),
            connection=ConnectionTcpAbridged,
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise AuthKeyUnregisteredError("Session not authorized")
            me = await client.get_me()
            return {
                "id":         me.id,
                "first_name": me.first_name or "",
                "last_name":  me.last_name  or "",
                "username":   me.username   or "",
                "phone":      me.phone      or phone,
            }
        finally:
            if client.is_connected():
                await client.disconnect()

    async def disconnect(self, account_id: int):
        client = self._clients.pop(account_id, None)
        self._client_proxies.pop(account_id, None)
        if client and client.is_connected():
            await client.disconnect()

    async def disconnect_all(self):
        for aid in list(self._clients.keys()):
            await self.disconnect(aid)
        for phone, client in list(self._pending_logins.items()):
            if client.is_connected():
                await client.disconnect()
        self._pending_logins.clear()


client_manager = ClientManager()