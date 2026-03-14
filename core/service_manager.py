"""
Unified Service Manager - Direct access to backend services from UI
"""
import asyncio
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
from core.models import Account, Proxy, Campaign, MessageTemplate, Log, FailedMessage
from services.telegram import client_manager
from services.tdata_import import import_tdata_accounts as _import_tdata_accounts

logger = logging.getLogger(__name__)

# ── In-memory job tracking ───────────────────────────────────────────────────
_load_jobs:    dict[str, dict] = {}
_import_jobs:  dict[str, dict] = {}
_send_jobs:    dict[str, dict] = {}   # messaging jobs
_scrape_jobs:  dict[str, dict] = {}
_join_jobs:    dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _new_job(store: dict, **extra) -> str:
    job_id = str(uuid.uuid4())[:12]
    store[job_id] = {"status": "starting", "sent": 0, "failed": 0,
                     "total": 0, "progress": 0, "message": "", **extra}
    return job_id


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
            account_ids   list[int]
            targets       list[str]   usernames / phone numbers
            message       str         plain text (used when no template)
            template_id   int | None
            delay_min     int         seconds
            delay_max     int         seconds
            mode          str         "sequential" | "round_robin"
            max_per_account int       0 = unlimited
            rotate_proxies  bool
            campaign_id   int | None
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
        """Background send task — mirrors routers/messaging_telethon.py _send_bulk."""
        job = _send_jobs[job_id]

        account_ids    = data.get("account_ids", [])
        targets        = data.get("targets", [])
        message        = data.get("message", "")
        template_id    = data.get("template_id")
        delay_min      = data.get("delay_min", 5)
        delay_max      = data.get("delay_max", 15)
        mode           = data.get("mode", "sequential")
        max_per_acct   = data.get("max_per_account", 0)
        rotate_proxies = data.get("rotate_proxies", True)
        campaign_id    = data.get("campaign_id")

        try:
            # Resolve template text
            template_text: Optional[str] = None
            if template_id:
                async with async_session() as db:
                    tmpl = await db.get(MessageTemplate, template_id)
                    if tmpl:
                        template_text = tmpl.text

            if not template_text and not message:
                job["status"] = "failed"
                job["message"] = "No message or template provided"
                return

            async with async_session() as db:
                # Load active accounts with proxies
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

                # Load proxy pool for rotation
                all_proxies: list[Proxy] = []
                if rotate_proxies:
                    pr = await db.execute(select(Proxy).where(Proxy.is_active == True))
                    all_proxies = list(pr.scalars().all())

            proxy_pool_idx = 0

            # Connect clients
            clients: list[tuple[Account, Any, Optional[Proxy]]] = []
            for acc in accounts:
                try:
                    client = await client_manager.get_client(acc.id, acc.phone, acc.proxy)
                    clients.append((acc, client, acc.proxy))
                    async with async_session() as db:
                        db.add(Log(level="info", category="message", account_id=acc.id,
                                   message=f"Connected for send job {job_id}"))
                        await db.commit()
                except Exception as e:
                    logger.error("Failed to connect account %s: %s", acc.id, e)
                    async with async_session() as db:
                        db.add(Log(level="error", category="message", account_id=acc.id,
                                   message=f"Failed to connect: {e}"))
                        await db.commit()

            if not clients:
                job["status"] = "failed"
                job["message"] = "Could not connect any account"
                return

            job["status"] = "running"
            job["total"] = len(targets)

            account_counts: dict[int, int] = {acc.id: 0 for acc, _, _ in clients}
            blocked_until:  dict[int, float] = {}
            failed_targets: list[dict] = []

            for i, target in enumerate(targets):
                if job.get("cancelled"):
                    job["status"] = "cancelled"
                    break

                # Pick account
                acc = client = cur_proxy = None
                for attempt in range(len(clients)):
                    idx = ((i + attempt) % len(clients)) if mode == "round_robin" else (attempt % len(clients))
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
                    failed_targets.append({"target": target, "error": "All accounts at limit or blocked"})
                    continue

                text = _resolve_message(template_text, message, {}, target)
                sent_ok = False

                for retry in range(3):
                    try:
                        await client.send_message(target, text)
                        sent_ok = True
                        job["sent"] += 1
                        account_counts[acc.id] += 1
                        async with async_session() as db:
                            acc_row = await db.get(Account, acc.id)
                            if acc_row:
                                acc_row.messages_sent = (acc_row.messages_sent or 0) + 1
                            db.add(Log(level="info", category="message", account_id=acc.id,
                                       message=f"Sent to {target}"))
                            await db.commit()
                        break

                    except Exception as e:
                        err = str(e).lower()
                        if "flood" in err:
                            # Parse wait seconds from error message if possible
                            wait = 60
                            import re as _re
                            m = _re.search(r'(\d+)', str(e))
                            if m:
                                wait = min(int(m.group(1)), 120)
                            blocked_until[acc.id] = time.time() + wait
                            # Try switching account
                            switched = False
                            for a2, c2, p2 in clients:
                                if a2.id != acc.id and a2.id not in blocked_until:
                                    acc, client, cur_proxy = a2, c2, p2
                                    switched = True
                                    break
                            if not switched:
                                await asyncio.sleep(min(wait, 30))
                        elif any(x in err for x in ("deactivated", "banned", "auth_key")):
                            async with async_session() as db:
                                acc_row = await db.get(Account, acc.id)
                                if acc_row:
                                    acc_row.status = "banned"
                                    acc_row.is_active = False
                                db.add(Log(level="error", category="message", account_id=acc.id,
                                           message=f"Account banned/deactivated during send"))
                                await db.commit()
                            clients = [(a, c, p) for a, c, p in clients if a.id != acc.id]
                            if not clients:
                                job["status"] = "failed"
                                job["message"] = "All accounts banned"
                                return
                            break
                        else:
                            # Generic error — try proxy rotation
                            if rotate_proxies and all_proxies and retry < 2:
                                proxy_pool_idx = (proxy_pool_idx + 1) % len(all_proxies)
                                new_proxy = all_proxies[proxy_pool_idx]
                                try:
                                    client = await client_manager.get_client(
                                        acc.id, acc.phone, new_proxy)
                                    cur_proxy = new_proxy
                                    clients = [(a, client if a.id == acc.id else c,
                                                new_proxy if a.id == acc.id else p)
                                               for a, c, p in clients]
                                except Exception:
                                    pass
                            else:
                                async with async_session() as db:
                                    db.add(Log(level="error", category="message", account_id=acc.id,
                                               message=f"Failed to send to {target}: {e}"))
                                    await db.commit()
                                break

                if not sent_ok:
                    job["failed"] += 1
                    failed_targets.append({"target": target, "error": "retries exhausted",
                                           "message_text": text})

                if i < len(targets) - 1 and not job.get("cancelled"):
                    await asyncio.sleep(random.uniform(delay_min, delay_max))

            # Save failed messages
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
            logger.exception("Send job %s failed", job_id)

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
            import json
            c = Campaign(
                name=data["name"],
                message_text=data.get("message_text", ""),
                account_ids=json.dumps(data.get("account_ids", [])),
                targets=json.dumps(data.get("targets", [])),
                status="draft",
                delay_min=data.get("delay_min", 30),
                delay_max=data.get("delay_max", 60),
                max_per_account=data.get("max_per_account", 50),
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
                          "media_path", "media_type"):
                if field in data:
                    setattr(c, field, data[field])
            await db.commit()
            await db.refresh(c)
            await self._notify("campaign_updated", {"id": c.id})
            return self._ser_campaign(c)

    async def run_campaign(self, campaign_id: int) -> dict:
        """Start a campaign as a send job and return job info."""
        import json
        async with async_session() as db:
            c = await db.get(Campaign, campaign_id)
            if not c:
                raise Exception("Campaign not found")
            account_ids = json.loads(c.account_ids) if c.account_ids else []
            targets     = json.loads(c.targets)     if c.targets     else []
            if not account_ids or not targets:
                raise Exception("Campaign has no accounts or targets configured")
            c.status = "running"
            await db.commit()

        result = await self.send_messages({
            "account_ids":     account_ids,
            "targets":         targets,
            "message":         c.message_text or "",
            "template_id":     c.template_id,
            "delay_min":       c.delay_min,
            "delay_max":       c.delay_max,
            "mode":            "round_robin",
            "max_per_account": c.max_per_account,
            "rotate_proxies":  c.rotate_proxies,
            "auto_retry":      c.auto_retry,
            "campaign_id":     campaign_id,
        })

        # When the job completes, update campaign status
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
        import json
        return {
            "id": c.id, "name": c.name,
            "message_text": c.message_text or "",
            "account_ids": json.loads(c.account_ids) if c.account_ids else [],
            "targets": json.loads(c.targets) if c.targets else [],
            "status": c.status or "draft",
            "delay_min": c.delay_min or 30,
            "delay_max": c.delay_max or 60,
            "max_per_account": c.max_per_account or 50,
            "media_path": c.media_path or "",
            "media_type": c.media_type or "",
            "rotate_accounts": c.rotate_accounts,
            "auto_retry": c.auto_retry,
            "retry_count": c.retry_count or 0,
            "max_retries": c.max_retries or 3,
            "schedule_cron": c.schedule_cron or "",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    # ── Templates ─────────────────────────────────────────────────────────────

    async def get_templates(self) -> List[dict]:
        async with async_session() as db:
            result = await db.execute(
                select(MessageTemplate).order_by(MessageTemplate.created_at.desc()))
            return [self._ser_template(t) for t in result.scalars().all()]

    async def create_template(self, data: dict) -> dict:
        async with async_session() as db:
            t = MessageTemplate(
                name=data["name"],
                text=data.get("text", ""),
                media_path=data.get("media_path") or "",
                media_type=data.get("media_type") or "",
            )
            db.add(t)
            await db.commit()
            await db.refresh(t)
            return self._ser_template(t)

    async def update_template(self, template_id: int, data: dict) -> dict:
        async with async_session() as db:
            t = await db.get(MessageTemplate, template_id)
            if not t:
                raise Exception("Template not found")
            for field in ("name", "text", "media_path", "media_type"):
                if field in data and data[field] is not None:
                    setattr(t, field, data[field])
            await db.commit()
            await db.refresh(t)
            return self._ser_template(t)

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

    def _ser_template(self, t: MessageTemplate) -> dict:
        return {"id": t.id, "name": t.name, "text": t.text or "",
                "media_path": t.media_path or "", "media_type": t.media_type or "",
                "created_at": t.created_at.isoformat() if t.created_at else None}

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
                except Exception:
                    pass

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
        async with async_session() as db:
            total_accounts  = await db.scalar(select(func.count(Account.id))) or 0
            active_accounts = await db.scalar(
                select(func.count(Account.id)).where(Account.is_active == True)) or 0
            total_sent      = await db.scalar(select(func.sum(Account.messages_sent))) or 0
            total_campaigns = await db.scalar(select(func.count(Campaign.id))) or 0
            total_proxies   = await db.scalar(select(func.count(Proxy.id))) or 0
            total_templates = await db.scalar(select(func.count(MessageTemplate.id))) or 0

            camp_result = await db.execute(
                select(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status))
            campaign_by_status = {s: c for s, c in camp_result.all()}

            per_account = []
            for acc in (await db.execute(select(Account))).scalars().all():
                per_account.append({
                    "id": acc.id, "name": acc.name or acc.phone,
                    "phone": acc.phone, "sent": acc.messages_sent or 0, "failed": 0,
                })

            logs_result = await db.execute(
                select(Log).order_by(Log.created_at.desc()).limit(50))
            recent_logs = [
                {"id": l.id, "category": l.category or "general",
                 "level": l.level or "info", "message": l.message or "",
                 "created_at": l.created_at.isoformat() if l.created_at else None}
                for l in logs_result.scalars().all()
            ]

            total_msgs = total_sent
            success_rate = "100%" if total_msgs > 0 else "0%"

            return {
                "accounts": {"total": total_accounts, "active": active_accounts},
                "messages": {"sent": total_sent, "failed": 0, "total": total_msgs},
                "success_rate": success_rate,
                "campaigns": {"total": total_campaigns, "by_status": campaign_by_status},
                "proxies": total_proxies,
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
        src = Path(file_path)
        if not src.exists():
            raise Exception("File not found")
        MEDIA_DIR.mkdir(exist_ok=True)
        filename = f"{uuid.uuid4().hex}{src.suffix.lower()}"
        dst = MEDIA_DIR / filename
        shutil.copy2(src, dst)
        return str(dst.relative_to(BASE_DIR))


# ── Singleton ─────────────────────────────────────────────────────────────────
service_manager = ServiceManager()
