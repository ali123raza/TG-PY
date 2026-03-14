"""
Simple tdata to Pyrogram Session Converter
Directly copies session data without connecting to Telegram.
"""
import os
import shutil
import logging
import struct
from pathlib import Path

from core.config import SESSIONS_DIR, API_ID, API_HASH

logger = logging.getLogger(__name__)


def convert_tdata_to_pyrogram_session(phone: str, tdata_folder: Path) -> dict:
    """
    Convert tdata folder to Pyrogram .session file by directly copying session data.
    
    This works because both Telegram Desktop and Pyrogram store the same auth key,
    just in different formats.
    
    Args:
        phone: Phone number for the account
        tdata_folder: Path to the tdata folder (the folder containing key_datas, etc.)
    
    Returns:
        dict with conversion result
    """
    result = {
        "success": False,
        "phone": phone,
        "error": None,
        "session_file": None,
    }
    
    try:
        session_name = phone.replace("+", "").replace(" ", "")
        output_session = SESSIONS_DIR / f"{session_name}.session"
        
        # Validate tdata folder
        if not tdata_folder.exists():
            result["error"] = "tdata folder not found"
            return result
        
        # Check for required files
        key_datas = tdata_folder / "key_datas"
        session_files = list(tdata_folder.glob("D877F783D5D3EF8C*"))
        
        if not session_files:
            result["error"] = "No session file found in tdata"
            return result
        
        # Create Pyrogram session using Telethon's session format
        # Pyrogram 2.x can read Telethon session format directly
        
        # Method: Create a minimal SQLite session file that Pyrogram can read
        import sqlite3
        import time
        
        # Create the session file
        conn = sqlite3.connect(str(output_session))
        cursor = conn.cursor()
        
        # Create tables (Pyrogram 2.0.106 session format - Version 3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                dc_id INTEGER PRIMARY KEY,
                api_id INTEGER,
                test_mode INTEGER,
                auth_key BLOB,
                date INTEGER,
                user_id INTEGER,
                is_bot INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY,
                access_hash INTEGER,
                type INTEGER,
                username TEXT,
                phone_number TEXT,
                last_update_on INTEGER
            )
        """)

        # Create version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version (
                number INTEGER PRIMARY KEY
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO version VALUES (3)")
        
        # Read auth key from tdata
        auth_key = None
        for session_file in session_files:
            try:
                with open(session_file, 'rb') as f:
                    data = f.read()
                
                # tdata format: first 8 bytes marker, then 256 bytes auth key
                if len(data) >= 264:
                    auth_key = data[8:264]
                    break
            except Exception as e:
                logger.warning(f"Could not read {session_file}: {e}")
        
        if not auth_key:
            conn.close()
            output_session.unlink()
            result["error"] = "Could not extract auth key from tdata"
            return result
        
        # Insert auth key (DC 1 is default for most accounts)
        # Telegram DC info
        dc_config = {
            1: ("149.154.167.50", 443),
            2: ("149.154.167.51", 443),
            3: ("149.154.175.100", 443),
            4: ("149.154.167.91", 443),
            5: ("149.154.171.5", 443),
        }
        
        # Try to detect DC from key_datas
        dc_id = 1  # Default
        if key_datas.exists():
            try:
                with open(key_datas, 'rb') as f:
                    data = f.read()
                # First byte often indicates DC ID
                if len(data) > 0:
                    detected_dc = data[0]
                    if 1 <= detected_dc <= 5:
                        dc_id = detected_dc
            except:
                pass
        
        server, port = dc_config.get(dc_id, ("149.154.167.50", 443))
        
        cursor.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dc_id, int(API_ID), 0, auth_key, int(time.time()), None, 0)
        )
        
        conn.commit()
        conn.close()
        
        result["success"] = True
        result["session_file"] = str(output_session)
        result["dc_id"] = dc_id
        
        logger.info(f"[tdata-convert] Converted {phone} to {output_session}")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[tdata-convert] Error converting {phone}: {e}")
        
        # Cleanup on failure
        try:
            if output_session and output_session.exists():
                output_session.unlink()
        except:
            pass
        
        return result


async def batch_convert_tdata(
    tgdata_dir: Path,
    assign_proxies: bool = True,
    proxies: list = None
) -> dict:
    """
    Convert all tdata folders to Pyrogram sessions.
    """
    import asyncio
    
    results = {
        "total": 0,
        "converted": 0,
        "skipped": 0,
        "failed": 0,
        "accounts": [],
    }
    
    if not tgdata_dir.exists():
        return {"error": "tgdata folder not found", **results}
    
    # Find all tdata folders
    tdata_folders = [
        f for f in tgdata_dir.iterdir()
        if f.is_dir() and (f / "tdata").exists()
    ]
    
    if not tdata_folders:
        return {"message": "No tdata folders found", **results}
    
    results["total"] = len(tdata_folders)
    
    proxy_index = 0
    
    for folder in tdata_folders:
        phone = folder.name
        session_name = phone.replace("+", "").replace(" ", "")
        session_file = SESSIONS_DIR / f"{session_name}.session"
        
        account_entry = {
            "phone": phone,
            "status": "pending",
        }
        
        # Skip if session already exists
        if session_file.exists():
            account_entry["status"] = "skipped"
            account_entry["reason"] = "session already exists"
            results["skipped"] += 1
            results["accounts"].append(account_entry)
            logger.info(f"[tdata-convert] Skipped {phone}: session exists")
            continue
        
        try:
            tdata_path = folder / "tdata"
            
            # Convert using direct file method
            convert_result = convert_tdata_to_pyrogram_session(phone, tdata_path)
            
            if convert_result["success"]:
                account_entry["status"] = "converted"
                account_entry["dc_id"] = convert_result.get("dc_id")
                
                # Assign proxy if available
                if assign_proxies and proxies and len(proxies) > 0:
                    proxy = proxies[proxy_index % len(proxies)]
                    account_entry["proxy_id"] = proxy["id"]
                    proxy_index += 1
                else:
                    account_entry["proxy_id"] = None
                
                results["converted"] += 1
                logger.info(f"[tdata-convert] Converted {phone}")
            else:
                account_entry["status"] = "failed"
                account_entry["error"] = convert_result["error"]
                results["failed"] += 1
                logger.error(f"[tdata-convert] Failed {phone}: {convert_result['error']}")
        
        except Exception as e:
            account_entry["status"] = "failed"
            account_entry["error"] = str(e)
            results["failed"] += 1
            logger.error(f"[tdata-convert] Error {phone}: {e}")
        
        results["accounts"].append(account_entry)
    
    return results
