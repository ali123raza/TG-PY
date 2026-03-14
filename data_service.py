"""
Data Service - Synchronous facade over ServiceManager for PyQt6 UI components.

Threading model
---------------
asyncio runs in a dedicated daemon thread (_worker_loop).  All calls from the
Qt main thread submit coroutines via asyncio.run_coroutine_threadsafe() and
block only for the duration of the actual DB/network operation.  Background
jobs (send, load-sessions, import-tdata, scrape) continue running on the
worker loop after the submit call returns.
"""
import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Callable, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core import service_manager

logger = logging.getLogger(__name__)

# ── Worker loop ───────────────────────────────────────────────────────────────

_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_thread: threading.Thread | None = None


def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop, _worker_thread
    if _worker_loop is not None and _worker_loop.is_running():
        return _worker_loop
    _worker_loop = asyncio.new_event_loop()
    _worker_thread = threading.Thread(
        target=_run_loop, args=(_worker_loop,), daemon=True, name="asyncio-worker")
    _worker_thread.start()
    while not _worker_loop.is_running():
        threading.Event().wait(0.005)
    return _worker_loop


def run_async(coro: Any, timeout: float = 120) -> Any:
    """Submit coroutine to the worker loop and block until done."""
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise TimeoutError(f"Async operation timed out after {timeout}s")


# ── DataService ───────────────────────────────────────────────────────────────

