"""
Unified Service Manager - Direct access to backend services from UI
"""
import asyncio
import os
import logging
import random
import re
import time
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import SESSIONS_DIR, BASE_DIR, MEDIA_DIR, TGDATA_DIR
from core.database import async_session, init_db
from core.models import (Account, Proxy, Campaign, MessageTemplate,
                         TemplateVariant, TemplateCategory, TemplateMedia,
                         Peer, Contact, Log, FailedMessage)
from services.telegram import client_manager
from services.tdata_import import import_tdata_accounts as _import_tdata_accounts

logger = logging.getLogger(__name__)

# ── In-memory job tracking ───────────────────────────────────────────────────
_load_jobs:    dict[str, dict] = {}
_import_jobs:  dict[str, dict] = {}
_send_jobs:    dict[str, dict] = {}   # messaging jobs
_scrape_jobs:  dict[str, dict] = {}
_join_jobs:    dict[str, dict] = {}
_import_contact_jobs: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _new_job(store: dict, **extra) -> str:
    job_id = str(uuid.uuid4())[:12]
    store[job_id] = {"status": "starting", "sent": 0, "failed": 0,
                     "total": 0, "progress": 0, "message": "", **extra}
    return job_id


import random as _random
import json as _json

def _pick_template_text(template: "MessageTemplate", custom: str) -> str:
    """Pick text from template — uses random variant if use_variants=True."""
    if template is None:
        return custom
    if template.use_variants and template.variants:
        variant = _random.choice(template.variants)
        return variant.text
    return template.text or custom


def _resolve_message(template: Optional[str], custom: str, variables: dict, target: str) -> str:
    text = template if template else custom
    variables = {**variables, "target": target}
    for k, v in variables.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


# ── ServiceManager ────────────────────────────────────────────────────────────

