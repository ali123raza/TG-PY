"""
tdata Import Service - Converts Telegram Desktop tdata to Pyrogram sessions.
"""
import os
import shutil
import logging
import asyncio
from pathlib import Path
from sqlalchemy import select

from core.config import SESSIONS_DIR, BASE_DIR
from core.database import async_session
from core.models import Account, Proxy
from services.tdata_converter import batch_convert_tdata

logger = logging.getLogger(__name__)


async def import_tdata_accounts(
    tgdata_dir: Path,
    assign_proxies: bool = True
) -> dict:
    """
    Import all tdata folders as Pyrogram sessions.
    Converts tdata → .session files, then creates database entries.
    
    Args:
        tgdata_dir: Path to tgdata folder containing account subfolders
        assign_proxies: Whether to auto-assign proxies (round-robin)
    
    Returns:
        dict with import results
    """
    results = {
        "total": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "accounts": [],
    }
    
    if not tgdata_dir.exists():
        return {"error": "tgdata folder not found", **results}
    
    # Get all tdata subfolders
    tdata_folders = [
        f for f in tgdata_dir.iterdir()
        if f.is_dir() and (f / "tdata").exists()
    ]
    
    if not tdata_folders:
        return {"message": "No tdata folders found", **results}
    
    results["total"] = len(tdata_folders)
    
    # Get existing phones to skip duplicates
    async with async_session() as db:
        result = await db.execute(select(Account.phone))
        existing_phones = set()
        for row in result.scalars().all():
            existing_phones.add(row.replace("+", "").replace(" ", ""))
        
        # Get active proxies for round-robin assignment
        if assign_proxies:
            proxy_result = await db.execute(
                select(Proxy).where(Proxy.is_active == True).order_by(Proxy.id)
            )
            proxies = [
                {"id": p.id, "scheme": p.scheme, "host": p.host, "port": p.port,
                 "username": p.username, "password": p.password}
                for p in proxy_result.scalars().all()
            ]
        else:
            proxies = []
    
    # Convert tdata to sessions
    convert_results = await batch_convert_tdata(tgdata_dir, assign_proxies, proxies)
    
    if "error" in convert_results:
        return convert_results
    
    # Create database entries for converted sessions
    for account_entry in convert_results.get("accounts", []):
        phone = account_entry["phone"]
        session_name = phone.replace("+", "").replace(" ", "")
        
        if account_entry["status"] == "skipped":
            results["skipped"] += 1
            results["accounts"].append({
                "phone": phone,
                "status": "skipped",
                "reason": account_entry.get("reason", "already exists"),
            })
            continue
        
        if account_entry["status"] == "failed":
            results["failed"] += 1
            results["accounts"].append({
                "phone": phone,
                "status": "failed",
                "error": account_entry.get("error", "unknown error"),
            })
            continue
        
        if account_entry["status"] == "converted":
            # Check if already in database
            if session_name in existing_phones:
                results["skipped"] += 1
                results["accounts"].append({
                    "phone": phone,
                    "status": "skipped",
                    "reason": "already in database",
                })
                continue
            
            # Create database entry
            user_info = account_entry.get("user_info", {})
            proxy_id = account_entry.get("proxy_id")
            
            async with async_session() as db:
                account = Account(
                    phone=phone,
                    name=f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or f"Account_{phone}",
                    username=user_info.get("username", ""),
                    session_file=session_name,
                    proxy_id=proxy_id,
                    is_active=True,
                    status="active",
                )
                db.add(account)
                await db.commit()
                await db.refresh(account)
                
                results["imported"] += 1
                results["accounts"].append({
                    "phone": phone,
                    "status": "imported",
                    "id": account.id,
                    "name": account.name,
                    "username": account.username,
                    "proxy_id": proxy_id,
                    "proxy_assigned": proxy_id is not None,
                })
                
                logger.info(f"[tdata-import] Imported {phone} ({account.name})")
    
    return results
