from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

from core.config import API_ID, API_HASH, SESSIONS_DIR


class ClientManager:
    """Manages multiple Pyrogram client instances with proxy support."""

    def __init__(self):
        self._clients: dict[int, Client] = {}  # account_id -> Client
        self._client_proxies: dict[int, dict | None] = {}  # account_id -> proxy dict (track current proxy)
        self._pending_logins: dict[str, Client] = {}  # phone -> Client (during OTP flow)

    def _make_proxy(self, proxy) -> dict | None:
        """Convert a Proxy model or dict to Pyrogram proxy format."""
        if not proxy:
            return None
        # Support both ORM objects and plain dicts
        if isinstance(proxy, dict):
            p = {
                "scheme": proxy.get("scheme", "socks5"),
                "hostname": proxy.get("host") or proxy.get("hostname", ""),
                "port": proxy.get("port", 0),
            }
            if proxy.get("username"):
                p["username"] = proxy["username"]
                p["password"] = proxy.get("password", "")
        else:
            p = {
                "scheme": proxy.scheme,
                "hostname": proxy.host,
                "port": proxy.port,
            }
            if proxy.username:
                p["username"] = proxy.username
                p["password"] = proxy.password
        return p

    async def start_login(self, phone: str, proxy=None) -> str:
        """Start login flow. Returns phone_code_hash via sent_code."""
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

    async def complete_login(self, phone: str, code: str, phone_code_hash: str, password: str | None = None) -> dict:
        """Complete OTP login. Returns user info dict."""
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
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
            "phone": user.phone_number or phone,
        }

    async def get_client(self, account_id: int, phone: str, proxy=None) -> Client:
        """Get or create a connected client for an account.

        If proxy changed since last connect, reconnects with new proxy.
        """
        proxy_dict = self._make_proxy(proxy)

        if account_id in self._clients:
            client = self._clients[account_id]
            old_proxy = self._client_proxies.get(account_id)

            # If proxy hasn't changed and client is connected, reuse
            if client.is_connected and proxy_dict == old_proxy:
                return client

            # Proxy changed or disconnected — stop old client
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
        self._clients[account_id] = client
        self._client_proxies[account_id] = proxy_dict
        return client

    async def disconnect(self, account_id: int):
        client = self._clients.pop(account_id, None)
        self._client_proxies.pop(account_id, None)
        if client and client.is_connected:
            await client.stop()

    async def verify_session(self, phone: str, proxy=None) -> dict:
        """Connect using existing session file, get user info, then disconnect."""
        session_name = phone.replace("+", "").replace(" ", "")
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
            proxy=self._make_proxy(proxy),
        )
        try:
            await client.start()
            me = await client.get_me()
            return {
                "id": me.id,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone_number or phone,
            }
        finally:
            if client.is_connected:
                await client.stop()

    async def disconnect_all(self):
        for aid in list(self._clients.keys()):
            await self.disconnect(aid)
        for phone, client in list(self._pending_logins.items()):
            if client.is_connected:
                await client.disconnect()
        self._pending_logins.clear()


client_manager = ClientManager()