class ServiceManager:
    """Central service manager for direct backend access from UI."""

    def __init__(self):
        self._listeners: List[callable] = []

    async def init(self):
        await init_db()


    @staticmethod
    def _safe_json(value, default=None):
        """Safe json.loads — handles None, empty string, already-list."""
        if default is None:
            default = []
        if not value:
            return default
        if isinstance(value, list):
            return value
        try:
            import json as _json
            return _json.loads(value)
        except Exception:
            return default

    def add_listener(self, cb: callable):
        self._listeners.append(cb)

    def remove_listener(self, cb: callable):
        if cb in self._listeners:
            self._listeners.remove(cb)

    async def _notify(self, event: str, data: dict = None):
        for cb in self._listeners:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event, data)
                else:
                    cb(event, data)
            except Exception as e:
                logger.error("Listener error: %s", e)

    # ── Accounts ─────────────────────────────────────────────────────────────

    async def login_start(self, phone: str, proxy_id: Optional[int] = None) -> dict:
        async with async_session() as db:
            proxy = await db.get(Proxy, proxy_id) if proxy_id else None
            try:
                phone_code_hash = await client_manager.start_login(phone, proxy)
                return {"phone_code_hash": phone_code_hash, "status": "code_sent"}
            except Exception as e:
                raise Exception(str(e))

    async def login_complete(self, phone: str, code: str, phone_code_hash: str,
                             password: Optional[str] = None,
                             proxy_id: Optional[int] = None) -> dict:
        async with async_session() as db:
            proxy = await db.get(Proxy, proxy_id) if proxy_id else None
            try:
                user_info = await client_manager.complete_login(
                    phone, code, phone_code_hash, password)
            except ValueError as e:
                raise Exception(str(e))
            except Exception as e:
                raise Exception(str(e))

            existing = (await db.execute(
                select(Account).where(Account.phone == phone)
            )).scalar_one_or_none()

            if existing:
                existing.name = f"{user_info['first_name']} {user_info['last_name']}".strip()
                existing.username = user_info["username"]
                existing.session_file = phone.replace("+", "").replace(" ", "")
                existing.proxy_id = proxy_id
                existing.is_active = True
                existing.status = "active"
                account = existing
            else:
                account = Account(
                    phone=phone,
                    name=f"{user_info['first_name']} {user_info['last_name']}".strip(),
                    username=user_info["username"],
                    session_file=phone.replace("+", "").replace(" ", ""),
                    proxy_id=proxy_id,
                    is_active=True,
                    status="active",
                )
                db.add(account)
            await db.commit()
            await db.refresh(account)
            await self._notify("account_added", {"id": account.id, "phone": account.phone})
            return {"id": account.id, "phone": account.phone,
                    "name": account.name, "username": account.username}

    async def get_accounts(self) -> List[dict]:
        async with async_session() as db:
            result = await db.execute(select(Account).order_by(Account.created_at.desc()))
            return [self._ser_account(a) for a in result.scalars().all()]

    async def get_account(self, account_id: int) -> Optional[dict]:
        async with async_session() as db:
            a = await db.get(Account, account_id)
            return self._ser_account(a) if a else None

    async def update_account(self, account_id: int, data: dict) -> dict:
        async with async_session() as db:
            a = await db.get(Account, account_id)
            if not a:
                raise Exception("Account not found")
            for field in ("name", "proxy_id", "is_active"):
                if field in data and data[field] is not None:
                    setattr(a, field, data[field])
            await db.commit()
            await db.refresh(a)
            await self._notify("account_updated", {"id": a.id})
            return self._ser_account(a)

    async def delete_account(self, account_id: int) -> bool:
        async with async_session() as db:
            a = await db.get(Account, account_id)
            if not a:
                raise Exception("Account not found")
            if a.session_file:
                for suffix in (".session", ".session-journal"):
                    p = SESSIONS_DIR / f"{a.session_file}{suffix}"
                    if p.exists():
                        p.unlink()
            await db.delete(a)
            await db.commit()
            await self._notify("account_deleted", {"id": account_id})
            return True

    async def check_account_health(self, account_id: int) -> dict:
        async with async_session() as db:
            a = await db.get(Account, account_id)
            if not a:
                raise Exception("Account not found")
            proxy = await db.get(Proxy, a.proxy_id) if a.proxy_id else None
            try:
                user_info = await client_manager.verify_session(a.phone, proxy)
                a.status = "active"
                a.name = f"{user_info['first_name']} {user_info['last_name']}".strip()
                a.username = user_info["username"]
                await db.commit()
                return {"status": "ok", "info": user_info}
            except Exception as e:
                a.status = "error"
                await db.commit()
                return {"status": "error", "error": str(e)}

    async def check_all_accounts_health(self) -> dict:
        accounts = await self.get_accounts()
        results = {}
        for acc in accounts:
            try:
                results[acc["id"]] = await self.check_account_health(acc["id"])
            except Exception as e:
                results[acc["id"]] = {"status": "error", "error": str(e)}
        return results

    def _ser_account(self, a: Account) -> dict:
        return {
            "id": a.id, "phone": a.phone, "name": a.name or "",
            "username": a.username or "", "proxy_id": a.proxy_id,
            "is_active": a.is_active, "status": a.status or "unknown",
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "messages_sent": a.messages_sent or 0, "messages_failed": 0,
        }

    async def load_sessions_from_folder(self, folder_path: str,
                                        proxy_id: Optional[int] = None) -> str:
        job_id = _new_job(_load_jobs)
        asyncio.create_task(self._do_load_sessions(job_id, folder_path, proxy_id))
        return job_id

    async def _do_load_sessions(self, job_id: str, folder_path: str,
                                proxy_id: Optional[int]):
        job = _load_jobs[job_id]
        try:
            folder = Path(folder_path)
            session_files = list(folder.glob("*.session"))
            job["total"] = len(session_files)

            async with async_session() as db:
                proxy = await db.get(Proxy, proxy_id) if proxy_id else None
                for i, sf in enumerate(session_files):
                    phone = sf.stem
                    existing = (await db.execute(
                        select(Account).where(Account.phone == phone)
                    )).scalar_one_or_none()
                    if existing:
                        job["message"] = f"Skipping {phone} (exists)"
                    else:
                        dst = SESSIONS_DIR / sf.name
                        shutil.copy2(sf, dst)
                        try:
                            user_info = await client_manager.verify_session(phone, proxy)
                            account = Account(
                                phone=phone,
                                name=f"{user_info['first_name']} {user_info['last_name']}".strip(),
                                username=user_info.get("username", ""),
                                session_file=phone,
                                proxy_id=proxy_id,
                                is_active=True,
                                status="active",
                            )
                            db.add(account)
                            await db.commit()
                            job["message"] = f"Added {user_info.get('username') or phone}"
                            await self._notify("account_added", {"phone": phone})
                        except Exception as e:
                            job["message"] = f"Failed {phone}: {str(e)[:30]}"
                    job["progress"] = i + 1

            job["status"] = "completed"
            job["message"] = f"Completed {job['progress']}/{len(session_files)}"
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)

    async def import_tdata(self, folder_path: str,
                           proxy_id: Optional[int] = None) -> str:
        job_id = _new_job(_import_jobs)
        asyncio.create_task(self._do_import_tdata(job_id, folder_path, proxy_id))
        return job_id

    async def _do_import_tdata(self, job_id: str, folder_path: str,
                               proxy_id: Optional[int]):
        job = _import_jobs[job_id]
        try:
            result = await _import_tdata_accounts(Path(folder_path), proxy_id)
            job["status"] = "completed"
            job["message"] = f"Imported {result.get('imported', 0)} accounts"
            job["progress"] = result.get("imported", 0)
            job["total"] = result.get("total", 0)
            await self._notify("tdata_import_completed", result)
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        for store in (_load_jobs, _import_jobs, _send_jobs, _scrape_jobs, _join_jobs):
            if job_id in store:
                return store[job_id]
        return None

    # ── Proxies ───────────────────────────────────────────────────────────────

    async def get_proxies(self) -> List[dict]:
        async with async_session() as db:
            result = await db.execute(select(Proxy).order_by(Proxy.created_at.desc()))
            return [self._ser_proxy(p) for p in result.scalars().all()]

    async def create_proxy(self, data: dict) -> dict:
        async with async_session() as db:
            proxy = Proxy(
                scheme=data.get("scheme", "socks5"),
                host=data["host"],
                port=data["port"],
                username=data.get("username") or "",
                password=data.get("password") or "",
                is_active=data.get("is_active", True),
            )
            db.add(proxy)
            await db.commit()
            await db.refresh(proxy)
            await self._notify("proxy_added", {"id": proxy.id})
            return self._ser_proxy(proxy)

    async def bulk_create_proxies(self, text: str) -> dict:
        """Parse multi-line proxy list and bulk-insert."""
        lines = text.strip().splitlines()
        imported = skipped = failed = 0
        async with async_session() as db:
            for line in lines:
                parsed = self._parse_proxy_line(line.strip())
                if parsed is None:
                    if line.strip():
                        failed += 1
                    continue
                existing = (await db.execute(
                    select(Proxy).where(
                        Proxy.host == parsed["host"],
                        Proxy.port == parsed["port"],
                        Proxy.scheme == parsed["scheme"],
                    )
                )).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue
                db.add(Proxy(**parsed))
                imported += 1
            if imported:
                await db.commit()
        return {"imported": imported, "skipped": skipped, "failed": failed}

    @staticmethod
    def _parse_proxy_line(line: str) -> Optional[dict]:
        # scheme://[user:pass@]host:port
        m = re.match(
            r'^(socks5|socks4|http|https)://(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$',
            line, re.IGNORECASE)
        if m:
            return {"scheme": m.group(1).lower(), "host": m.group(4),
                    "port": int(m.group(5)), "username": m.group(2) or "",
                    "password": m.group(3) or "", "is_active": True}
        # host:port:user:pass
        parts = line.split(":")
        if len(parts) == 4:
            try:
                return {"scheme": "socks5", "host": parts[0], "port": int(parts[1]),
                        "username": parts[2], "password": parts[3], "is_active": True}
            except ValueError:
                return None
        # host:port
        if len(parts) == 2:
            try:
                return {"scheme": "socks5", "host": parts[0], "port": int(parts[1]),
                        "username": "", "password": "", "is_active": True}
            except ValueError:
                return None
        return None

    async def test_proxy(self, proxy_id: int) -> dict:
        """Try opening a TCP connection to the proxy."""
        import asyncio
        async with async_session() as db:
            proxy = await db.get(Proxy, proxy_id)
            if not proxy:
                raise Exception("Proxy not found")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(proxy.host, proxy.port), timeout=8)
            writer.close()
            await writer.wait_closed()
            return {"ok": True, "message": f"Connected to {proxy.host}:{proxy.port}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    async def delete_proxy(self, proxy_id: int) -> bool:
        async with async_session() as db:
            proxy = await db.get(Proxy, proxy_id)
            if not proxy:
                raise Exception("Proxy not found")
            await db.delete(proxy)
            await db.commit()
            await self._notify("proxy_deleted", {"id": proxy_id})
            return True

    def _ser_proxy(self, p: Proxy) -> dict:
        return {"id": p.id, "scheme": p.scheme, "host": p.host, "port": p.port,
                "username": p.username or "", "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None}

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send_messages(self, data: dict) -> dict:
        """
        Start a bulk send job.  Returns {"job_id": ..., "status": "starting"}.

        data keys:
            account_ids     list[int]
            targets         list[str]   usernames / phone numbers
            message         str         plain text (used when no template)
            template_id     int | None
            delay_min       int         seconds
            delay_max       int         seconds
            mode            str         "sequential" | "round_robin"
            max_per_account int         0 = unlimited
            rotate_proxies  bool        only rotates on FloodWait, never overrides
                                        account's assigned proxy on normal errors
            campaign_id     int | None

        NOTE: Each account always uses its own assigned proxy.
              rotate_proxies only switches account when FloodWait occurs.
        """
        job_id = _new_job(_send_jobs, campaign_id=data.get("campaign_id"))
        _send_jobs[job_id]["total"] = len(data.get("targets", []))
        asyncio.create_task(self._do_send(job_id, data))
        return {"job_id": job_id, "status": "starting"}

    async def cancel_job(self, job_id: str) -> bool:
        for store in (_send_jobs, _scrape_jobs, _join_jobs):
            if job_id in store:
                store[job_id]["cancelled"] = True
                return True
        return False

    async def _do_send(self, job_id: str, data: dict):
        """
        Background bulk send task.

        Proxy policy (FIXED):
        ─────────────────────
        Each account ALWAYS uses its own assigned proxy (acc.proxy).
        We NEVER randomly swap an account's proxy from a global pool.

        The only exception is FloodWait with no available alternative account:
        in that case we wait and retry with the SAME account+proxy, or switch
        to a different account (with that account's own proxy).

        rotate_proxies flag is intentionally ignored for per-send rotation —
        it is kept in the API signature for compatibility only.
        """
        job = _send_jobs[job_id]

        account_ids  = data.get("account_ids", [])
        targets      = data.get("targets", [])
        message      = data.get("message", "")
        template_id  = data.get("template_id")
        delay_min    = data.get("delay_min", 5)
        delay_max    = data.get("delay_max", 15)
        mode         = data.get("mode", "sequential")
        max_per_acct = data.get("max_per_account", 0)
        campaign_id  = data.get("campaign_id")

        try:
            # ── Resolve template (text + media) ───────────────────────────────
            template_text: Optional[str] = None
            template_media_path: Optional[str] = None
            template_media_type: str = ""

            # template_media_files: list of (abs_path, media_type) for sending
            template_media_files: list[tuple[str, str]] = []

            if template_id:
                async with async_session() as db:
                    from sqlalchemy.orm import selectinload as _sil
                    result_t = await db.execute(
                        select(MessageTemplate)
                        .options(_sil(MessageTemplate.variants),
                                 _sil(MessageTemplate.media_files))
                        .where(MessageTemplate.id == template_id))
                    tmpl = result_t.scalar_one_or_none()
                    if tmpl:
                        template_text = _pick_template_text(tmpl, message)
                        # Load ALL media files from template (ordered)
                        for mf in (tmpl.media_files or []):
                            abs_p = (str(BASE_DIR / mf.file_path)
                                     if not os.path.isabs(mf.file_path)
                                     else mf.file_path)
                            if os.path.exists(abs_p):
                                template_media_files.append((abs_p, mf.media_type or "photo"))
                            else:
                                logger.warning("Template media missing: %s", abs_p)
                        # Backward compat: old single media_path column
                        if not template_media_files and tmpl.media_path:
                            abs_p = (str(BASE_DIR / tmpl.media_path)
                                     if not os.path.isabs(tmpl.media_path)
                                     else tmpl.media_path)
                            if os.path.exists(abs_p):
                                template_media_files.append(
                                    (abs_p, tmpl.media_type or "photo"))

            if not template_text and not message:
                job["status"] = "failed"
                job["message"] = "No message or template provided"
                return

            # Campaign-level media (if no template media)
            if not template_media_files:
                raw_mp = data.get("media_path") or ""
                raw_mt = data.get("media_type") or "photo"
                if raw_mp:
                    abs_p = str(BASE_DIR / raw_mp) if not os.path.isabs(raw_mp) else raw_mp
                    if os.path.exists(abs_p):
                        template_media_files.append((abs_p, raw_mt))
                    else:
                        logger.warning("Campaign media not found: %s", abs_p)

            # For backward compat, keep single-file vars too
            final_media_path = template_media_files[0][0] if template_media_files else ""
            final_media_type = template_media_files[0][1] if template_media_files else "photo"

            # ── Load accounts with their OWN proxies ──────────────────────────
            async with async_session() as db:
                result = await db.execute(
                    select(Account)
                    .options(selectinload(Account.proxy))
                    .where(Account.id.in_(account_ids), Account.is_active == True)
                )
                accounts = list(result.scalars().all())

            if not accounts:
                job["status"] = "failed"
                job["message"] = "No active accounts found"
                return

            # ── Connect every account using its OWN assigned proxy ────────────
            # Each entry: (Account, TelegramClient, assigned_proxy)
            # The proxy here is FIXED for this account — we never change it.
            clients: list[tuple[Account, Any, Optional[Proxy]]] = []
            for acc in accounts:
                assigned_proxy = acc.proxy   # the proxy assigned in edit_account
                proxy_label = f"{assigned_proxy.host}:{assigned_proxy.port}" if assigned_proxy else "direct"
                try:
                    client = await client_manager.get_client(
                        acc.id, acc.phone, assigned_proxy)
                    clients.append((acc, client, assigned_proxy))
                    async with async_session() as db:
                        db.add(Log(level="info", category="message", account_id=acc.id,
                                   message=f"Connected via {proxy_label}"))
                        await db.commit()
                except Exception as e:
                    logger.error("Account %s failed to connect via %s: %s",
                                 acc.phone, proxy_label, e)
                    async with async_session() as db:
                        db.add(Log(level="error", category="message", account_id=acc.id,
                                   message=f"Cannot connect via {proxy_label}: {e}"))
                        await db.commit()

            if not clients:
                job["status"] = "failed"
                job["message"] = "Could not connect any account. Check: 1) Session valid? 2) Proxy working?"
                async with async_session() as db:
                    db.add(Log(level="error", category="message",
                               message=f"Send job {job_id}: no accounts could connect"))
                    await db.commit()
                return

            job["status"] = "running"

            # ── BULK phone resolution before sending ──────────────────────────
            # Separate targets into phones and non-phones
            phone_targets   = [t for t in targets
                               if t.startswith("+") or
                               (t.lstrip("+").isdigit() and len(t) > 7)]
            direct_targets  = [t for t in targets if t not in phone_targets]

            # _resolved_map: original_target → resolved_entity (user_id or username)
            # None means "not on Telegram — skip"
            _resolved_map: dict[str, object] = {t: t for t in direct_targets}

            if phone_targets and clients:
                # Use first available client for phone resolution
                bulk_acc, bulk_client, _ = clients[0]
                job["message"] = f"Checking {len(phone_targets)} phone number(s) on Telegram…"

                try:
                    from pyrogram.types import InputPhoneContact as _IPC

                    # Step 1: Get all existing contacts first
                    logger.info("Fetching contacts list...")
                    all_contacts = await bulk_client.get_contacts()
                    
                    # Build phone → user_id map from existing contacts
                    contact_map: dict[str, int] = {}
                    for contact in all_contacts:
                        phone = getattr(contact, 'phone_number', None)
                        if phone:
                            digits = phone.lstrip('+').replace(' ', '')
                            contact_map[digits] = contact.id
                            # Also store with + prefix
                            contact_map['+' + digits] = contact.id
                    
                    logger.info("Loaded %d contacts from list", len(all_contacts))

                    for p in phone_targets:
                        phone_e164 = p if p.startswith("+") else f"+{p}"
                        digits = phone_e164.lstrip("+").replace(' ', '')
                        
                        # Step 2: Check if number exists in contacts
                        user_id = contact_map.get(digits) or contact_map.get(phone_e164)
                        
                        if user_id:
                            # ✅ Found in existing contacts!
                            logger.info("✅ %s found in contacts (user_id: %s)", p, user_id)
                            _resolved_map[p] = user_id
                            
                        else:
                            # Not in contacts - try to import
                            logger.info("→ %s not in contacts - attempting import...", p)
                            try:
                                import_result = await bulk_client.import_contacts([
                                    _IPC(phone=phone_e164, first_name="User", last_name="")
                                ])
                                
                                # Check if user was returned
                                if import_result.users:
                                    for u in import_result.users:
                                        u_phone = getattr(u, 'phone_number', None)
                                        if u_phone:
                                            u_digits = u_phone.lstrip('+').replace(' ', '')
                                            if u_digits == digits:
                                                user_id = u.id
                                                logger.info("✅ %s added via import (user_id: %s)", p, user_id)
                                                _resolved_map[p] = user_id
                                                break
                                
                                if not user_id:
                                    # Still not found - privacy settings may block
                                    logger.warning("❌ %s - import returned no match (privacy settings?)", p)
                                    _resolved_map[p] = phone_e164  # Try direct send
                                    
                            except Exception as import_err:
                                logger.error("❌ Error importing %s: %s", p, import_err)
                                _resolved_map[p] = phone_e164  # Try direct send

                    job["message"] = f"Resolved {len([t for t in _resolved_map if _resolved_map[t]])} / {len(phone_targets)} phone(s)"
                    logger.info("Phone resolution complete: %d to attempt", 
                               len([t for t in _resolved_map if _resolved_map[t]]))

                except Exception as bulk_err:
                    logger.error("Phone resolution failed: %s", bulk_err)
                    # Fallback: try direct send for all
                    for p in phone_targets:
                        _resolved_map[p] = p if p.startswith("+") else f"+{p}"

            # Effective targets = those that resolved successfully
            effective_targets = [t for t in targets if _resolved_map.get(t) is not None]
            job["total"] = len(effective_targets)
            # Pre-count phones not found as failed
            phones_not_found = [t for t in phone_targets if _resolved_map.get(t) is None]
            job["failed"] = len(phones_not_found)
            if phones_not_found:
                async with async_session() as db:
                    for p in phones_not_found:
                        db.add(FailedMessage(
                            campaign_id=campaign_id,
                            target=p,
                            message_text="",
                            error="Phone not registered on Telegram",
                        ))
                    await db.commit()

            account_counts: dict[int, int] = {acc.id: 0 for acc, _, _ in clients}
            blocked_until:  dict[int, float] = {}
            failed_targets: list[dict] = []

            for i, target in enumerate(effective_targets):
                if job.get("cancelled"):
                    job["status"] = "cancelled"
                    break

                # ── Pick account (round-robin / sequential) ───────────────────
                acc = client = cur_proxy = None
                for attempt in range(len(clients)):
                    if mode == "round_robin":
                        idx = (i + attempt) % len(clients)
                    else:
                        idx = attempt % len(clients)
                    c_acc, c_client, c_proxy = clients[idx]
                    if max_per_acct > 0 and account_counts[c_acc.id] >= max_per_acct:
                        continue
                    if c_acc.id in blocked_until and time.time() < blocked_until[c_acc.id]:
                        continue
                    blocked_until.pop(c_acc.id, None)
                    acc, client, cur_proxy = c_acc, c_client, c_proxy
                    break

                if not acc:
                    job["failed"] += 1
                    failed_targets.append({"target": target,
                                           "error": "All accounts at limit or flood-blocked"})
                    continue

                text = _resolve_message(template_text, message, {}, target)
                sent_ok = False

                # resolved_target set by bulk resolution above
                resolved_target = _resolved_map.get(target, target)
                if resolved_target is None:
                    # Phone not on Telegram — already counted in failed
                    continue

                for retry in range(3):
                    try:
                        # Reconnect if needed
                        if hasattr(client, 'is_connected') and not client.is_connected:
                            client = await client_manager.get_client(acc.id, acc.phone, cur_proxy)
                        elif callable(getattr(client, 'is_connected', None)) and not client.is_connected():
                            client = await client_manager.get_client(acc.id, acc.phone, cur_proxy)

                        # ── Send: text, single media, or media group ──────
                        if not template_media_files:
                            # Text only
                            await client.send_message(
                                chat_id=resolved_target, text=text)

                        elif len(template_media_files) == 1:
                            # Single media file
                            abs_p, mt = template_media_files[0]
                            mt = mt.lower()
                            if mt == "photo":
                                await client.send_photo(
                                    chat_id=resolved_target,
                                    photo=abs_p, caption=text)
                            elif mt == "video":
                                await client.send_video(
                                    chat_id=resolved_target,
                                    video=abs_p, caption=text)
                            elif mt == "audio":
                                await client.send_audio(
                                    chat_id=resolved_target,
                                    audio=abs_p, caption=text)
                            else:
                                await client.send_document(
                                    chat_id=resolved_target,
                                    document=abs_p, caption=text)

                        else:
                            # Multiple media files → send_media_group
                            # Caption goes on first item only
                            from pyrogram.types import (
                                InputMediaPhoto, InputMediaVideo,
                                InputMediaDocument, InputMediaAudio,
                            )
                            media_group = []
                            for idx, (abs_p, mt) in enumerate(template_media_files):
                                cap = text if idx == 0 else ""
                                mt  = mt.lower()
                                if mt == "photo":
                                    media_group.append(
                                        InputMediaPhoto(abs_p, caption=cap))
                                elif mt == "video":
                                    media_group.append(
                                        InputMediaVideo(abs_p, caption=cap))
                                elif mt == "audio":
                                    media_group.append(
                                        InputMediaAudio(abs_p, caption=cap))
                                else:
                                    media_group.append(
                                        InputMediaDocument(abs_p, caption=cap))
                            await client.send_media_group(
                                chat_id=resolved_target,
                                media=media_group)

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

                    except Exception as e:
                        err_lower = str(e).lower()

                        # ── PEER_ID_INVALID: Phone number not on Telegram ────────
                        if "peer_id_invalid" in err_lower:
                            logger.warning("❌ PEER_ID_INVALID for %s - number not on Telegram or contact not added", target)
                            # Mark as failed and skip retries
                            job["failed"] += 1
                            async with async_session() as db:
                                db.add(FailedMessage(
                                    campaign_id=campaign_id,
                                    account_id=acc.id if acc else None,
                                    target=target,
                                    message_text=text,
                                    error="PEER_ID_INVALID - Number not on Telegram or contact not added",
                                ))
                                await db.commit()
                            break  # Skip retries for this target

                        # ── FloodWait: block this account, try another ────────
                        if "flood" in err_lower:
                            import re as _re
                            m = _re.search(r'(\d+)', str(e))
                            wait_secs = min(int(m.group(1)), 120) if m else 60
                            blocked_until[acc.id] = time.time() + wait_secs

                            async with async_session() as db:
                                db.add(Log(level="warn", category="message", account_id=acc.id,
                                           message=f"FloodWait {wait_secs}s — blocked temporarily"))
                                await db.commit()

                            # Try switching to another account (each with its own proxy)
                            switched = False
                            for a2, c2, p2 in clients:
                                if a2.id != acc.id and a2.id not in blocked_until:
                                    if max_per_acct <= 0 or account_counts[a2.id] < max_per_acct:
                                        acc, client, cur_proxy = a2, c2, p2
                                        switched = True
                                        break
                            if not switched:
                                # No other account available — wait and retry same
                                await asyncio.sleep(min(wait_secs, 30))
                            # retry loop continues

                        # ── Account banned / deactivated ─────────────────────
                        elif any(x in err_lower for x in
                                 ("deactivated", "banned", "auth_key", "user_deactivated")):
                            async with async_session() as db:
                                acc_row = await db.get(Account, acc.id)
                                if acc_row:
                                    acc_row.status = "banned"
                                    acc_row.is_active = False
                                db.add(Log(level="error", category="message", account_id=acc.id,
                                           message="Account banned/deactivated"))
                                await db.commit()
                            clients = [(a, c, p) for a, c, p in clients if a.id != acc.id]
                            if not clients:
                                job["status"] = "failed"
                                job["message"] = "All accounts banned"
                                return
                            break  # move to next target

                        # ── Other errors: log clearly, retry with backoff ──────
                        else:
                            proxy_label = f"{cur_proxy.host}:{cur_proxy.port}" if cur_proxy else "direct"
                            err_msg = f"Send to {target} via {proxy_label} failed (retry {retry+1}/3): {e}"
                            logger.warning(err_msg)
                            async with async_session() as db:
                                db.add(Log(level="error", category="message", account_id=acc.id,
                                           message=err_msg))
                                await db.commit()
                            if retry < 2:
                                await asyncio.sleep(2 ** retry)  # 1s, 2s backoff
                            else:
                                break  # 3 retries exhausted

                if not sent_ok:
                    job["failed"] += 1
                    failed_targets.append({"target": target,
                                           "error": "failed after retries",
                                           "message_text": text})

                if i < len(targets) - 1 and not job.get("cancelled"):
                    await asyncio.sleep(random.uniform(delay_min, delay_max))

            # ── Save failed messages to DB ────────────────────────────────────
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
            job["message"] = f"Done — sent: {job['sent']}, failed: {job['failed']}"

        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)
            logger.exception("Send job %s failed: %s", job_id, e)
            # Also log to DB so user can see in Logs page
            try:
                async with async_session() as db:
                    db.add(Log(level="error", category="message",
                               message=f"Send job {job_id} crashed: {e}"))
                    await db.commit()
            except Exception as _log_err:
                logger.warning("Could not write crash log to DB: %s", _log_err)

    # ── Campaigns ─────────────────────────────────────────────────────────────

    async def get_campaigns(self) -> List[dict]:
        async with async_session() as db:
            result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
            return [self._ser_campaign(c) for c in result.scalars().all()]

    async def get_campaign(self, campaign_id: int) -> Optional[dict]:
        async with async_session() as db:
            c = await db.get(Campaign, campaign_id)
            return self._ser_campaign(c) if c else None

    async def create_campaign(self, data: dict) -> dict:
        async with async_session() as db:
            c = Campaign(
                name=data["name"],
                message_text=data.get("message_text", ""),
                account_ids=_json.dumps(data.get("account_ids", [])),
                targets=_json.dumps(data.get("targets", [])),
                peer_ids=_json.dumps(data.get("peer_ids", [])),
                template_id=data.get("template_id"),
                status="draft",
                delay_min=data.get("delay_min", 30),
                delay_max=data.get("delay_max", 60),
                max_per_account=data.get("max_per_account", 0),
                media_path=data.get("media_path", ""),
                media_type=data.get("media_type", ""),
                rotate_accounts=data.get("rotate_accounts", True),
                auto_retry=data.get("auto_retry", False),
            )
            db.add(c)
            await db.commit()
            await db.refresh(c)
            await self._notify("campaign_added", {"id": c.id, "name": c.name})
            return self._ser_campaign(c)

    async def update_campaign(self, campaign_id: int, data: dict) -> dict:
        async with async_session() as db:
            c = await db.get(Campaign, campaign_id)
            if not c:
                raise Exception("Campaign not found")
            for field in ("name", "message_text", "targets", "status",
                          "delay_min", "delay_max", "max_per_account",
                          "media_path", "media_type", "template_id",
                          "rotate_accounts", "auto_retry"):
                if field in data and data[field] is not None:
                    setattr(c, field, data[field])
            # JSON list fields
            if "account_ids" in data:
                c.account_ids = (_json.dumps(data["account_ids"])
                                 if isinstance(data["account_ids"], list)
                                 else data["account_ids"])
            if "peer_ids" in data:
                c.peer_ids = (_json.dumps(data["peer_ids"])
                              if isinstance(data["peer_ids"], list)
                              else data["peer_ids"])
            await db.commit()
            await db.refresh(c)
            await self._notify("campaign_updated", {"id": c.id})
            return self._ser_campaign(c)

    async def run_campaign(self, campaign_id: int) -> dict:
        """
        Start a campaign as a send job.

        Target resolution order:
          1. peer_ids → fetch all contact values from those peers
          2. targets  → manually saved targets list
          Fails clearly if neither is set.
        """
        async with async_session() as db:
            c = await db.get(Campaign, campaign_id)
            if not c:
                raise Exception("Campaign not found")

            account_ids = self._safe_json(c.account_ids)
            if not account_ids:
                raise Exception("Campaign has no accounts configured. Edit the campaign and select accounts.")

            # ── Resolve targets ───────────────────────────────────────────────
            targets: list[str] = []

            # 1. From peers (peer_ids column)
            peer_ids = self._safe_json(c.peer_ids)
            if peer_ids:
                for pid in peer_ids:
                    peer_targets = await self.get_peer_targets(pid)
                    targets.extend(peer_targets)
                targets = list(dict.fromkeys(targets))  # deduplicate
                logger.info("Campaign %s: loaded %d targets from %d peer(s)",
                            campaign_id, len(targets), len(peer_ids))

            # 2. Fallback: manual targets stored in campaign
            if not targets:
                targets = self._safe_json(c.targets)

            if not targets:
                raise Exception("Campaign has no targets. Add targets manually or assign a Peer in campaign settings.")

            # Check message/template
            if not c.message_text and not c.template_id:
                raise Exception("Campaign has no message or template. Edit the campaign and add a message.")

            c.status = "running"
            await db.commit()

        logger.info("Campaign %s starting: %d accounts, %d targets",
                    campaign_id, len(account_ids), len(targets))

        result = await self.send_messages({
            "account_ids":     account_ids,
            "targets":         targets,
            "message":         c.message_text or "",
            "template_id":     c.template_id,
            "media_path":      c.media_path or "",
            "media_type":      c.media_type or "photo",
            "delay_min":       c.delay_min,
            "delay_max":       c.delay_max,
            "mode":            "round_robin",
            "max_per_account": c.max_per_account,
            "rotate_proxies":  False,
            "auto_retry":      c.auto_retry,
            "campaign_id":     campaign_id,
        })

        job_id = result["job_id"]
        asyncio.create_task(self._watch_campaign_job(campaign_id, job_id))
        return result

    async def _watch_campaign_job(self, campaign_id: int, job_id: str):
        while True:
            await asyncio.sleep(2)
            job = _send_jobs.get(job_id)
            if not job:
                break
            if job["status"] in ("completed", "failed", "cancelled"):
                async with async_session() as db:
                    c = await db.get(Campaign, campaign_id)
                    if c:
                        c.status = job["status"]
                        await db.commit()
                break

    async def delete_campaign(self, campaign_id: int) -> bool:
        async with async_session() as db:
            c = await db.get(Campaign, campaign_id)
            if not c:
                raise Exception("Campaign not found")
            await db.delete(c)
            await db.commit()
            await self._notify("campaign_deleted", {"id": campaign_id})
            return True

    def _ser_campaign(self, c: Campaign) -> dict:
        return {
            "id":              c.id,
            "name":            c.name,
            "message_text":    c.message_text or "",
            "account_ids":     self._safe_json(c.account_ids),
            "targets":         self._safe_json(c.targets),
            "peer_ids":        self._safe_json(getattr(c, "peer_ids", "[]")),
            "template_id":     c.template_id,
            "status":          c.status or "draft",
            "delay_min":       c.delay_min or 30,
            "delay_max":       c.delay_max or 60,
            "max_per_account": c.max_per_account or 0,
            "media_path":      c.media_path or "",
            "media_type":      c.media_type or "",
            "rotate_accounts": bool(c.rotate_accounts),
            "auto_retry":      bool(c.auto_retry),
            "retry_count":     c.retry_count or 0,
            "max_retries":     c.max_retries or 3,
            "schedule_cron":   c.schedule_cron or "",
            "created_at":      c.created_at.isoformat() if c.created_at else None,
        }

    # ── Templates — see full implementation below (with variants/categories) ──────
    # ── Scraper ───────────────────────────────────────────────────────────────

    async def scrape_members(self, account_id: int, group: str,
                             limit: int = 0, filter_type: str = "all") -> str:
        job_id = _new_job(_scrape_jobs, group=group, members=[])
        asyncio.create_task(self._do_scrape(job_id, account_id, group, limit, filter_type))
        return job_id

    async def _do_scrape(self, job_id: str, account_id: int, group: str,
                         limit: int, filter_type: str):
        job = _scrape_jobs[job_id]
        try:
            async with async_session() as db:
                acc = await db.get(Account, account_id)
                if not acc:
                    raise Exception("Account not found")
                proxy = await db.get(Proxy, acc.proxy_id) if acc.proxy_id else None

            client = await client_manager.get_client(account_id, acc.phone, proxy)

            from services.scraper import scrape_members as _scrape
            members = await _scrape(client, group, limit, filter_type)
            job["status"] = "completed"
            job["members"] = members
            job["total"] = len(members)

            async with async_session() as db:
                db.add(Log(level="info", category="scrape", account_id=account_id,
                           message=f"Scraped {len(members)} from {group}"))
                await db.commit()

        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)
            logger.error("Scrape job %s failed: %s", job_id, e)

    async def join_groups(self, account_ids: list[int], groups: list[str],
                          delay_min: int = 10, delay_max: int = 30) -> str:
        job_id = _new_job(_join_jobs, total=len(groups), results=[])
        asyncio.create_task(self._do_join(job_id, account_ids, groups, delay_min, delay_max))
        return job_id

    async def _do_join(self, job_id: str, account_ids: list[int], groups: list[str],
                       delay_min: int, delay_max: int):
        job = _join_jobs[job_id]
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(Account).options(selectinload(Account.proxy))
                    .where(Account.id.in_(account_ids), Account.is_active == True))
                accounts = list(result.scalars().all())

            clients = []
            for acc in accounts:
                try:
                    c = await client_manager.get_client(acc.id, acc.phone, acc.proxy)
                    clients.append((acc, c))
                except Exception as _conn_err:
                    logger.error("Account %s failed to connect: %s", acc.id, _conn_err)

            if not clients:
                job["status"] = "failed"
                job["message"] = "Could not connect any account"
                return

            from services.scraper import join_group as _join
            for i, group in enumerate(groups):
                if job.get("cancelled"):
                    break
                acc, client = clients[i % len(clients)]
                res = await _join(client, group)
                job["results"].append({"group": group, **res})
                if res["ok"]:
                    job["sent"] += 1
                else:
                    job["failed"] += 1
                job["progress"] = i + 1

                async with async_session() as db:
                    lvl = "info" if res["ok"] else "error"
                    db.add(Log(level=lvl, category="scrape", account_id=acc.id,
                               message=f"{'Joined' if res['ok'] else 'Failed to join'} {group}"))
                    await db.commit()

                if i < len(groups) - 1:
                    await asyncio.sleep(random.uniform(delay_min, delay_max))

            job["status"] = "completed"
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        # FIX: SQLAlchemy async sessions do NOT support concurrent queries
        # on the same session (asyncio.gather with same db = crash).
        # Use ONE session, run queries SEQUENTIALLY — still fast for SQLite.
        async with async_session() as db:
            total_accounts  = (await db.scalar(select(func.count(Account.id)))) or 0
            active_accounts = (await db.scalar(
                select(func.count(Account.id)).where(Account.is_active == True))) or 0
            total_sent      = (await db.scalar(select(func.sum(Account.messages_sent)))) or 0
            total_campaigns = (await db.scalar(select(func.count(Campaign.id)))) or 0
            total_proxies   = (await db.scalar(select(func.count(Proxy.id)))) or 0
            total_templates = (await db.scalar(select(func.count(MessageTemplate.id)))) or 0

            camp_result = await db.execute(
                select(Campaign.status, func.count(Campaign.id))
                .group_by(Campaign.status))
            campaign_by_status = {s: c for s, c in camp_result.all()}

            accs_res = await db.execute(
                select(Account.id, Account.name, Account.phone, Account.messages_sent)
                .order_by(Account.created_at.desc()))
            per_account = [
                {"id": r.id, "name": r.name or r.phone,
                 "phone": r.phone, "sent": r.messages_sent or 0, "failed": 0}
                for r in accs_res.all()
            ]

            logs_res = await db.execute(
                select(Log).order_by(Log.created_at.desc()).limit(50))
            recent_logs = [
                {"id": l.id, "category": l.category or "general",
                 "level": l.level or "info", "message": l.message or "",
                 "created_at": l.created_at.isoformat() if l.created_at else None}
                for l in logs_res.scalars().all()
            ]

        success_rate = (
            f"{total_sent / max(total_sent, 1) * 100:.0f}%"
            if total_sent > 0 else "0%")

        return {
            "accounts": {"total": total_accounts, "active": active_accounts},
            "messages": {"sent": total_sent, "failed": 0, "total": total_sent},
            "success_rate": success_rate,
            "campaigns": {"total": total_campaigns, "by_status": campaign_by_status},
            "proxies":   total_proxies,
            "templates": total_templates,
            "scrape_ops": 0,
            "per_account": per_account,
            "recent_logs": recent_logs,
        }

    # ── Logs ──────────────────────────────────────────────────────────────────

    async def get_logs(self, category: Optional[str] = None, limit: int = 100) -> List[dict]:
        async with async_session() as db:
            q = select(Log).order_by(Log.created_at.desc()).limit(limit)
            if category:
                q = q.where(Log.category == category)
            result = await db.execute(q)
            return [{"id": l.id, "category": l.category or "general",
                     "level": l.level or "info", "message": l.message or "",
                     "created_at": l.created_at.isoformat() if l.created_at else None}
                    for l in result.scalars().all()]

    async def clear_logs(self, category: Optional[str] = None) -> dict:
        async with async_session() as db:
            q = sa_delete(Log)
            if category:
                q = q.where(Log.category == category)
            result = await db.execute(q)
            await db.commit()
            return {"deleted": result.rowcount}

    async def create_log(self, message: str, category: str = "general",
                         level: str = "info") -> dict:
        async with async_session() as db:
            log = Log(message=message, category=category, level=level)
            db.add(log)
            await db.commit()
            await db.refresh(log)
            await self._notify("log_added", {"id": log.id, "message": message, "level": level})
            return {"id": log.id, "message": message, "category": category, "level": level}

    # ── Settings ──────────────────────────────────────────────────────────────

    async def get_settings(self) -> dict:
        from core.config import get_settings as _get
        return _get()

    async def save_settings(self, settings: dict) -> dict:
        from core.config import _save_settings
        _save_settings(settings)
        return settings

    # ── Media ─────────────────────────────────────────────────────────────────

    async def save_media(self, file_path: str) -> str:
        """
        Copy media file to MEDIA_DIR.
        Returns path relative to BASE_DIR (e.g. "media/abc123.jpg").
        UI can resolve to absolute with: BASE_DIR / returned_path
        """
        src_p = Path(file_path)
        if not src_p.exists():
            raise Exception(f"File not found: {file_path}")
        MEDIA_DIR.mkdir(exist_ok=True)
        filename = f"{uuid.uuid4().hex}{src_p.suffix.lower()}"
        dst = MEDIA_DIR / filename
        shutil.copy2(src_p, dst)
        # Return relative path stored in DB
        return str(dst.relative_to(BASE_DIR)).replace("\\", "/")



    # ══════════════════════════════════════════════════════════════════════════
    # PEERS
    # ══════════════════════════════════════════════════════════════════════════

    async def get_peers(self) -> List[dict]:
        async with async_session() as db:
            # Single query: peers + contact counts via LEFT JOIN GROUP BY
            from sqlalchemy import outerjoin, case
            peers_q = await db.execute(select(Peer).order_by(Peer.created_at.desc()))
            peers = peers_q.scalars().all()
            if not peers:
                return []
            # Batch count in one query
            peer_ids = [p.id for p in peers]
            counts_q = await db.execute(
                select(Contact.peer_id, func.count(Contact.id).label("cnt"))
                .where(Contact.peer_id.in_(peer_ids))
                .group_by(Contact.peer_id)
            )
            count_map = {row.peer_id: row.cnt for row in counts_q.all()}
            return [{**self._ser_peer(p),
                     "contact_count": count_map.get(p.id, 0)}
                    for p in peers]

    async def get_peer(self, peer_id: int) -> Optional[dict]:
        async with async_session() as db:
            p = await db.get(Peer, peer_id)
            if not p:
                return None
            count = await db.scalar(
                select(func.count(Contact.id)).where(Contact.peer_id == peer_id))
            return {**self._ser_peer(p), "contact_count": count or 0}

    async def create_peer(self, data: dict) -> dict:
        async with async_session() as db:
            p = Peer(
                title=data["title"],
                description=data.get("description", ""),
                color=data.get("color", "#58A6FF"),
            )
            db.add(p)
            await db.commit()
            await db.refresh(p)
            await self._notify("peer_created", {"id": p.id, "title": p.title})
            return {**self._ser_peer(p), "contact_count": 0}

    async def update_peer(self, peer_id: int, data: dict) -> dict:
        async with async_session() as db:
            p = await db.get(Peer, peer_id)
            if not p:
                raise Exception("Peer not found")
            for field in ("title", "description", "color"):
                if field in data:
                    setattr(p, field, data[field])
            await db.commit()
            await db.refresh(p)
            count = await db.scalar(
                select(func.count(Contact.id)).where(Contact.peer_id == peer_id))
            return {**self._ser_peer(p), "contact_count": count or 0}

    async def delete_peer(self, peer_id: int) -> bool:
        async with async_session() as db:
            p = await db.get(Peer, peer_id)
            if not p:
                raise Exception("Peer not found")
            await db.delete(p)   # cascade deletes contacts
            await db.commit()
            await self._notify("peer_deleted", {"id": peer_id})
            return True

    def _ser_peer(self, p: Peer) -> dict:
        return {
            "id": p.id, "title": p.title,
            "description": p.description or "",
            "color": p.color or "#58A6FF",
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # CONTACTS
    # ══════════════════════════════════════════════════════════════════════════

    async def get_contacts(self, peer_id: int, status: Optional[str] = None,
                           search: Optional[str] = None,
                           limit: int = 500, offset: int = 0) -> List[dict]:
        async with async_session() as db:
            q = select(Contact).where(Contact.peer_id == peer_id)
            if status:
                q = q.where(Contact.status == status)
            if search:
                q = q.where(
                    (Contact.value.ilike(f"%{search}%")) |
                    (Contact.label.ilike(f"%{search}%"))
                )
            q = q.order_by(Contact.created_at.desc()).limit(limit).offset(offset)
            result = await db.execute(q)
            return [self._ser_contact(c) for c in result.scalars().all()]

    async def get_peer_contact_count(self, peer_id: int) -> dict:
        """Returns counts per status — single GROUP BY query."""
        async with async_session() as db:
            result = await db.execute(
                select(Contact.status, func.count(Contact.id).label("cnt"))
                .where(Contact.peer_id == peer_id)
                .group_by(Contact.status)
            )
            counts = {row.status: row.cnt for row in result.all()}
            all_statuses = ["pending", "sent", "failed", "invalid", "duplicate"]
            for s in all_statuses:
                counts.setdefault(s, 0)
            counts["total"] = sum(counts[s] for s in all_statuses)
            return counts

    async def bulk_import_contacts(self, peer_id: int, raw_text: str,
                                   fmt: str = "auto") -> dict:
        """
        Parse and bulk-insert contacts from raw text.

        fmt: "auto" | "phone" | "username" | "csv"

        CSV format: first column = value, second (optional) = label
        TXT format: one value per line
        """
        import csv, io, re

        async with async_session() as db:
            p = await db.get(Peer, peer_id)
            if not p:
                raise Exception("Peer not found")

        # ── Parse ─────────────────────────────────────────────────────────────
        entries: list[tuple[str, str]] = []  # (value, label)
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]

        for line in lines:
            # Try CSV (comma-separated)
            if "," in line:
                parts = [p.strip() for p in line.split(",", 1)]
                value = parts[0]
                label = parts[1] if len(parts) > 1 else ""
            else:
                value = line
                label = ""

            # Normalize value
            if value.startswith("@"):
                pass  # username — keep as is
            elif value.lstrip("+").isdigit() and len(value.lstrip("+")) >= 7:
                # Phone number — ensure + prefix
                if not value.startswith("+"):
                    value = f"+{value}"
            elif value.isdigit() and len(value) > 5:
                pass  # user_id
            else:
                continue  # skip unrecognizable

            if value:
                entries.append((value, label))

        if not entries:
            return {"imported": 0, "skipped": 0, "duplicates": 0, "total": len(lines)}

        # ── Get existing values for this peer (duplicate check) ───────────────
        async with async_session() as db:
            existing_result = await db.execute(
                select(Contact.value).where(Contact.peer_id == peer_id))
            existing_values = {row[0] for row in existing_result.all()}

        # ── Bulk insert ───────────────────────────────────────────────────────
        imported = duplicates = skipped = 0
        batch_size = 500

        async with async_session() as db:
            batch = []
            for value, label in entries:
                if value in existing_values:
                    duplicates += 1
                    continue
                existing_values.add(value)  # prevent same-batch duplicates
                batch.append(Contact(
                    peer_id=peer_id,
                    value=value,
                    label=label,
                    status="pending",
                ))
                imported += 1

                if len(batch) >= batch_size:
                    db.add_all(batch)
                    await db.commit()
                    batch = []

            if batch:
                db.add_all(batch)
                await db.commit()

        await self._notify("contacts_imported",
                           {"peer_id": peer_id, "count": imported})
        return {
            "imported": imported,
            "duplicates": duplicates,
            "skipped": skipped,
            "total": len(lines),
        }

    async def delete_contact(self, contact_id: int) -> bool:
        async with async_session() as db:
            c = await db.get(Contact, contact_id)
            if not c:
                raise Exception("Contact not found")
            await db.delete(c)
            await db.commit()
            return True

    async def clear_peer_contacts(self, peer_id: int,
                                   status_filter: Optional[str] = None) -> int:
        """Delete all (or filtered) contacts from a peer."""
        from sqlalchemy import delete as sa_delete
        async with async_session() as db:
            q = sa_delete(Contact).where(Contact.peer_id == peer_id)
            if status_filter:
                q = q.where(Contact.status == status_filter)
            result = await db.execute(q)
            await db.commit()
            return result.rowcount

    async def export_peer_contacts(self, peer_id: int,
                                    fmt: str = "txt") -> str:
        """Return contacts as a string (txt or csv)."""
        async with async_session() as db:
            result = await db.execute(
                select(Contact).where(Contact.peer_id == peer_id)
                .order_by(Contact.created_at))
            contacts = result.scalars().all()

        if fmt == "csv":
            lines = ["value,label,status"]
            for c in contacts:
                lines.append(f"{c.value},{c.label or ''},{c.status}")
        else:  # txt
            lines = [c.value for c in contacts]

        return "\n".join(lines)

    async def update_contact_status(self, contact_value: str,
                                     peer_id: int, status: str,
                                     resolved_id: Optional[int] = None):
        """Called after send to mark contact status."""
        async with async_session() as db:
            result = await db.execute(
                select(Contact).where(
                    Contact.peer_id == peer_id,
                    Contact.value == contact_value))
            contact = result.scalar_one_or_none()
            if contact:
                contact.status = status
                if resolved_id:
                    contact.resolved_id = resolved_id
                await db.commit()

    async def get_peer_targets(self, peer_id: int) -> List[str]:
        """Get all contact values from a peer for sending."""
        async with async_session() as db:
            result = await db.execute(
                select(Contact.value).where(
                    Contact.peer_id == peer_id,
                    Contact.status.notin_(["invalid", "duplicate"])))
            return [row[0] for row in result.all()]

    def _ser_contact(self, c: Contact) -> dict:
        return {
            "id": c.id, "peer_id": c.peer_id,
            "value": c.value, "label": c.label or "",
            "status": c.status, "resolved_id": c.resolved_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # TEMPLATE CATEGORIES
    # ══════════════════════════════════════════════════════════════════════════

    async def get_template_categories(self) -> List[dict]:
        async with async_session() as db:
            result = await db.execute(
                select(TemplateCategory).order_by(TemplateCategory.name))
            return [{"id": c.id, "name": c.name, "color": c.color}
                    for c in result.scalars().all()]

    async def create_template_category(self, name: str,
                                        color: str = "#3FB950") -> dict:
        async with async_session() as db:
            cat = TemplateCategory(name=name, color=color)
            db.add(cat)
            await db.commit()
            await db.refresh(cat)
            return {"id": cat.id, "name": cat.name, "color": cat.color}

    async def delete_template_category(self, cat_id: int) -> bool:
        async with async_session() as db:
            cat = await db.get(TemplateCategory, cat_id)
            if not cat:
                raise Exception("Category not found")
            # Unlink templates
            result = await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.category_id == cat_id))
            for t in result.scalars().all():
                t.category_id = None
            await db.delete(cat)
            await db.commit()
            return True

    # ══════════════════════════════════════════════════════════════════════════
    # TEMPLATES (upgraded)
    # ══════════════════════════════════════════════════════════════════════════

    async def get_templates(self) -> List[dict]:
        async with async_session() as db:
            from sqlalchemy.orm import selectinload as _sil
            result = await db.execute(
                select(MessageTemplate)
                .options(_sil(MessageTemplate.variants),
                         _sil(MessageTemplate.category),
                         _sil(MessageTemplate.media_files))
                .order_by(MessageTemplate.created_at.desc()))
            return [self._ser_template_full(t) for t in result.scalars().all()]

    async def create_template(self, data: dict) -> dict:
        from sqlalchemy.orm import selectinload as _sil
        async with async_session() as db:
            t = MessageTemplate(
                name=data["name"],
                text=data.get("text", ""),
                media_path=data.get("media_path") or "",   # backward compat
                media_type=data.get("media_type") or "",
                category_id=data.get("category_id"),
                use_variants=data.get("use_variants", False),
                variables_used=_json.dumps(data.get("variables_used", [])),
            )
            db.add(t)
            await db.flush()

            # Text variants
            for i, vtext in enumerate(data.get("variants", [])):
                if vtext.strip():
                    db.add(TemplateVariant(
                        template_id=t.id, text=vtext, order=i))

            # Media files (new multi-media system)
            for i, mf in enumerate(data.get("media_files", [])):
                fp = mf.get("file_path") or mf.get("path", "")
                mt = mf.get("media_type", "photo")
                if fp:
                    db.add(TemplateMedia(
                        template_id=t.id, file_path=fp,
                        media_type=mt, order=i))

            await db.commit()
            new_id = t.id

        async with async_session() as db:
            result = await db.execute(
                select(MessageTemplate)
                .options(_sil(MessageTemplate.variants),
                         _sil(MessageTemplate.category),
                         _sil(MessageTemplate.media_files))
                .where(MessageTemplate.id == new_id))
            t2 = result.scalar_one()
            return self._ser_template_full(t2)

    async def update_template(self, template_id: int, data: dict) -> dict:
        async with async_session() as db:
            from sqlalchemy.orm import selectinload as _sil
            result = await db.execute(
                select(MessageTemplate)
                .options(_sil(MessageTemplate.variants))
                .where(MessageTemplate.id == template_id))
            t = result.scalar_one_or_none()
            if not t:
                raise Exception("Template not found")

            for field in ("name", "text", "media_path", "media_type",
                          "category_id", "use_variants"):
                if field in data and data[field] is not None:
                    setattr(t, field, data[field])

            if "variables_used" in data:
                t.variables_used = _json.dumps(data["variables_used"])

            # Replace variants if provided
            if "variants" in data:
                for v in t.variants:
                    await db.delete(v)
                await db.flush()
                for i, vtext in enumerate(data["variants"]):
                    if vtext.strip():
                        db.add(TemplateVariant(
                            template_id=t.id, text=vtext, order=i))

            # Replace media files if provided
            if "media_files" in data:
                for mf in t.media_files:
                    await db.delete(mf)
                await db.flush()
                for i, mf in enumerate(data["media_files"]):
                    fp = mf.get("file_path") or mf.get("path", "")
                    mt = mf.get("media_type", "photo")
                    if fp:
                        db.add(TemplateMedia(
                            template_id=t.id, file_path=fp,
                            media_type=mt, order=i))

            await db.commit()
            new_id = t.id

        from sqlalchemy.orm import selectinload as _sil2
        async with async_session() as db:
            result = await db.execute(
                select(MessageTemplate)
                .options(_sil2(MessageTemplate.variants),
                         _sil2(MessageTemplate.category),
                         _sil2(MessageTemplate.media_files))
                .where(MessageTemplate.id == new_id))
            t2 = result.scalar_one()
            return self._ser_template_full(t2)

    async def delete_template(self, template_id: int) -> bool:
        async with async_session() as db:
            t = await db.get(MessageTemplate, template_id)
            if not t:
                raise Exception("Template not found")
            if t.media_path:
                p = MEDIA_DIR / t.media_path
                if p.exists():
                    p.unlink()
            await db.delete(t)
            await db.commit()
            return True

    async def preview_template(self, template_id: int,
                                sample_vars: dict) -> str:
        """Render template with sample variables for preview."""
        async with async_session() as db:
            from sqlalchemy.orm import selectinload as _sil
            result = await db.execute(
                select(MessageTemplate)
                .options(_sil(MessageTemplate.variants))
                .where(MessageTemplate.id == template_id))
            t = result.scalar_one_or_none()
            if not t:
                raise Exception("Template not found")

        text = _pick_template_text(t, "")
        if not text:
            return ""

        defaults = {
            "name": "Ahmed Ali",
            "username": "@ahmed_ali",
            "phone": "+923001234567",
            "custom_1": "Value1",
            "custom_2": "Value2",
        }
        variables = {**defaults, **sample_vars}
        for k, v in variables.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

    def _ser_template_full(self, t: MessageTemplate) -> dict:
        try:
            vars_used = _json.loads(t.variables_used) if t.variables_used else []
        except Exception:
            vars_used = []

        # Build media_files list from new TemplateMedia table
        mf_list = [
            {"id": mf.id, "file_path": mf.file_path,
             "media_type": mf.media_type or "photo", "order": mf.order}
            for mf in sorted(getattr(t, "media_files", []) or [],
                             key=lambda x: x.order)
        ]
        # Backward compat: show old single column if no multi-media rows
        if not mf_list and t.media_path:
            mf_list = [{"id": None, "file_path": t.media_path,
                        "media_type": t.media_type or "photo", "order": 0}]

        return {
            "id": t.id,
            "name": t.name,
            "text": t.text or "",
            "media_path": t.media_path or "",   # backward compat
            "media_type": t.media_type or "",
            "media_files": mf_list,             # NEW — ordered list
            "media_count": len(mf_list),
            "category_id": t.category_id,
            "category": ({"id": t.category.id, "name": t.category.name,
                          "color": t.category.color}
                         if t.category_id and t.category else None),
            "use_variants": t.use_variants,
            "variables_used": vars_used,
            "variants": [{"id": v.id, "text": v.text, "order": v.order}
                         for v in (t.variants or [])],
            "variant_count": len(t.variants or []),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
service_manager = ServiceManager()