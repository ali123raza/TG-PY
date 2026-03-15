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
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme: Mapped[str] = mapped_column(String(10), default="socks5")
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(100), default="")
    password: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["Account"]] = relationship(back_populates="proxy")


# ── Contacts / Peers ──────────────────────────────────────────────────────────

class Peer(Base):
    """A named group of contacts (like an audience list)."""
    __tablename__ = "peers"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(20), default="#58A6FF")  # hex color for UI
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="peer", cascade="all, delete-orphan")


class Contact(Base):
    """A single contact inside a peer."""
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    peer_id: Mapped[int] = mapped_column(ForeignKey("peers.id"))
    value: Mapped[str] = mapped_column(String(255))   # +phone / @username / user_id
    label: Mapped[str] = mapped_column(String(200), default="")   # optional name
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending / sent / failed / invalid / duplicate
    resolved_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Telegram user_id after resolution — cached so we don't re-import each time
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    peer: Mapped["Peer"] = relationship(back_populates="contacts")


# ── Templates (upgraded) ──────────────────────────────────────────────────────

class TemplateCategory(Base):
    """Tag/category for organizing templates."""
    __tablename__ = "template_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="#3FB950")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    templates: Mapped[list["MessageTemplate"]] = relationship(back_populates="category")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("template_categories.id"), nullable=True)

    # Primary text (kept for backward compat)
    text: Mapped[str] = mapped_column(Text)

    # Media
    media_path: Mapped[str] = mapped_column(String(500), default="")
    media_type: Mapped[str] = mapped_column(String(20), default="")

    # Variables used: JSON list e.g. ["name","username","phone","custom_1"]
    variables_used: Mapped[str] = mapped_column(Text, default="[]")

    # Anti-spam: if True, random variant is picked per send
    use_variants: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["TemplateCategory | None"] = relationship(back_populates="templates")
    variants: Mapped[list["TemplateVariant"]] = relationship(
        back_populates="template", cascade="all, delete-orphan",
        order_by="TemplateVariant.order")


class TemplateVariant(Base):
    """
    One of multiple text variants for a template.
    When use_variants=True, a random variant is picked for each message.
    This helps avoid Telegram spam detection.
    """
    __tablename__ = "template_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("message_templates.id"))
    text: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    template: Mapped["MessageTemplate"] = relationship(back_populates="variants")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    account_ids: Mapped[str] = mapped_column(Text, default="")     # JSON list
    targets: Mapped[str] = mapped_column(Text, default="")          # JSON list (custom)
    peer_ids: Mapped[str] = mapped_column(Text, default="[]")       # NEW: JSON list of peer IDs
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("message_templates.id"), nullable=True)
    message_text: Mapped[str] = mapped_column(Text, default="")
    media_path: Mapped[str] = mapped_column(String(500), default="")
    media_type: Mapped[str] = mapped_column(String(20), default="")
    delay_min: Mapped[int] = mapped_column(Integer, default=30)
    delay_max: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    schedule_cron: Mapped[str] = mapped_column(String(100), default="")
    rotate_accounts: Mapped[bool] = mapped_column(Boolean, default=True)
    rotate_proxies: Mapped[bool] = mapped_column(Boolean, default=False)
    max_per_account: Mapped[int] = mapped_column(Integer, default=0)
    auto_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    template: Mapped["MessageTemplate | None"] = relationship()


class MessageTemplate_Legacy:
    """Placeholder — MessageTemplate is defined above."""
    pass


class FailedMessage(Base):
    __tablename__ = "failed_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True)
    target: Mapped[str] = mapped_column(String(255))
    message_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="failed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(10), default="info")
    category: Mapped[str] = mapped_column(String(50), default="general")
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
