from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    username: Mapped[str] = mapped_column(String(100), default="")
    session_file: Mapped[str] = mapped_column(String(255), default="")
    proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxies.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, banned, restricted, disconnected
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme: Mapped[str] = mapped_column(String(10), default="socks5")  # socks5, socks4, http
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(100), default="")
    password: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["Account"]] = relationship(back_populates="proxy")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    account_ids: Mapped[str] = mapped_column(Text, default="")  # JSON list
    targets: Mapped[str] = mapped_column(Text, default="")  # JSON list of usernames/phones
    template_id: Mapped[int | None] = mapped_column(ForeignKey("message_templates.id"), nullable=True)
    message_text: Mapped[str] = mapped_column(Text, default="")
    media_path: Mapped[str] = mapped_column(String(500), default="")
    media_type: Mapped[str] = mapped_column(String(20), default="")  # photo, video, audio, document
    delay_min: Mapped[int] = mapped_column(Integer, default=30)
    delay_max: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, running, paused, completed
    schedule_cron: Mapped[str] = mapped_column(String(100), default="")
    rotate_accounts: Mapped[bool] = mapped_column(Boolean, default=True)
    rotate_proxies: Mapped[bool] = mapped_column(Boolean, default=True)
    max_per_account: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    auto_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    template: Mapped["MessageTemplate | None"] = relationship()


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    media_path: Mapped[str] = mapped_column(String(500), default="")
    media_type: Mapped[str] = mapped_column(String(20), default="")  # photo, video, audio, document
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FailedMessage(Base):
    __tablename__ = "failed_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    target: Mapped[str] = mapped_column(String(255))
    message_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="failed")  # failed, retrying, success
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(10), default="info")  # info, warn, error
    category: Mapped[str] = mapped_column(String(50), default="general")  # auth, message, campaign, scrape
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
