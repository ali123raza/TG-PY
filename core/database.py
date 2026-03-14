from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL

# SQLite specific settings to avoid database locked issues
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 60, "check_same_thread": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from core.models import Account, Proxy, Campaign, MessageTemplate, FailedMessage, Log
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=60000"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        # Migrate: add media columns to existing tables
        for table in ["message_templates", "campaigns"]:
            for col, typ in [("media_path", "VARCHAR(500)"), ("media_type", "VARCHAR(20)")]:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ} DEFAULT ''"))
                except Exception:
                    pass


async def get_db():
    async with async_session() as session:
        yield session
