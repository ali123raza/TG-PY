"""
Telethon-based Messaging Router

FIXES applied:
  - send_photo/send_video/send_audio → send_file()   (Telethon API)
  - InputPhoneContact phone kwarg fixed
  - Phone resolution error handling improved
  - is_connected property → is_connected() method
"""
import asyncio
import random
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from telethon.errors import (
    FloodWaitError, UserBannedInChannelError, PeerFloodError,
    UserPrivacyRestrictedError, PeerIdInvalidError,
)

from core.database import get_db, async_session
from core.models import Account, Proxy, MessageTemplate, Log, FailedMessage
from services.telethon_client import client_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class SendRequest(BaseModel):
    account_ids:     list[int]
    targets:         list[str]
    message:         str            = ""
    template_id:     int | None     = None
    variables:       dict           = {}
    media_path:      str | None     = None
    media_type:      str            = ""
    delay_min:       int            = 5
    delay_max:       int            = 15
    mode:            str            = "sequential"
    max_per_account: int            = 0
    rotate_proxies:  bool           = False   # FIX: default False — use account proxy
    auto_retry:      bool           = False
    campaign_id:     int | None     = None


_active_jobs: dict[str, dict] = {}


def _resolve_text(template: str | None, custom: str, variables: dict, target: str) -> str:
    text = template if template else custom
    variables = {**variables, "target": target}
    for k, v in variables.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


async def _resolve_phone(client, phone: str) -> int | str | None:
    """
    Resolve a phone number to a Telegram user_id via contact import.
    Returns user_id (int) on success, None if not on Telegram.

    FIX: Telethon InputPhoneContact uses 'phone' kwarg (same as Pyrogram).
    """
    from telethon.tl.types import InputPhoneContact
    phone_e164 = phone if phone.startswith("+") else f"+{phone}"
    try:
        result = await client(
            # Telethon raw API call
            __import__("telethon.tl.functions.contacts", fromlist=["ImportContactsRequest"])
            .ImportContactsRequest(
                contacts=[InputPhoneContact(
                    client_id=0,
                    phone=phone_e164,     # FIX: correct kwarg
                    first_name="User",
                    last_name="",
                )]
            )
        )
        if result.users:
            return result.users[0].id
        return None
    except Exception as e:
        logger.warning("Could not resolve phone %s: %s", phone, e)
        return None


async def _send_media(client, entity, media_path: str, media_type: str, caption: str):
    """
    Send media using Telethon's unified send_file() API.

    FIX: Telethon does NOT have send_photo/send_video/send_audio.
    All media goes through send_file() — Telethon auto-detects type.
    """
    await client.send_file(entity, media_path, caption=caption)


