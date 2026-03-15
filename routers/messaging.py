"""
Pyrogram Messaging Router

BUG FIXES:
  - InputPhoneContact(phone_num, "User") → correct kwarg: phone=, first_name=
  - send_photo/video/audio: use keyword args (Pyrogram 2.x)
  - Bulk phone resolution: all numbers in ONE import_contacts call (speed)
"""
import asyncio
import random
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pyrogram.errors import FloodWait, UserBannedInChannel, PeerFlood, UserDeactivatedBan, PeerIdInvalid
from pyrogram.types import InputPhoneContact

from core.database import get_db, async_session
from core.models import Account, Proxy, MessageTemplate, Log, FailedMessage
from services.telegram import client_manager

router = APIRouter()


class SendRequest(BaseModel):
    account_ids:     list[int]
    targets:         list[str]
    message:         str        = ""
    template_id:     int | None = None
    variables:       dict       = {}
    media_path:      str | None = None
    media_type:      str        = ""
    delay_min:       int        = 5
    delay_max:       int        = 15
    mode:            str        = "sequential"
    max_per_account: int        = 0
    rotate_proxies:  bool       = False
    auto_retry:      bool       = False
    campaign_id:     int | None = None


_active_jobs: dict[str, dict] = {}


def _resolve_message(message: str, template_text: str | None,
                     variables: dict, target: str) -> str:
    text = template_text if template_text else message
    variables["target"] = target
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


async def _bulk_resolve_phones(client, phone_targets: list[str]) -> dict[str, int | None]:
    """
    Resolve all phone numbers in ONE import_contacts API call.
    Returns dict: original_target → user_id (or None if not found).

    FIX: InputPhoneContact Pyrogram kwarg is phone= (NOT phone_number=)
    """
    if not phone_targets:
        return {}

    contacts = [
        InputPhoneContact(
            phone=p if p.startswith("+") else f"+{p}",
            first_name="User",
            last_name="",
        )
        for p in phone_targets
    ]
    result_map: dict[str, int | None] = {}
    try:
        result = await client.import_contacts(contacts)
        # Map phone_number → user_id
        id_map = {}
        for u in result.users:
            if hasattr(u, "phone_number") and u.phone_number:
                id_map[u.phone_number.lstrip("+")] = u.id
                id_map[f"+{u.phone_number.lstrip('+')}"] = u.id

        for p in phone_targets:
            phone_e164 = p if p.startswith("+") else f"+{p}"
            uid = id_map.get(phone_e164) or id_map.get(p.lstrip("+"))
            result_map[p] = uid
    except Exception as e:
        # Fallback: try phones directly
        for p in phone_targets:
            result_map[p] = p if p.startswith("+") else f"+{p}"
    return result_map


