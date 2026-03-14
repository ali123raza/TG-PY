"""
Data Service - Replaces API client with direct service manager calls
Provides synchronous interface for PyQt6 UI components
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from core import service_manager
from core.models import Account, Proxy, Campaign, MessageTemplate, Log

logger = logging.getLogger(__name__)

# Global event loop for async operations
_loop: Optional[asyncio.AbstractEventLoop] = None

def get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create event loop"""
    global _loop
    if _loop is None:
        try:
            _loop = asyncio.get_event_loop()
        except RuntimeError:
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
    return _loop

def run_async(coro) -> Any:
    """Run async coroutine synchronously"""
    loop = get_event_loop()
    return loop.run_until_complete(coro)

class DataService(QObject):
    """Data service for UI components - replaces APIClient"""
    
    # Signals for realtime updates
    account_added = pyqtSignal(dict)
    account_updated = pyqtSignal(dict)
    account_deleted = pyqtSignal(dict)
    proxy_added = pyqtSignal(dict)
    proxy_deleted = pyqtSignal(dict)
    campaign_added = pyqtSignal(dict)
    campaign_updated = pyqtSignal(dict)
    campaign_deleted = pyqtSignal(dict)
    log_added = pyqtSignal(dict)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self._connected = False
        self._poll_timer: Optional[QTimer] = None
        self._listeners: List[Callable] = []
        
    async def _on_event(self, event: str, data: dict):
        """Handle events from service manager"""
        # Emit Qt signals for UI updates
        if event == "account_added":
            self.account_added.emit(data or {})
        elif event == "account_updated":
            self.account_updated.emit(data or {})
        elif event == "account_deleted":
            self.account_deleted.emit(data or {})
        elif event == "proxy_added":
            self.proxy_added.emit(data or {})
        elif event == "proxy_deleted":
            self.proxy_deleted.emit(data or {})
        elif event == "campaign_added":
            self.campaign_added.emit(data or {})
        elif event == "campaign_updated":
            self.campaign_updated.emit(data or {})
        elif event == "campaign_deleted":
            self.campaign_deleted.emit(data or {})
        elif event == "log_added":
            self.log_added.emit(data or {})
            
        # Notify any registered listeners
        for listener in self._listeners:
            try:
                listener(event, data)
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    def connect(self):
        """Initialize connection to backend"""
        if not self._connected:
            # Initialize database
            run_async(service_manager.init())
            # Register as listener for realtime updates
            service_manager.add_listener(self._on_event)
            self._connected = True
            logger.info("DataService connected")
    
    def disconnect(self):
        """Disconnect from backend."""
        if self._connected:
            service_manager.remove_listener(self._on_event)
            self._connected = False
    
    def add_listener(self, callback: Callable):
        """Add event listener"""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """Remove event listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    # ========== Accounts ==========
    
    def get_accounts(self) -> List[Dict]:
        """Get all accounts"""
        return run_async(service_manager.get_accounts())
    
    def get_account(self, account_id: int) -> Optional[Dict]:
        """Get single account"""
        return run_async(service_manager.get_account(account_id))
    
    def login_start(self, phone: str, proxy_id: Optional[int] = None) -> Dict:
        """Start login flow"""
        return run_async(service_manager.login_start(phone, proxy_id))
    
    def login_complete(self, phone: str, code: str, phone_code_hash: str,
                      password: Optional[str] = None, proxy_id: Optional[int] = None) -> Dict:
        """Complete login"""
        return run_async(service_manager.login_complete(phone, code, phone_code_hash, password, proxy_id))
    
    def update_account(self, account_id: int, data: Dict) -> Dict:
        """Update account"""
        return run_async(service_manager.update_account(account_id, data))
    
    def delete_account(self, account_id: int) -> bool:
        """Delete account"""
        return run_async(service_manager.delete_account(account_id))
    
    def check_account_health(self, account_id: int) -> Dict:
        """Check account health"""
        return run_async(service_manager.check_account_health(account_id))
    
    def check_all_accounts_health(self) -> Dict:
        """Check all accounts health"""
        return run_async(service_manager.check_all_accounts_health())
    
    def load_sessions_from_folder(self, folder_path: str, proxy_id: Optional[int] = None) -> str:
        """Load sessions from folder - returns job_id"""
        return run_async(service_manager.load_sessions_from_folder(folder_path, proxy_id))
    
    def import_tdata(self, folder_path: str, proxy_id: Optional[int] = None) -> str:
        """Import tdata - returns job_id"""
        return run_async(service_manager.import_tdata(folder_path, proxy_id))
    
    # ========== Proxies ==========
    
    def get_proxies(self) -> List[Dict]:
        """Get all proxies"""
        return run_async(service_manager.get_proxies())
    
    def create_proxy(self, data: Dict) -> Dict:
        """Create proxy"""
        return run_async(service_manager.create_proxy(data))
    
    def delete_proxy(self, proxy_id: int) -> bool:
        """Delete proxy"""
        return run_async(service_manager.delete_proxy(proxy_id))
    
    # ========== Campaigns ==========
    
    def get_campaigns(self) -> List[Dict]:
        """Get all campaigns"""
        return run_async(service_manager.get_campaigns())
    
    def get_campaign(self, campaign_id: int) -> Optional[Dict]:
        """Get single campaign"""
        return run_async(service_manager.get_campaign(campaign_id))
    
    def create_campaign(self, data: Dict) -> Dict:
        """Create campaign"""
        return run_async(service_manager.create_campaign(data))
    
    def update_campaign(self, campaign_id: int, data: Dict) -> Dict:
        """Update campaign"""
        return run_async(service_manager.update_campaign(campaign_id, data))
    
    def delete_campaign(self, campaign_id: int) -> bool:
        """Delete campaign"""
        return run_async(service_manager.delete_campaign(campaign_id))
    
    # ========== Templates ==========
    
    def get_templates(self) -> List[Dict]:
        """Get all templates"""
        return run_async(service_manager.get_templates())
    
    def create_template(self, data: Dict) -> Dict:
        """Create template"""
        return run_async(service_manager.create_template(data))
    
    def delete_template(self, template_id: int) -> bool:
        """Delete template"""
        return run_async(service_manager.delete_template(template_id))
    
    # ========== Stats ==========
    
    def get_stats(self) -> Dict:
        """Get dashboard stats"""
        return run_async(service_manager.get_stats())
    
    # ========== Logs ==========
    
    def get_logs(self, category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get logs"""
        return run_async(service_manager.get_logs(category, limit))
    
    def create_log(self, message: str, category: str = "general", level: str = "info") -> Dict:
        """Create log"""
        return run_async(service_manager.create_log(message, category, level))
    
    # ========== Settings ==========
    
    def get_settings(self) -> Dict:
        """Get settings"""
        return run_async(service_manager.get_settings())
    
    def send_messages(self, data: dict) -> dict:
        """Send messages to targets"""
        # TODO: Implement message sending in service manager
        import uuid
        job_id = str(uuid.uuid4())
        return {"job_id": job_id, "status": "started"}
    
    def save_settings(self, settings: Dict) -> Dict:
        """Save settings"""
        return run_async(service_manager.save_settings(settings))
    
    def update_template(self, template_id: int, data: dict) -> dict:
        """Update template"""
        # TODO: Implement update_template in service manager
        return {"id": template_id, **data}
    
    def health_check(self) -> bool:
        """Check if backend is healthy"""
        try:
            self.get_stats()
            return True
        except:
            return False
    
    # ========== Jobs ==========
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        return run_async(service_manager.get_job_status(job_id))
    
    # ========== Media ==========
    
    def save_media(self, file_path: str) -> str:
        """Save media file"""
        return run_async(service_manager.save_media(file_path))


# Global data service instance
_data_service: Optional[DataService] = None

def get_data_service() -> DataService:
    """Get global data service instance"""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
