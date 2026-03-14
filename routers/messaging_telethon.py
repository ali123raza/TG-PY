"""
Telethon-based Messaging Router
Supports bulk messaging with proxy rotation and flood wait handling.
"""
import asyncio
import random
import time
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import FloodWaitError, UserBannedInChannelError, PeerFloodError
from telethon.tl.types import InputPhoneContact

from core.database import get_db, async_session
from core.models import Account, Proxy, MessageTemplate, Log, FailedMessage
from services.telethon_client import client_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class SendRequest(BaseModel):
    account_ids: list[int]
    targets: list[str]
    message: str = ""
    template_id: int | None = None
    variables: dict = {}
    media_path: str | None = None
    media_type: str = ""
    delay_min: int = 5
    delay_max: int = 15
    mode: str = "sequential"
    max_per_account: int = 0
    rotate_proxies: bool = True
    auto_retry: bool = False
    campaign_id: int | None = None


_active_jobs: dict[str, dict] = {}


def _resolve_message(message: str, template_text: str | None, variables: dict, target: str) -> str:
    text = template_text if template_text else message
    variables["target"] = target
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


async def _load_accounts_with_proxies(db, account_ids: list[int]) -> list[tuple]:
    """Load accounts with their proxy relationships eagerly."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.proxy))
        .where(Account.id.in_(account_ids), Account.is_active == True)
    )
    return list(result.scalars().all())


async def _load_all_proxies(db) -> list:
    """Load all active proxies for rotation pool."""
    result = await db.execute(select(Proxy).where(Proxy.is_active == True))
    return list(result.scalars().all())


async def _send_bulk(job_id: str, account_ids: list[int], targets: list[str],
                     message: str, template_text: str | None, variables: dict,
                     media_path: str | None, delay_min: int, delay_max: int, mode: str,
                     max_per_account: int = 0, rotate_proxies: bool = True,
                     auto_retry: bool = False, campaign_id: int | None = None,
                     media_type: str = ""):
    """Background task with anti-ban: account rotation, proxy rotation, flood wait."""
    job = _active_jobs[job_id]
    
    async with async_session() as db:
        # Load accounts WITH their assigned proxies
        accounts = await _load_accounts_with_proxies(db, account_ids)
        if not accounts:
            job["status"] = "failed"
            job["error"] = "No active accounts found"
            return
        
        # Load all proxies for rotation pool
        all_proxies = await _load_all_proxies(db) if rotate_proxies else []
        proxy_pool_idx = 0
        
        # Connect clients with their assigned proxies
        clients = []
        for acc in accounts:
            try:
                proxy = acc.proxy
                session_path = None
                if acc.session_file:
                    # Check if it's a tdata path
                    from pathlib import Path
                    tdata_path = Path(f"tgdata/{acc.session_name if hasattr(acc, 'session_name') else acc.phone.replace('+', '')}/tdata")
                    if tdata_path.exists():
                        session_path = str(tdata_path)
                
                client = await client_manager.get_client(
                    acc.id, acc.phone, proxy, session_path
                )
                clients.append((acc, client, proxy))
            except Exception as e:
                logger.error(f"Failed to connect account {acc.id}: {e}")
                db.add(Log(level="error", category="message", account_id=acc.id,
                          message=f"Failed to connect: {e}"))
                await db.commit()
        
        if not clients:
            job["status"] = "failed"
            job["error"] = "Could not connect any account"
            return
        
        job["status"] = "running"
        job["total"] = len(targets)
        
        account_counts: dict[int, int] = {acc.id: 0 for acc, _, _ in clients}
        blocked_until: dict[int, float] = {}
        failed_targets: list[dict] = []
        
        for i, target in enumerate(targets):
            if job.get("cancelled"):
                job["status"] = "cancelled"
                break
            
            # Pick account with rotation + per-account limit
            acc, client, cur_proxy = None, None, None
            for attempt in range(len(clients)):
                if mode == "round-robin":
                    idx = (i + attempt) % len(clients)
                else:
                    idx = attempt % len(clients)
                candidate_acc, candidate_client, candidate_proxy = clients[idx]
                
                if max_per_account > 0 and account_counts[candidate_acc.id] >= max_per_account:
                    continue
                if candidate_acc.id in blocked_until:
                    if time.time() < blocked_until[candidate_acc.id]:
                        continue
                    else:
                        del blocked_until[candidate_acc.id]
                
                acc, client, cur_proxy = candidate_acc, candidate_client, candidate_proxy
                break
            
            if not acc:
                job["failed"] += 1
                db.add(Log(level="warn", category="message",
                          message=f"No available account for {target} (limits/blocks)"))
                failed_targets.append({"target": target, "error": "All accounts at limit or blocked"})
                await db.commit()
                continue
            
            text = _resolve_message(message, template_text, dict(variables), target)
            sent_ok = False
            retries = 0
            
            # Resolve phone numbers to user IDs via contact import
            resolved_target = target
            if target.startswith("+") or target.replace(" ", "").isdigit():
                try:
                    phone_num = target if target.startswith("+") else f"+{target}"
                    result = await client.import_contacts([InputPhoneContact(phone_num, "User")])
                    if result.users:
                        resolved_target = result.users[0].id
                except Exception:
                    pass
            
            while retries <= 2:
                try:
                    if media_path:
                        if media_type == "photo":
                            await client.send_photo(resolved_target, media_path, caption=text)
                        elif media_type == "video":
                            await client.send_video(resolved_target, media_path, caption=text)
                        elif media_type == "audio":
                            await client.send_audio(resolved_target, media_path, caption=text)
                        else:
                            await client.send_file(resolved_target, media_path, caption=text)
                    else:
                        await client.send_message(resolved_target, text)
                    
                    sent_ok = True
                    job["sent"] += 1
                    account_counts[acc.id] += 1
                    
                    acc.messages_sent = (acc.messages_sent or 0) + 1
                    await db.merge(acc)
                    db.add(Log(level="info", category="message", account_id=acc.id,
                              message=f"Sent to {target} via proxy:{cur_proxy.host if cur_proxy else 'direct'}"))
                    await db.commit()
                    break
                
                except FloodWaitError as e:
                    wait_time = e.seconds
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                              message=f"FloodWait {wait_time}s for {target}"))
                    await db.commit()
                    blocked_until[acc.id] = time.time() + wait_time
                    
                    # Try switching to another account
                    switched = False
                    for alt_acc, alt_client, alt_proxy in clients:
                        if alt_acc.id != acc.id and alt_acc.id not in blocked_until:
                            if max_per_account <= 0 or account_counts[alt_acc.id] < max_per_account:
                                acc, client, cur_proxy = alt_acc, alt_client, alt_proxy
                                switched = True
                                break
                    
                    if not switched:
                        # Try rotating proxy on current account before waiting
                        if rotate_proxies and all_proxies:
                            proxy_pool_idx = (proxy_pool_idx + 1) % len(all_proxies)
                            new_proxy = all_proxies[proxy_pool_idx]
                            try:
                                client = await client_manager.get_client(acc.id, acc.phone, new_proxy)
                                cur_proxy = new_proxy
                                db.add(Log(level="info", category="message", account_id=acc.id,
                                          message=f"Rotated proxy to {new_proxy['addr']}:{new_proxy['port']}"))
                                await db.commit()
                                # Update in clients list
                                clients = [(a, c if a.id != acc.id else client,
                                           p if a.id != acc.id else new_proxy)
                                          for a, c, p in clients]
                            except Exception:
                                pass
                        await asyncio.sleep(min(wait_time, 60))
                    retries += 1
                
                except (PeerFloodError, UserBannedInChannelError) as e:
                    db.add(Log(level="error", category="message", account_id=acc.id,
                              message=f"Account restricted: {e}"))
                    acc.status = "restricted"
                    acc.is_active = False
                    await db.merge(acc)
                    await db.commit()
                    clients = [(a, c, p) for a, c, p in clients if a.id != acc.id]
                    if not clients:
                        job["status"] = "failed"
                        job["error"] = "All accounts restricted"
                        return
                    retries += 1
                
                except Exception as e:
                    db.add(Log(level="error", category="message", account_id=acc.id,
                              message=f"Failed to send to {target}: {e}"))
                    await db.commit()
                    
                    # On generic error, try proxy rotation
                    if rotate_proxies and all_proxies and retries < 2:
                        proxy_pool_idx = (proxy_pool_idx + 1) % len(all_proxies)
                        new_proxy = all_proxies[proxy_pool_idx]
                        try:
                            client = await client_manager.get_client(acc.id, acc.phone, new_proxy)
                            cur_proxy = new_proxy
                            db.add(Log(level="info", category="message", account_id=acc.id,
                                      message=f"Rotated proxy to {new_proxy['addr']}:{new_proxy['port']} after error"))
                            await db.commit()
                            clients = [(a, c if a.id != acc.id else client,
                                       p if a.id != acc.id else new_proxy)
                                      for a, c, p in clients]
                            retries += 1
                            continue
                        except Exception:
                            pass
                    break
            
            if not sent_ok:
                job["failed"] += 1
                failed_targets.append({"target": target, "error": str(retries) + " retries exhausted",
                                      "message_text": text})
            
            if i < len(targets) - 1:
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)
        
        if failed_targets:
            for ft in failed_targets:
                db.add(FailedMessage(
                    campaign_id=campaign_id,
                    target=ft["target"],
                    message_text=ft.get("message_text", ""),
                    error=ft.get("error", ""),
                ))
            await db.commit()
        
        if job["status"] == "running":
            job["status"] = "completed"


@router.post("/send")
async def send_messages(req: SendRequest, background_tasks: BackgroundTasks,
                        db: AsyncSession = Depends(get_db)):
    if not req.targets:
        raise HTTPException(400, "No targets provided")
    if not req.account_ids:
        raise HTTPException(400, "No accounts selected")
    
    template_text = None
    if req.template_id:
        t = await db.get(MessageTemplate, req.template_id)
        if not t:
            raise HTTPException(404, "Template not found")
        template_text = t.text
    
    if not template_text and not req.message:
        raise HTTPException(400, "No message or template provided")
    
    job_id = f"send_{random.randint(10000, 99999)}"
    _active_jobs[job_id] = {"status": "starting", "sent": 0, "failed": 0, "total": 0}
    
    background_tasks.add_task(
        _send_bulk, job_id, req.account_ids, req.targets,
        req.message, template_text, req.variables,
        req.media_path, req.delay_min, req.delay_max, req.mode,
        req.max_per_account, req.rotate_proxies, req.auto_retry, req.campaign_id,
        req.media_type,
    )
    return {"job_id": job_id}


@router.get("/jobs")
async def list_jobs():
    return _active_jobs


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in _active_jobs:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, **_active_jobs[job_id]}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    if job_id not in _active_jobs:
        raise HTTPException(404, "Job not found")
    _active_jobs[job_id]["cancelled"] = True
    return {"ok": True}


@router.get("/failed")
async def list_failed(campaign_id: int | None = None, limit: int = 100,
                      db: AsyncSession = Depends(get_db)):
    q = select(FailedMessage).where(FailedMessage.status == "failed").order_by(FailedMessage.id.desc())
    if campaign_id:
        q = q.where(FailedMessage.campaign_id == campaign_id)
    result = await db.execute(q.limit(limit))
    return [
        {"id": f.id, "target": f.target, "error": f.error, "retries": f.retries,
         "campaign_id": f.campaign_id, "created_at": f.created_at.isoformat()}
        for f in result.scalars().all()
    ]


@router.post("/retry")
async def retry_failed(background_tasks: BackgroundTasks,
                       account_ids: list[int] = [],
                       campaign_id: int | None = None,
                       delay_min: int = 30, delay_max: int = 60,
                       db: AsyncSession = Depends(get_db)):
    q = select(FailedMessage).where(FailedMessage.status == "failed")
    if campaign_id:
        q = q.where(FailedMessage.campaign_id == campaign_id)
    result = await db.execute(q)
    failed = list(result.scalars().all())
    
    if not failed:
        raise HTTPException(400, "No failed messages to retry")
    if not account_ids:
        raise HTTPException(400, "No accounts selected for retry")
    
    targets = [f.target for f in failed]
    message_text = failed[0].message_text or ""
    
    for f in failed:
        f.status = "retrying"
        f.retries += 1
    await db.commit()
    
    job_id = f"retry_{random.randint(10000, 99999)}"
    _active_jobs[job_id] = {"status": "starting", "sent": 0, "failed": 0, "total": 0}
    
    background_tasks.add_task(
        _send_bulk, job_id, account_ids, targets,
        message_text, None, {}, None, delay_min, delay_max, "round-robin",
    )
    return {"job_id": job_id, "retrying": len(targets)}


@router.get("/logs")
async def get_message_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Log).where(Log.category == "message").order_by(Log.id.desc()).limit(limit)
    )
    return [
        {"id": l.id, "level": l.level, "account_id": l.account_id,
         "message": l.message, "created_at": l.created_at.isoformat()}
        for l in result.scalars().all()
    ]