async def _send_bulk(
    job_id: str,
    account_ids: list[int],
    targets: list[str],
    message: str,
    template_text: str | None,
    variables: dict,
    media_path: str | None,
    delay_min: int,
    delay_max: int,
    mode: str,
    max_per_account: int  = 0,
    rotate_proxies: bool  = False,
    auto_retry: bool      = False,
    campaign_id: int | None = None,
    media_type: str       = "",
):
    job = _active_jobs[job_id]

    async with async_session() as db:
        # Load accounts WITH their assigned proxies
        result = await db.execute(
            select(Account)
            .options(selectinload(Account.proxy))
            .where(Account.id.in_(account_ids), Account.is_active == True)
        )
        accounts = list(result.scalars().all())

        if not accounts:
            job["status"] = "failed"
            job["error"]  = "No active accounts found"
            return

    # Connect clients — each uses its OWN proxy
    clients: list[tuple[Account, object, object]] = []
    for acc in accounts:
        proxy = acc.proxy
        proxy_label = f"{proxy.host}:{proxy.port}" if proxy else "direct"
        try:
            client = await client_manager.get_client(acc.id, acc.phone, proxy)
            clients.append((acc, client, proxy))
        except Exception as e:
            logger.error("Account %s connect failed via %s: %s", acc.phone, proxy_label, e)
            async with async_session() as db:
                db.add(Log(level="error", category="message", account_id=acc.id,
                           message=f"Connect failed via {proxy_label}: {e}"))
                await db.commit()

    if not clients:
        job["status"] = "failed"
        job["error"]  = "Could not connect any account"
        return

    job["status"] = "running"
    job["total"]  = len(targets)

    account_counts: dict[int, int]   = {acc.id: 0 for acc, _, _ in clients}
    blocked_until:  dict[int, float] = {}
    failed_targets: list[dict]       = []

    for i, target in enumerate(targets):
        if job.get("cancelled"):
            job["status"] = "cancelled"
            break

        # ── Pick account ─────────────────────────────────────────────────────
        acc = client = cur_proxy = None
        for attempt in range(len(clients)):
            idx = ((i + attempt) % len(clients)) if mode == "round_robin" \
                  else (attempt % len(clients))
            c_acc, c_client, c_proxy = clients[idx]
            if max_per_account > 0 and account_counts[c_acc.id] >= max_per_account:
                continue
            if c_acc.id in blocked_until and time.time() < blocked_until[c_acc.id]:
                continue
            blocked_until.pop(c_acc.id, None)
            acc, client, cur_proxy = c_acc, c_client, c_proxy
            break

        if not acc:
            job["failed"] += 1
            failed_targets.append({"target": target, "error": "All accounts blocked/at limit"})
            continue

        text = _resolve_text(template_text, message, dict(variables), target)

        # ── Resolve phone numbers ─────────────────────────────────────────────
        resolved = target
        if target.startswith("+") or (target.lstrip("+").isdigit() and len(target) > 7):
            user_id = await _resolve_phone(client, target)
            if user_id is None:
                job["failed"] += 1
                failed_targets.append({"target": target,
                                       "error": "Phone not registered on Telegram"})
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"Phone {target} not on Telegram — skipped"))
                    await db.commit()
                continue
            resolved = user_id

        # ── Send with retry ───────────────────────────────────────────────────
        sent_ok = False
        for retry in range(3):
            try:
                # FIX: reconnect check (is_connected is a METHOD in Telethon)
                if not client.is_connected():
                    client = await client_manager.get_client(acc.id, acc.phone, cur_proxy)

                if media_path:
                    # FIX: Telethon uses send_file() for ALL media types
                    await _send_media(client, resolved, media_path, media_type, text)
                else:
                    await client.send_message(resolved, text)

                sent_ok = True
                job["sent"] += 1
                account_counts[acc.id] += 1

                async with async_session() as db:
                    acc_row = await db.get(Account, acc.id)
                    if acc_row:
                        acc_row.messages_sent = (acc_row.messages_sent or 0) + 1
                    proxy_label = f"{cur_proxy.host}:{cur_proxy.port}" if cur_proxy else "direct"
                    db.add(Log(level="info", category="message", account_id=acc.id,
                               message=f"Sent to {target} via {proxy_label}"))
                    await db.commit()
                break

            except FloodWaitError as e:
                wait = e.seconds
                blocked_until[acc.id] = time.time() + wait
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"FloodWait {wait}s"))
                    await db.commit()
                # Try another account
                switched = False
                for a2, c2, p2 in clients:
                    if a2.id != acc.id and a2.id not in blocked_until:
                        if max_per_account <= 0 or account_counts[a2.id] < max_per_account:
                            acc, client, cur_proxy = a2, c2, p2
                            switched = True
                            break
                if not switched:
                    await asyncio.sleep(min(wait, 30))

            except UserPrivacyRestrictedError:
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"User {target} has privacy restrictions"))
                    await db.commit()
                break   # no point retrying

            except PeerIdInvalidError:
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"PeerIdInvalid for {target} — skip"))
                    await db.commit()
                break

            except (PeerFloodError, UserBannedInChannelError) as e:
                async with async_session() as db:
                    acc_row = await db.get(Account, acc.id)
                    if acc_row:
                        acc_row.status    = "restricted"
                        acc_row.is_active = False
                    db.add(Log(level="error", category="message", account_id=acc.id,
                               message=f"Account restricted: {e}"))
                    await db.commit()
                clients = [(a, c, p) for a, c, p in clients if a.id != acc.id]
                if not clients:
                    job["status"] = "failed"
                    job["error"]  = "All accounts restricted"
                    return
                break

            except Exception as e:
                err_lower = str(e).lower()
                if any(x in err_lower for x in ("deactivated", "banned", "auth_key")):
                    async with async_session() as db:
                        acc_row = await db.get(Account, acc.id)
                        if acc_row:
                            acc_row.status    = "banned"
                            acc_row.is_active = False
                        db.add(Log(level="error", category="message", account_id=acc.id,
                                   message="Account banned/deactivated"))
                        await db.commit()
                    clients = [(a, c, p) for a, c, p in clients if a.id != acc.id]
                    if not clients:
                        job["status"] = "failed"
                        job["error"]  = "All accounts banned"
                        return
                    break
                else:
                    proxy_label = f"{cur_proxy.host}:{cur_proxy.port}" if cur_proxy else "direct"
                    async with async_session() as db:
                        db.add(Log(level="error", category="message", account_id=acc.id,
                                   message=f"Send to {target} via {proxy_label} failed "
                                           f"(retry {retry+1}/3): {e}"))
                        await db.commit()
                    if retry < 2:
                        await asyncio.sleep(2 ** retry)
                    else:
                        break

        if not sent_ok:
            job["failed"] += 1
            failed_targets.append({"target": target,
                                   "error": "failed after 3 retries",
                                   "message_text": text})

        if i < len(targets) - 1 and not job.get("cancelled"):
            await asyncio.sleep(random.uniform(delay_min, delay_max))

    if failed_targets:
        async with async_session() as db:
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
    job["message"] = f"sent: {job['sent']}, failed: {job['failed']}"


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
        req.max_per_account, req.rotate_proxies, req.auto_retry,
        req.campaign_id, req.media_type,
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


@router.get("/logs")
async def get_message_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Log).where(Log.category == "message")
        .order_by(Log.id.desc()).limit(limit)
    )
    return [
        {"id": l.id, "level": l.level, "account_id": l.account_id,
         "message": l.message, "created_at": l.created_at.isoformat()}
        for l in result.scalars().all()
    ]