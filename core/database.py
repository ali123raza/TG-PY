from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 60, "check_same_thread": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from core.models import (Account, Proxy, Campaign, MessageTemplate,
                              TemplateVariant, TemplateCategory,
                              Peer, Contact, FailedMessage, Log)
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # SQLite performance
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=60000"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))

        # ── Migrations for existing installations ────────────────────────────
        migrations = [
            # message_templates upgrades
            ("message_templates", "media_path",      "VARCHAR(500) DEFAULT ''"),
            ("message_templates", "media_type",      "VARCHAR(20)  DEFAULT ''"),
            ("message_templates", "category_id",     "INTEGER      REFERENCES template_categories(id)"),
            ("message_templates", "use_variants",    "BOOLEAN      DEFAULT 0"),
            ("message_templates", "variables_used",  "TEXT         DEFAULT '[]'"),
            # campaigns upgrades
            ("campaigns",         "media_path",      "VARCHAR(500) DEFAULT ''"),
            ("campaigns",         "media_type",      "VARCHAR(20)  DEFAULT ''"),
            ("campaigns",         "peer_ids",        "TEXT         DEFAULT '[]'"),
            ("campaigns",         "rotate_proxies",  "BOOLEAN      DEFAULT 0"),
        ]
        for table, col, typ in migrations:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
            except Exception:
                pass   # column already exists — fine


async def get_db():
    async with async_session() as session:
        yield session
