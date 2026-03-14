"""Async API client for TG-PY Python Frontend"""
import requests
import json
from typing import Optional, Dict, Any, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread

API_BASE_URL = "http://127.0.0.1:8767/api"
MEDIA_BASE_URL = "http://127.0.0.1:8767/media"


class APIError(Exception):
    """API error with message and status code"""
    def __init__(self, message: str, status_code: int = 0):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class APIClient(QObject):
    """Synchronous API client with signal-based error handling"""
    
    # Signals for UI notifications
    error_occurred = pyqtSignal(str)
    success_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.timeout = 120  # Increased from 30s to 120s for login operations
    
    def _handle_error(self, error: Exception, endpoint: str) -> None:
        """Handle API errors and emit signal"""
        message = str(error)
        if isinstance(error, requests.exceptions.ConnectionError):
            message = "Backend not reachable. Is the backend running?"
        elif isinstance(error, requests.exceptions.Timeout):
            message = f"Request to {endpoint} timed out"
        elif isinstance(error, requests.exceptions.HTTPError):
            try:
                data = error.response.json()
                message = data.get("detail", data.get("message", str(error)))
            except:
                message = error.response.text or str(error)
        
        self.error_occurred.emit(message)
        raise APIError(message)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            self._handle_error(e, endpoint)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, silent: bool = False) -> Dict[str, Any]:
        """Make POST request"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            json_data = json.dumps(data) if data else None
            response = self.session.post(url, data=json_data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json() if response.content else {}
            if not silent:
                self.success_occurred.emit("Operation completed successfully")
            return result
        except Exception as e:
            self._handle_error(e, endpoint)
    
    def patch(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make PATCH request"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            json_data = json.dumps(data)
            response = self.session.patch(url, data=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            self._handle_error(e, endpoint)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            response = self.session.delete(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            self._handle_error(e, endpoint)
    
    def upload_file(self, endpoint: str, file_path: str, field_name: str = "file") -> Dict[str, Any]:
        """Upload a file"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            with open(file_path, 'rb') as f:
                files = {field_name: f}
                response = self.session.post(url, files=files, timeout=60)
                response.raise_for_status()
                return response.json() if response.content else {}
        except Exception as e:
            self._handle_error(e, endpoint)
    
    def health_check(self) -> bool:
        """Check if backend is running"""
        try:
            response = self.session.get(f"{API_BASE_URL}/health", timeout=2)
            return response.status_code == 200
        except:
            return False


# Create singleton instance
api_client = APIClient()


def get_api_client() -> APIClient:
    """Get the singleton API client instance"""
    return api_client


class JobPoller(QThread):
    """Background thread for polling job status"""
    
    status_updated = pyqtSignal(dict)  # Emits job status dict
    completed = pyqtSignal(dict)  # Emits final job status
    error = pyqtSignal(str)
    
    def __init__(self, job_id: str, endpoint: str, interval_ms: int = 2000):
        super().__init__()
        self.job_id = job_id
        self.endpoint = endpoint  # e.g., /messaging/jobs/{job_id}
        self.interval_ms = interval_ms
        self._running = True
        self.client = APIClient()
    
    def stop(self):
        """Stop polling"""
        self._running = False
        self.wait(1000)
    
    def run(self):
        """Poll job status until completion"""
        import time
        
        while self._running:
            try:
                response = self.client.session.get(
                    f"{API_BASE_URL}{self.endpoint}",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                self.status_updated.emit(data)
                
                # Check if job is complete
                status = data.get("status", "")
                if status in ("completed", "failed", "cancelled"):
                    self.completed.emit(data)
                    break
                
                # Wait before next poll
                time.sleep(self.interval_ms / 1000)
                
            except Exception as e:
                self.error.emit(str(e))
                time.sleep(self.interval_ms / 1000)


# API Endpoint helpers
class Endpoints:
    """API endpoint paths"""
    
    # Health
    HEALTH = "/health"
    
    # Accounts
    ACCOUNTS = "/accounts/"
    ACCOUNT = "/accounts/{id}"
    LOGIN_START = "/accounts/login/start"
    LOGIN_COMPLETE = "/accounts/login/complete"
    LOAD_SESSIONS = "/accounts/load-sessions"
    LOAD_SESSIONS_STATUS = "/accounts/load-sessions/status/{job_id}"
    IMPORT_TDATA = "/accounts/import-tdata"
    IMPORT_TDATA_STATUS = "/accounts/import-tdata/status/{job_id}"
    ACCOUNT_HEALTH = "/accounts/{id}/health"
    HEALTH_ALL = "/accounts/health/all"
    
    # Proxies
    PROXIES = "/proxies/"
    PROXY = "/proxies/{id}"
    PROXY_TEST = "/proxies/{id}/test"
    PROXIES_BULK = "/proxies/bulk"
    
    # Messaging
    MESSAGING_SEND = "/messaging/send"
    MESSAGING_JOBS = "/messaging/jobs"
    MESSAGING_JOB = "/messaging/jobs/{job_id}"
    MESSAGING_LOGS = "/messaging/logs"
    
    # Campaigns
    CAMPAIGNS = "/campaigns/"
    CAMPAIGN = "/campaigns/{id}"
    CAMPAIGN_RUN = "/campaigns/{id}/run"
    CAMPAIGN_PAUSE = "/campaigns/{id}/pause"
    CAMPAIGN_SCHEDULE = "/campaigns/{id}/schedule"
    
    # Scraper
    SCRAPER_SCRAPE = "/scraper/scrape"
    SCRAPER_SCRAPE_JOB = "/scraper/scrape/{job_id}"
    SCRAPER_JOIN = "/scraper/join"
    SCRAPER_JOIN_JOB = "/scraper/join/{job_id}"
    
    # Templates
    TEMPLATES = "/templates/"
    TEMPLATE = "/templates/{id}"
    
    # Logs
    LOGS = "/logs/"
    LOGS_CLEAR = "/logs/clear"
    
    # Settings
    SETTINGS = "/settings/"
    
    # Stats
    STATS = "/stats/"
    
    # Media
    MEDIA_UPLOAD = "/media/upload"
