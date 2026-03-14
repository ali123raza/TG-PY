"""
Telethon Client Manager with Proxy Support
Handles multiple Telegram accounts with SOCKS5/HTTP proxy support.
"""
import asyncio
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession, Session
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError

from core.config import API_ID, API_HASH, TGDATA_DIR, SESSIONS_DIR

logger = logging.getLogger(__name__)


class ClientManager:
    """Manages multiple Telethon client instances with proxy support."""
    
    def __init__(self):
        self._clients: dict[int, TelegramClient] = {}  # account_id -> Client
        self._client_proxies: dict[int, dict | None] = {}  # account_id -> proxy dict
        self._pending_logins: dict[str, TelegramClient] = {}  # phone -> Client (during OTP)
    
    def _make_proxy(self, proxy) -> dict | None:
        """Convert a Proxy model or dict to Telethon proxy format."""
        if not proxy:
            return None
        
        if isinstance(proxy, dict):
            p = {
                'proxy_type': proxy.get('scheme', 'socks5'),
                'addr': proxy.get('host', ''),
                'port': proxy.get('port', 0),
            }
            if proxy.get('username'):
                p['username'] = proxy['username']
                p['password'] = proxy.get('password', '')
        else:
            # ORM object
            p = {
                'proxy_type': proxy.scheme,
                'addr': proxy.host,
                'port': proxy.port,
            }
            if proxy.username:
                p['username'] = proxy.username
                p['password'] = proxy.password
        
        return p
    
    def _get_session_path(self, phone: str) -> str:
        """Get session path from tdata folder or session file."""
        session_name = phone.replace('+', '').replace(' ', '')
        
        # Check if tdata folder exists
        tdata_path = TGDATA_DIR / session_name / 'tdata'
        if tdata_path.exists():
            return str(tdata_path)
        
        # Check for .session file
        session_file = SESSIONS_DIR / f'{session_name}.session'
        if session_file.exists():
            return str(session_file)
        
        # Return tdata path anyway (will fail gracefully)
        return str(tdata_path)
    
    async def start_login(self, phone: str, proxy=None) -> str:
        """Start login flow. Returns phone_code_hash via sent_code."""
        session_path = self._get_session_path(phone)
        
        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            proxy=self._make_proxy(proxy),
            connection=ConnectionTcpAbridged,
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            await client.disconnect()
            raise ValueError("Already authorized")
        
        sent_code = await client.send_code(phone)
        self._pending_logins[phone] = client
        
        return sent_code.phone_code_hash
    
    async def complete_login(self, phone: str, code: str, phone_code_hash: str, password: str | None = None) -> dict:
        """Complete OTP login. Returns user info dict."""
        client = self._pending_logins.get(phone)
        if not client:
            raise ValueError("No pending login for this phone. Start login first.")
        
        try:
            await client.sign_in(phone, phone_code_hash, code)
        except SessionPasswordNeededError:
            if not password:
                raise ValueError("2FA password required")
            await client.check_password(password)
        
        await client.disconnect()
        del self._pending_logins[phone]
        
        me = await client.get_me()
        return {
            'id': me.id,
            'first_name': me.first_name or '',
            'last_name': me.last_name or '',
            'username': me.username or '',
            'phone': me.phone or phone,
        }
    
    async def get_client(self, account_id: int, phone: str, proxy=None, session_path: str = None) -> TelegramClient:
        """Get or create a connected client for an account.
        
        If proxy changed since last connect, reconnects with new proxy.
        """
        if account_id in self._clients:
            client = self._clients[account_id]
            old_proxy = self._client_proxies.get(account_id)
            
            # If proxy hasn't changed and client is connected, reuse
            if client.is_connected() and proxy == old_proxy:
                return client
            
            # Proxy changed or disconnected — stop old client
            if client.is_connected():
                await client.disconnect()
        
        # Use provided session path or get from phone
        if not session_path:
            session_path = self._get_session_path(phone)
        
        proxy_dict = self._make_proxy(proxy)
        
        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            proxy=proxy_dict,
            connection=ConnectionTcpAbridged,
        )
        
        await client.connect()
        
        # Verify authorization
        if not await client.is_user_authorized():
            await client.disconnect()
            raise AuthKeyUnregisteredError("Session is not authorized")
        
        self._clients[account_id] = client
        self._client_proxies[account_id] = proxy_dict
        
        return client
    
    async def verify_session(self, phone: str, proxy=None) -> dict:
        """Connect using existing session file/tdata, get user info, then disconnect."""
        session_path = self._get_session_path(phone)
        
        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            proxy=self._make_proxy(proxy),
            connection=ConnectionTcpAbridged,
        )
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                raise AuthKeyUnregisteredError("Session not authorized")
            
            me = await client.get_me()
            await client.disconnect()
            
            return {
                'id': me.id,
                'first_name': me.first_name or '',
                'last_name': me.last_name or '',
                'username': me.username or '',
                'phone': me.phone or phone,
            }
        except Exception as e:
            await client.disconnect()
            raise
    
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
