"""
Core module initialization
"""
from .config import BASE_DIR, DATA_DIR, SESSIONS_DIR, MEDIA_DIR, TGDATA_DIR, SETTINGS_FILE
from .database import init_db, async_session, engine, Base
from .models import (
    Account, Proxy, Campaign, MessageTemplate, Log, FailedMessage,
    Peer, Contact, TemplateVariant, TemplateCategory, TemplateMedia,
)
from .service_manager import service_manager, ServiceManager

__all__ = [
    "BASE_DIR", "DATA_DIR", "SESSIONS_DIR", "MEDIA_DIR", "TGDATA_DIR", "SETTINGS_FILE",
    "init_db", "async_session", "engine", "Base",
    "Account", "Proxy", "Campaign", "MessageTemplate", "Log", "FailedMessage",
    "Peer", "Contact", "TemplateVariant", "TemplateCategory", "TemplateMedia",
    "service_manager", "ServiceManager",
]