class DataService(QObject):
    """Synchronous wrapper around ServiceManager for PyQt6 UI."""

    # Realtime update signals
    account_added    = pyqtSignal(dict)
    account_updated  = pyqtSignal(dict)
    account_deleted  = pyqtSignal(dict)
    proxy_added      = pyqtSignal(dict)
    proxy_deleted    = pyqtSignal(dict)
    campaign_added   = pyqtSignal(dict)
    campaign_updated = pyqtSignal(dict)
    campaign_deleted = pyqtSignal(dict)
    log_added        = pyqtSignal(dict)
    stats_updated    = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._listeners: List[Callable] = []

    async def _on_event(self, event: str, data: dict) -> None:
        payload = data or {}
        mapping = {
            "account_added":    self.account_added,
            "account_updated":  self.account_updated,
            "account_deleted":  self.account_deleted,
            "proxy_added":      self.proxy_added,
            "proxy_deleted":    self.proxy_deleted,
            "campaign_added":   self.campaign_added,
            "campaign_updated": self.campaign_updated,
            "campaign_deleted": self.campaign_deleted,
            "log_added":        self.log_added,
        }
        sig = mapping.get(event)
        if sig:
            sig.emit(payload)
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.error("DataService listener error: %s", e)

    def connect(self) -> None:
        if self._connected:
            return
        _get_loop()
        run_async(service_manager.init())
        service_manager.add_listener(self._on_event)
        self._connected = True
        logger.info("DataService connected")

    def disconnect(self) -> None:
        if self._connected:
            service_manager.remove_listener(self._on_event)
            self._connected = False

    def add_listener(self, cb: Callable) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: Callable) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)

    # ── Accounts ──────────────────────────────────────────────────────────────

    def get_accounts(self) -> list:
        return run_async(service_manager.get_accounts())

    def get_account(self, account_id: int) -> Optional[dict]:
        return run_async(service_manager.get_account(account_id))

    def login_start(self, phone: str, proxy_id: Optional[int] = None) -> dict:
        return run_async(service_manager.login_start(phone, proxy_id))

    def login_complete(self, phone: str, code: str, phone_code_hash: str,
                       password: Optional[str] = None,
                       proxy_id: Optional[int] = None) -> dict:
        return run_async(service_manager.login_complete(
            phone, code, phone_code_hash, password, proxy_id))

    def update_account(self, account_id: int, data: dict) -> dict:
        return run_async(service_manager.update_account(account_id, data))

    def delete_account(self, account_id: int) -> bool:
        return run_async(service_manager.delete_account(account_id))

    def check_account_health(self, account_id: int) -> dict:
        return run_async(service_manager.check_account_health(account_id))

    def check_all_accounts_health(self) -> dict:
        return run_async(service_manager.check_all_accounts_health())

    def load_sessions_from_folder(self, folder_path: str,
                                  proxy_id: Optional[int] = None) -> str:
        return run_async(service_manager.load_sessions_from_folder(folder_path, proxy_id))

    def import_tdata(self, folder_path: str, proxy_id: Optional[int] = None) -> str:
        return run_async(service_manager.import_tdata(folder_path, proxy_id))

    # ── Proxies ───────────────────────────────────────────────────────────────

    def get_proxies(self) -> list:
        return run_async(service_manager.get_proxies())

    def create_proxy(self, data: dict) -> dict:
        return run_async(service_manager.create_proxy(data))

    def bulk_create_proxies(self, text: str) -> dict:
        return run_async(service_manager.bulk_create_proxies(text))

    def test_proxy(self, proxy_id: int) -> dict:
        return run_async(service_manager.test_proxy(proxy_id), timeout=15)

    def delete_proxy(self, proxy_id: int) -> bool:
        return run_async(service_manager.delete_proxy(proxy_id))

    # ── Messaging ─────────────────────────────────────────────────────────────

    def send_messages(self, data: dict) -> dict:
        """Start bulk send. Returns {"job_id":..., "status":"starting"} immediately."""
        return run_async(service_manager.send_messages(data))

    def cancel_job(self, job_id: str) -> bool:
        return run_async(service_manager.cancel_job(job_id))

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def get_campaigns(self) -> list:
        return run_async(service_manager.get_campaigns())

    def get_campaign(self, campaign_id: int) -> Optional[dict]:
        return run_async(service_manager.get_campaign(campaign_id))

    def create_campaign(self, data: dict) -> dict:
        return run_async(service_manager.create_campaign(data))

    def update_campaign(self, campaign_id: int, data: dict) -> dict:
        return run_async(service_manager.update_campaign(campaign_id, data))

    def run_campaign(self, campaign_id: int) -> dict:
        """Run campaign and return {"job_id":..., "status":"starting"}."""
        return run_async(service_manager.run_campaign(campaign_id))

    def delete_campaign(self, campaign_id: int) -> bool:
        return run_async(service_manager.delete_campaign(campaign_id))

    # ── Templates ─────────────────────────────────────────────────────────────

    def get_templates(self) -> list:
        return run_async(service_manager.get_templates())

    def create_template(self, data: dict) -> dict:
        return run_async(service_manager.create_template(data))

    def update_template(self, template_id: int, data: dict) -> dict:
        return run_async(service_manager.update_template(template_id, data))

    def delete_template(self, template_id: int) -> bool:
        return run_async(service_manager.delete_template(template_id))

    # ── Scraper ───────────────────────────────────────────────────────────────

    def scrape_members(self, account_id: int, group: str,
                       limit: int = 0, filter_type: str = "all") -> str:
        return run_async(service_manager.scrape_members(account_id, group, limit, filter_type))

    def join_groups(self, account_ids: list, groups: list,
                    delay_min: int = 10, delay_max: int = 30) -> str:
        return run_async(service_manager.join_groups(account_ids, groups, delay_min, delay_max))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return run_async(service_manager.get_stats())

    # ── Logs ──────────────────────────────────────────────────────────────────

    def get_logs(self, category: Optional[str] = None, limit: int = 100) -> list:
        return run_async(service_manager.get_logs(category, limit))

    def clear_logs(self, category: Optional[str] = None) -> dict:
        return run_async(service_manager.clear_logs(category))

    def create_log(self, message: str, category: str = "general",
                   level: str = "info") -> dict:
        return run_async(service_manager.create_log(message, category, level))

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        return run_async(service_manager.get_settings())

    def save_settings(self, settings: dict) -> dict:
        return run_async(service_manager.save_settings(settings))

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def get_job_status(self, job_id: str) -> Optional[dict]:
        return run_async(service_manager.get_job_status(job_id))

    # ── Media ─────────────────────────────────────────────────────────────────

    def save_media(self, file_path: str) -> str:
        return run_async(service_manager.save_media(file_path))

    # ── Health ────────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            self.get_stats()
            return True
        except Exception:
            return False


# ── Singleton ─────────────────────────────────────────────────────────────────

_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
