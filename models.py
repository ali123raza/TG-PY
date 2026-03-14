"""Data models for TG-PY Python Frontend"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Account:
    id: int
    phone: str
    name: str = ""
    username: str = ""
    proxy_id: Optional[int] = None
    is_active: bool = True
    status: str = "active"  # active, banned, restricted, disconnected
    messages_sent: int = 0
    last_checked: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        return cls(
            id=data.get("id", 0),
            phone=data.get("phone", ""),
            name=data.get("name", ""),
            username=data.get("username", ""),
            proxy_id=data.get("proxy_id"),
            is_active=data.get("is_active", True),
            status=data.get("status", "active"),
            messages_sent=data.get("messages_sent", 0),
            last_checked=data.get("last_checked"),
            created_at=data.get("created_at"),
        )


@dataclass
class Proxy:
    id: int
    scheme: str  # socks5, socks4, http
    host: str
    port: int
    username: str = ""
    password: str = ""
    is_active: bool = True
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proxy":
        return cls(
            id=data.get("id", 0),
            scheme=data.get("scheme", "socks5"),
            host=data.get("host", ""),
            port=data.get("port", 0),
            username=data.get("username", ""),
            password=data.get("password", ""),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
        )

    def __str__(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.scheme}://{auth}{self.host}:{self.port}"


@dataclass
class MessageTemplate:
    id: int
    name: str
    text: str = ""
    media_path: str = ""
    media_type: str = ""  # photo, video, audio, document
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageTemplate":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            text=data.get("text", ""),
            media_path=data.get("media_path", ""),
            media_type=data.get("media_type", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class Campaign:
    id: int
    name: str
    account_ids: List[int] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    template_id: Optional[int] = None
    message_text: str = ""
    media_path: str = ""
    media_type: str = ""
    delay_min: int = 30
    delay_max: int = 60
    status: str = "draft"  # draft, running, paused, completed
    schedule_cron: str = ""
    rotate_accounts: bool = True
    rotate_proxies: bool = True
    max_per_account: int = 0
    auto_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        import json
        account_ids = data.get("account_ids", "[]")
        targets = data.get("targets", "[]")
        if isinstance(account_ids, str):
            account_ids = json.loads(account_ids) if account_ids else []
        if isinstance(targets, str):
            targets = json.loads(targets) if targets else []

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            account_ids=account_ids,
            targets=targets,
            template_id=data.get("template_id"),
            message_text=data.get("message_text", ""),
            media_path=data.get("media_path", ""),
            media_type=data.get("media_type", ""),
            delay_min=data.get("delay_min", 30),
            delay_max=data.get("delay_max", 60),
            status=data.get("status", "draft"),
            schedule_cron=data.get("schedule_cron", ""),
            rotate_accounts=data.get("rotate_accounts", True),
            rotate_proxies=data.get("rotate_proxies", True),
            max_per_account=data.get("max_per_account", 0),
            auto_retry=data.get("auto_retry", False),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            created_at=data.get("created_at"),
        )


@dataclass
class Log:
    id: int
    level: str  # info, warn, error
    category: str  # auth, message, campaign, scrape, general
    message: str
    account_id: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Log":
        return cls(
            id=data.get("id", 0),
            level=data.get("level", "info"),
            category=data.get("category", "general"),
            message=data.get("message", ""),
            account_id=data.get("account_id"),
            created_at=data.get("created_at"),
        )


@dataclass
class Stats:
    accounts: Dict[str, Any] = field(default_factory=dict)
    messages: Dict[str, Any] = field(default_factory=dict)
    campaigns: Dict[str, Any] = field(default_factory=dict)
    proxies: int = 0
    templates: int = 0
    scrape_ops: int = 0
    per_account: List[Dict[str, Any]] = field(default_factory=list)
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stats":
        return cls(
            accounts=data.get("accounts", {}),
            messages=data.get("messages", {}),
            campaigns=data.get("campaigns", {}),
            proxies=data.get("proxies", 0),
            templates=data.get("templates", 0),
            scrape_ops=data.get("scrape_ops", 0),
            per_account=data.get("per_account", []),
            recent_logs=data.get("recent_logs", []),
        )

    @property
    def success_rate(self) -> str:
        total = self.messages.get("total", 0)
        sent = self.messages.get("sent", 0)
        if total > 0:
            return f"{(sent / total * 100):.1f}%"
        return "—"


@dataclass
class Job:
    id: str
    status: str  # starting, running, completed, failed, cancelled
    sent: int = 0
    failed: int = 0
    total: int = 0
    message: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(
            id=data.get("id", data.get("job_id", "")),
            status=data.get("status", "unknown"),
            sent=data.get("sent", 0),
            failed=data.get("failed", 0),
            total=data.get("total", 0),
            message=data.get("message", ""),
        )


@dataclass
class ScrapedMember:
    user_id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    phone: str = ""
    status: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrapedMember":
        return cls(
            user_id=data.get("user_id", 0),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            username=data.get("username", ""),
            phone=data.get("phone", ""),
            status=data.get("status", ""),
        )

    def to_csv_row(self) -> str:
        return f'{self.user_id},"{self.first_name}","{self.last_name}",{self.username},{self.phone},{self.status}'


@dataclass
class Settings:
    api_id: int = 0
    api_hash: str = ""
    api_hash_preview: str = ""
    default_delay_min: int = 30
    default_delay_max: int = 60
    max_per_account: int = 50
    flood_wait_cap: int = 120

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        return cls(
            api_id=data.get("api_id", 0),
            api_hash=data.get("api_hash", ""),
            api_hash_preview=data.get("api_hash_preview", ""),
            default_delay_min=data.get("default_delay_min", 30),
            default_delay_max=data.get("default_delay_max", 60),
            max_per_account=data.get("max_per_account", 50),
            flood_wait_cap=data.get("flood_wait_cap", 120),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "api_id": self.api_id,
            "default_delay_min": self.default_delay_min,
            "default_delay_max": self.default_delay_max,
            "max_per_account": self.max_per_account,
            "flood_wait_cap": self.flood_wait_cap,
        }
        if self.api_hash:
            result["api_hash"] = self.api_hash
        return result
