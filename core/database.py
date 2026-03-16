"""
Database setup for TG-PY.

Why NullPool:
  aiosqlite connections are tied to the asyncio event loop of the thread that
  created them. SQLAlchemy's default pool tries to reuse connections across
  requests — when a connection from one loop is reused in another, it crashes:
    "close() can't be called here / _connection_for_bind already in progress"

  NullPool disables reuse: each `async with async_session()` gets a fresh
  connection and closes it on exit. Correct approach for SQLite + WAL mode.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,          # no cross-thread connection reuse
    connect_args={
        "timeout":           60,
        "check_same_thread": False,
    },
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    from core.models import (Account, Proxy, Campaign, MessageTemplate,
                              TemplateVariant, TemplateCategory, TemplateMedia,
                              Peer, Contact, FailedMessage, Log)
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # SQLite performance tuning — applied once at startup
        for pragma in [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=-32000",    # 32 MB page cache
            "PRAGMA temp_store=MEMORY",    # temp tables in RAM
            "PRAGMA mmap_size=268435456",  # 256 MB mmap IO
            "PRAGMA busy_timeout=30000",
        ]:
            await conn.execute(text(pragma))

        # Safe migrations — skip if column already exists
        migrations = [
            ("message_templates", "media_path",     "VARCHAR(500) DEFAULT ''"),
            ("message_templates", "media_type",     "VARCHAR(20)  DEFAULT ''"),
            ("message_templates", "category_id",    "INTEGER"),
            ("message_templates", "use_variants",   "BOOLEAN DEFAULT 0"),
            ("message_templates", "variables_used", "TEXT DEFAULT '[]'"),
            ("campaigns",         "media_path",     "VARCHAR(500) DEFAULT ''"),
            ("campaigns",         "media_type",     "VARCHAR(20)  DEFAULT ''"),
            ("campaigns",         "peer_ids",       "TEXT DEFAULT '[]'"),
            ("campaigns",         "rotate_proxies", "BOOLEAN DEFAULT 0"),
            ("campaigns",         "template_id",    "INTEGER"),
        ]
        for table, col, typ in migrations:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
            except Exception:
                pass


async def get_db():
    async with async_session() as session:
        yield session