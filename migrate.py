"""
migrate.py — Run once to create missing tables
Usage: python migrate.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('TG_BASE_DIR', str(Path(__file__).parent.parent))

async def run():
    from sqlalchemy import text
    from core.database import engine, Base

    # Import ALL models so Base knows about them
    from core.models import (
        Account, Proxy, Campaign, MessageTemplate,
        TemplateVariant, TemplateCategory, TemplateMedia,
        Peer, Contact,
        FailedMessage, Log,
    )

    async with engine.begin() as conn:
        # Create any missing tables
        await conn.run_sync(Base.metadata.create_all)
        print("✓  Tables created / verified")

        # WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=60000"))

        # Add missing columns to existing tables (safe — skips if already exist)
        migrations = [
            ("message_templates", "category_id",    "INTEGER"),
            ("message_templates", "use_variants",   "BOOLEAN DEFAULT 0"),
            ("message_templates", "variables_used", "TEXT DEFAULT '[]'"),
            ("campaigns",         "peer_ids",        "TEXT DEFAULT '[]'"),
            ("campaigns",         "rotate_proxies",  "BOOLEAN DEFAULT 0"),
        ]
        for table, col, typ in migrations:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
                print(f"✓  Added column {table}.{col}")
            except Exception:
                print(f"   Skipped {table}.{col} (already exists)")

        # List all tables now in DB
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        tables = [r[0] for r in result.fetchall()]
        print(f"\nAll tables in DB: {tables}")

    print("\nMigration complete — start the app normally: python app.py")

asyncio.run(run())