async def _send_bulk(job_id: str, account_ids: list[int], targets: list[str],
                     message: str, template_text: str | None, variables: dict,
                     media_path: str | None, delay_min: int, delay_max: int,
                     mode: str, max_per_account: int = 0,
                     rotate_proxies: bool = False, auto_retry: bool = False,
                     campaign_id: int | None = None, media_type: str = ""):
    job = _active_jobs[job_id]

    async with async_session() as db:
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

    # ── Connect clients ───────────────────────────────────────────────────────
    clients: list[tuple[Account, object, object]] = []
    for acc in accounts:
        try:
            client = await client_manager.get_client(acc.id, acc.phone, acc.proxy)
            clients.append((acc, client, acc.proxy))
        except Exception as e:
            async with async_session() as db:
                db.add(Log(level="error", category="message", account_id=acc.id,
                           message=f"Failed to connect: {e}"))
                await db.commit()

    if not clients:
        job["status"] = "failed"
        job["error"]  = "Could not connect any account"
        return

    job["status"] = "running"

    # ── Bulk phone resolution BEFORE send loop ───────────────────────────────
    phone_targets  = [t for t in targets
                      if t.startswith("+") or
                      (t.lstrip("+").isdigit() and len(t.lstrip("+")) >= 7)]
    direct_targets = [t for t in targets if t not in phone_targets]

    _resolved_map: dict[str, object] = {t: t for t in direct_targets}

    if phone_targets:
        bulk_acc, bulk_client, _ = clients[0]
        job["message"] = f"Resolving {len(phone_targets)} phone(s)…"
        phone_resolve = await _bulk_resolve_phones(bulk_client, phone_targets)
        not_found = []
        for p, uid in phone_resolve.items():
            if uid is None:
                not_found.append(p)
            else:
                _resolved_map[p] = uid

        if not_found:
            job["failed"] = len(not_found)
            async with async_session() as db:
                for p in not_found:
                    db.add(Log(level="warn", category="message", account_id=bulk_acc.id,
                               message=f"Phone {p} not on Telegram — skipped"))
                    db.add(FailedMessage(campaign_id=campaign_id, target=p,
                                         error="Phone not on Telegram"))
                await db.commit()

    effective = [t for t in targets if _resolved_map.get(t) is not None]
    job["total"] = len(effective)

    account_counts: dict[int, int]   = {acc.id: 0 for acc, _, _ in clients}
    blocked_until:  dict[int, float] = {}
    failed_targets: list[dict]       = []

    for i, target in enumerate(effective):
        if job.get("cancelled"):
            job["status"] = "cancelled"
            break

        # Pick account
        acc = client = cur_proxy = None
        for attempt in range(len(clients)):
            idx = ((i + attempt) % len(clients)) if mode == "round-robin"                   else (attempt % len(clients))
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
            failed_targets.append({"target": target, "error": "No available account"})
            continue

        text    = _resolve_message(message, template_text, dict(variables), target)
        resolved = _resolved_map.get(target, target)
        sent_ok  = False
        retries  = 0

        while retries <= 2:
            try:
                if media_path:
                    # FIX: Pyrogram 2.x — use keyword args for all send methods
                    if media_type == "photo":
                        await client.send_photo(chat_id=resolved,
                                                photo=media_path, caption=text)
                    elif media_type == "video":
                        await client.send_video(chat_id=resolved,
                                                video=media_path, caption=text)
                    elif media_type == "audio":
                        await client.send_audio(chat_id=resolved,
                                                audio=media_path, caption=text)
                    else:
                        await client.send_document(chat_id=resolved,
                                                   document=media_path, caption=text)
                else:
                    await client.send_message(chat_id=resolved, text=text)

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

            except FloodWait as e:
                wait = e.value
                blocked_until[acc.id] = time.time() + wait
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"FloodWait {wait}s for {target}"))
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
                    await asyncio.sleep(min(wait, 60))
                retries += 1

            except (PeerFlood, UserBannedInChannel) as e:
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
                    return
                retries += 1

            except UserDeactivatedBan:
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
                    return
                retries += 1

            except PeerIdInvalid:
                async with async_session() as db:
                    db.add(Log(level="warn", category="message", account_id=acc.id,
                               message=f"PeerIdInvalid for {target} — skip"))
                    await db.commit()
                break

            except Exception as e:
                proxy_label = f"{cur_proxy.host}:{cur_proxy.port}" if cur_proxy else "direct"
                async with async_session() as db:
                    db.add(Log(level="error", category="message", account_id=acc.id,
                               message=f"Send to {target} via {proxy_label} failed "
                                       f"(attempt {retries+1}/3): {e}"))
                    await db.commit()
                retries += 1
                if retries <= 2:
                    await asyncio.sleep(2 ** retries)

        if not sent_ok:
            job["failed"] += 1
            failed_targets.append({"target": target, "error": "failed after retries",
                                   "message_text": text})

        if i < len(effective) - 1 and not job.get("cancelled"):
            await asyncio.sleep(random.uniform(delay_min, delay_max))

    if failed_targets:
        async with async_session() as db:
            for ft in failed_targets:
                db.add(FailedMessage(campaign_id=campaign_id, target=ft["target"],
                                     message_text=ft.get("message_text", ""),
                                     error=ft.get("error", "")))
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