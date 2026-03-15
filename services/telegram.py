"""
Pyrogram Client Manager with Proxy Support
Speed improvements:
  - Connection reuse (don't reconnect if already connected with same proxy)
  - verify_session: safe finally block (check is_connected before stop)
  - get_client: faster proxy equality check

Bug fixes:
  - verify_session finally: was calling stop() even if connect() never succeeded
  - is_connected is a Pyrogram property (not method) — no () needed
"""
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

from core.config import API_ID, API_HASH, SESSIONS_DIR


class ClientManager:
    """Manages multiple Pyrogram client instances with proxy support."""

    def __init__(self):
        self._clients: dict[int, Client] = {}
        self._client_proxies: dict[int, dict | None] = {}
        self._pending_logins: dict[str, Client] = {}

    # ── Proxy helper ──────────────────────────────────────────────────────────

    def _make_proxy(self, proxy) -> dict | None:
        if not proxy:
            return None
        if isinstance(proxy, dict):
            p = {
                "scheme":   proxy.get("scheme", "socks5"),
                "hostname": proxy.get("host") or proxy.get("hostname", ""),
                "port":     proxy.get("port", 0),
            }
            if proxy.get("username"):
                p["username"] = proxy["username"]
                p["password"] = proxy.get("password", "")
        else:
            p = {
                "scheme":   proxy.scheme,
                "hostname": proxy.host,
                "port":     proxy.port,
            }
            if proxy.username:
                p["username"] = proxy.username
                p["password"] = proxy.password or ""
        return p

    def _proxy_key(self, proxy_dict: dict | None) -> tuple:
        """Hashable key for proxy dict comparison (faster than dict ==)."""
        if not proxy_dict:
            return ()
        return (
            proxy_dict.get("hostname", ""),
            proxy_dict.get("port", 0),
            proxy_dict.get("scheme", ""),
        )

    # ── Login flow ────────────────────────────────────────────────────────────

    async def start_login(self, phone: str, proxy=None) -> str:
        session_name = phone.replace("+", "").replace(" ", "")
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
            proxy=self._make_proxy(proxy),
            in_memory=False,
        )
        await client.connect()
        sent_code = await client.send_code(phone)
        self._pending_logins[phone] = client
        return sent_code.phone_code_hash

    async def complete_login(self, phone: str, code: str,
                             phone_code_hash: str,
                             password: str | None = None) -> dict:
        client = self._pending_logins.get(phone)
        if not client:
            raise ValueError("No pending login for this phone. Start login first.")
        try:
            signed_in = await client.sign_in(phone, phone_code_hash, code)
        except SessionPasswordNeeded:
            if not password:
                raise ValueError("2FA password required")
            signed_in = await client.check_password(password)

        del self._pending_logins[phone]
        await client.disconnect()

        user = signed_in
        return {
            "id":         user.id,
            "first_name": user.first_name or "",
            "last_name":  user.last_name or "",
            "username":   user.username or "",
            "phone":      user.phone_number or phone,
        }

    # ── Client management ─────────────────────────────────────────────────────

    async def get_client(self, account_id: int, phone: str, proxy=None) -> Client:
        """
        Get or create a connected client.
        Reuses existing connection if proxy hasn't changed — avoids reconnect overhead.
        Pyrogram: is_connected is a PROPERTY (not method).
        """
        proxy_dict = self._make_proxy(proxy)
        new_key    = self._proxy_key(proxy_dict)

        if account_id in self._clients:
            client  = self._clients[account_id]
            old_key = self._proxy_key(self._client_proxies.get(account_id))

            # ── Reuse if connected and proxy unchanged ─────────────────────────
            if client.is_connected and old_key == new_key:
                return client

            # Proxy changed or disconnected — tear down
            if client.is_connected:
                await client.stop()

        session_name = phone.replace("+", "").replace(" ", "")
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
            proxy=proxy_dict,
        )
        await client.start()
        self._clients[account_id]        = client
        self._client_proxies[account_id] = proxy_dict
        return client

    async def disconnect(self, account_id: int):
        client = self._clients.pop(account_id, None)
        self._client_proxies.pop(account_id, None)
        if client and client.is_connected:
            await client.stop()

    async def verify_session(self, phone: str, proxy=None) -> dict:
        """
        Connect, get user info, disconnect.
        FIX: finally block now checks is_connected before stop() to avoid
             'ConnectionError: not connected' when connect() itself failed.
        """
        session_name = phone.replace("+", "").replace(" ", "")
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
            proxy=self._make_proxy(proxy),
        )
        connected = False
        try:
            await client.start()
            connected = True
            me = await client.get_me()
            return {
                "id":         me.id,
                "first_name": me.first_name or "",
                "last_name":  me.last_name or "",
                "username":   me.username or "",
                "phone":      me.phone_number or phone,
            }
        finally:
            # FIX: only stop if we successfully connected — prevents
            # "stop() called on non-started client" error
            if connected and client.is_connected:
                await client.stop()

    async def disconnect_all(self):
        for aid in list(self._clients.keys()):
            await self.disconnect(aid)
        for phone, client in list(self._pending_logins.items()):
            if client.is_connected:
                await client.disconnect()
        self._pending_logins.clear()


client_manager = ClientManager()