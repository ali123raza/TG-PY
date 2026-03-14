"""
Unified Service Manager - Direct access to backend services from UI
Replaces the FastAPI layer with direct function calls for realtime data sharing
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import SESSIONS_DIR, BASE_DIR, MEDIA_DIR
from core.database import async_session, init_db
from core.models import Account, Proxy, Campaign, MessageTemplate, Log, FailedMessage
from services.telegram import client_manager
from services.tdata_import import import_tdata_accounts as _import_tdata_accounts

logger = logging.getLogger(__name__)

# In-memory job tracking
_load_jobs: dict[str, dict] = {}
_import_jobs: dict[str, dict] = {}

class ServiceManager:
    """Central service manager for direct backend access from UI"""
    
    def __init__(self):
        self._db_session: Optional[AsyncSession] = None
        self._listeners: List[callable] = []  # For realtime updates
        
    async def init(self):
        """Initialize database"""
        await init_db()
        
    def add_listener(self, callback: callable):
        """Add a listener for realtime updates"""
        self._listeners.append(callback)
        
    def remove_listener(self, callback: callable):
        """Remove a listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    async def _notify(self, event: str, data: dict = None):
        """Notify all listeners of an event"""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event, data)
                else:
                    listener(event, data)
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    # ========== Accounts ==========
    
    async def login_start(self, phone: str, proxy_id: Optional[int] = None) -> dict:
        """Start login flow - returns phone_code_hash"""
        async with async_session() as db:
            proxy = None
            if proxy_id:
                proxy = await db.get(Proxy, proxy_id)
            try:
                phone_code_hash = await client_manager.start_login(phone, proxy)
                return {"phone_code_hash": phone_code_hash, "status": "code_sent"}
            except Exception as e:
                logger.error(f"Login start failed: {e}")
                raise Exception(str(e))
    
    async def login_complete(self, phone: str, code: str, phone_code_hash: str, 
                            password: Optional[str] = None, proxy_id: Optional[int] = None) -> dict:
        """Complete OTP login"""
        async with async_session() as db:
            proxy = None
            if proxy_id:
                proxy = await db.get(Proxy, proxy_id)
            try:
                user_info = await client_manager.complete_login(phone, code, phone_code_hash, password)
            except ValueError as e:
                raise Exception(str(e))
            except Exception as e:
                raise Exception(str(e))

            existing = (await db.execute(select(Account).where(Account.phone == phone))).scalar_one_or_none()
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
            return {"id": account.id, "phone": account.phone, "name": account.name, "username": account.username}
    
    async def get_accounts(self) -> List[dict]:
        """Get all accounts"""
        async with async_session() as db:
            result = await db.execute(select(Account).order_by(Account.created_at.desc()))
            accounts = result.scalars().all()
            return [self._serialize_account(a) for a in accounts]
    
    async def get_account(self, account_id: int) -> Optional[dict]:
        """Get single account by ID"""
        async with async_session() as db:
            account = await db.get(Account, account_id)
            if account:
                return self._serialize_account(account)
            return None
    
    async def update_account(self, account_id: int, data: dict) -> dict:
        """Update account"""
        async with async_session() as db:
            account = await db.get(Account, account_id)
            if not account:
                raise Exception("Account not found")
            
            if "name" in data and data["name"] is not None:
                account.name = data["name"]
            if "proxy_id" in data:
                account.proxy_id = data["proxy_id"]
            if "is_active" in data and data["is_active"] is not None:
                account.is_active = data["is_active"]
                
            await db.commit()
            await db.refresh(account)
            await self._notify("account_updated", {"id": account.id})
            return self._serialize_account(account)
    
    async def delete_account(self, account_id: int) -> bool:
        """Delete account"""
        async with async_session() as db:
            account = await db.get(Account, account_id)
            if not account:
                raise Exception("Account not found")
            
            # Delete session file if exists
            if account.session_file:
                session_path = SESSIONS_DIR / f"{account.session_file}.session"
                if session_path.exists():
                    session_path.unlink()
                    # Also delete session journal if exists
                    journal_path = SESSIONS_DIR / f"{account.session_file}.session-journal"
                    if journal_path.exists():
                        journal_path.unlink()
            
            await db.delete(account)
            await db.commit()
            await self._notify("account_deleted", {"id": account_id})
            return True
    
    async def check_account_health(self, account_id: int) -> dict:
        """Check if account session is valid"""
        async with async_session() as db:
            account = await db.get(Account, account_id)
            if not account:
                raise Exception("Account not found")
            
            proxy = None
            if account.proxy_id:
                proxy = await db.get(Proxy, account.proxy_id)
            
            try:
                user_info = await client_manager.verify_session(account.phone, proxy)
                account.status = "active"
                account.name = f"{user_info['first_name']} {user_info['last_name']}".strip()
                account.username = user_info["username"]
                await db.commit()
                return {"status": "ok", "info": user_info}
            except Exception as e:
                account.status = "error"
                await db.commit()
                return {"status": "error", "error": str(e)}
    
    async def check_all_accounts_health(self) -> dict:
        """Check health of all accounts"""
        accounts = await self.get_accounts()
        results = {}
        for acc in accounts:
            try:
                results[acc["id"]] = await self.check_account_health(acc["id"])
            except Exception as e:
                results[acc["id"]] = {"status": "error", "error": str(e)}
        return results
    
    def _serialize_account(self, a: Account) -> dict:
        """Serialize account to dict"""
        return {
            "id": a.id, 
            "phone": a.phone, 
            "name": a.name or "", 
            "username": a.username or "",
            "proxy_id": a.proxy_id, 
            "is_active": a.is_active, 
            "status": a.status or "unknown",
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "messages_sent": a.messages_sent or 0,
            "messages_failed": 0,  # Account model doesn't have messages_failed field
        }
    
    # ========== Proxies ==========
    
    async def get_proxies(self) -> List[dict]:
        """Get all proxies"""
        async with async_session() as db:
            result = await db.execute(select(Proxy).order_by(Proxy.created_at.desc()))
            proxies = result.scalars().all()
            return [{"id": p.id, "scheme": p.scheme, "host": p.host, "port": p.port,
                     "username": p.username, "is_active": p.is_active,
                     "created_at": p.created_at.isoformat() if p.created_at else None} for p in proxies]
    
    async def create_proxy(self, data: dict) -> dict:
        """Create new proxy"""
        async with async_session() as db:
            proxy = Proxy(
                scheme=data.get("scheme", "socks5"),
                host=data["host"],
                port=data["port"],
                username=data.get("username"),
                password=data.get("password"),
                is_active=data.get("is_active", True)
            )
            db.add(proxy)
            await db.commit()
            await db.refresh(proxy)
            await self._notify("proxy_added", {"id": proxy.id})
            return {"id": proxy.id, "scheme": proxy.scheme, "host": proxy.host, 
                    "port": proxy.port, "is_active": proxy.is_active}
    
    async def delete_proxy(self, proxy_id: int) -> bool:
        """Delete proxy"""
        async with async_session() as db:
            proxy = await db.get(Proxy, proxy_id)
            if not proxy:
                raise Exception("Proxy not found")
            await db.delete(proxy)
            await db.commit()
            await self._notify("proxy_deleted", {"id": proxy_id})
            return True
    
    # ========== Campaigns ==========
    
    async def get_campaigns(self) -> List[dict]:
        """Get all campaigns"""
        async with async_session() as db:
            result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
            campaigns = result.scalars().all()
            return [self._serialize_campaign(c) for c in campaigns]
    
    async def get_campaign(self, campaign_id: int) -> Optional[dict]:
        """Get single campaign"""
        async with async_session() as db:
            campaign = await db.get(Campaign, campaign_id)
            if campaign:
                return self._serialize_campaign(campaign)
            return None
    
    async def create_campaign(self, data: dict) -> dict:
        """Create new campaign"""
        async with async_session() as db:
            campaign = Campaign(
                name=data["name"],
                message_text=data.get("message_text", ""),
                targets=data.get("targets", ""),
                status="pending",
                delay_min=data.get("delay_min", 30),
                delay_max=data.get("delay_max", 60),
                max_per_account=data.get("max_per_account", 50),
                media_path=data.get("media_path", ""),
                media_type=data.get("media_type", ""),
            )
            db.add(campaign)
            await db.commit()
            await db.refresh(campaign)
            await self._notify("campaign_added", {"id": campaign.id, "name": campaign.name})
            return self._serialize_campaign(campaign)
    
    async def update_campaign(self, campaign_id: int, data: dict) -> dict:
        """Update campaign"""
        async with async_session() as db:
            campaign = await db.get(Campaign, campaign_id)
            if not campaign:
                raise Exception("Campaign not found")
            
            for field in ["name", "message_text", "targets", "status", 
                         "delay_min", "delay_max", "max_per_account", "media_path", "media_type"]:
                if field in data:
                    setattr(campaign, field, data[field])
                    
            await db.commit()
            await db.refresh(campaign)
            await self._notify("campaign_updated", {"id": campaign.id})
            return self._serialize_campaign(campaign)
    
    async def delete_campaign(self, campaign_id: int) -> bool:
        """Delete campaign"""
        async with async_session() as db:
            campaign = await db.get(Campaign, campaign_id)
            if not campaign:
                raise Exception("Campaign not found")
            await db.delete(campaign)
            await db.commit()
            await self._notify("campaign_deleted", {"id": campaign_id})
            return True
    
    def _serialize_campaign(self, c: Campaign) -> dict:
        """Serialize campaign to dict"""
        return {
            "id": c.id,
            "name": c.name,
            "message_text": c.message_text or "",
            "targets": c.targets or "",
            "status": c.status or "pending",
            "delay_min": c.delay_min or 30,
            "delay_max": c.delay_max or 60,
            "max_per_account": c.max_per_account or 50,
            "media_path": c.media_path or "",
            "media_type": c.media_type or "",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
    
    # ========== Templates ==========
    
    async def get_templates(self) -> List[dict]:
        """Get all templates"""
        async with async_session() as db:
            result = await db.execute(select(MessageTemplate).order_by(MessageTemplate.created_at.desc()))
            templates = result.scalars().all()
            return [{"id": t.id, "name": t.name, "text": t.text or "",
                     "media_path": t.media_path or "", "media_type": t.media_type or "",
                     "created_at": t.created_at.isoformat() if t.created_at else None} for t in templates]
    
    async def create_template(self, data: dict) -> dict:
        """Create new template"""
        async with async_session() as db:
            template = MessageTemplate(
                name=data["name"],
                text=data.get("text", ""),
                media_path=data.get("media_path", ""),
                media_type=data.get("media_type", ""),
            )
            db.add(template)
            await db.commit()
            await db.refresh(template)
            return {"id": template.id, "name": template.name, "text": template.text or "",
                    "media_path": template.media_path or "", "media_type": template.media_type or ""}
    
    async def delete_template(self, template_id: int) -> bool:
        """Delete template"""
        async with async_session() as db:
            template = await db.get(MessageTemplate, template_id)
            if not template:
                raise Exception("Template not found")
            await db.delete(template)
            await db.commit()
            return True
    
    # ========== Stats ==========
    
    async def get_stats(self) -> dict:
        """Get dashboard statistics"""
        async with async_session() as db:
            # Count accounts
            total_accounts = await db.scalar(select(func.count(Account.id)))
            active_accounts = await db.scalar(select(func.count(Account.id)).where(Account.is_active == True))
            
            # Count messages
            total_sent = await db.scalar(select(func.sum(Account.messages_sent)))
            total_failed = 0  # Account model doesn't have messages_failed field
            
            # Count campaigns by status
            from sqlalchemy import func as sa_func
            campaign_counts = await db.execute(
                select(Campaign.status, sa_func.count(Campaign.id)).group_by(Campaign.status)
            )
            campaign_by_status = {status: count for status, count in campaign_counts.all()}
            total_campaigns = sum(campaign_by_status.values())
            
            # Count proxies
            total_proxies = await db.scalar(select(func.count(Proxy.id)))
            
            # Count templates
            total_templates = await db.scalar(select(func.count(MessageTemplate.id)))
            
            # Per-account stats
            accounts_result = await db.execute(select(Account))
            per_account = []
            for acc in accounts_result.scalars().all():
                per_account.append({
                    "id": acc.id,
                    "name": acc.name or acc.phone,
                    "phone": acc.phone,
                    "sent": acc.messages_sent or 0,
                    "failed": 0,  # Account model doesn't have messages_failed
                })
            
            # Recent logs
            logs_result = await db.execute(
                select(Log).order_by(Log.created_at.desc()).limit(50)
            )
            recent_logs = [{"id": l.id, "category": l.category or "general", "level": l.level or "info",
                           "message": l.message or "", "created_at": l.created_at.isoformat() if l.created_at else None}
                          for l in logs_result.scalars().all()]
            
            total_messages = (total_sent or 0) + (total_failed or 0)
            success_rate = round((total_sent or 0) / total_messages * 100, 1) if total_messages > 0 else 0
            
            return {
                "accounts": {"total": total_accounts or 0, "active": active_accounts or 0},
                "messages": {"sent": total_sent or 0, "failed": total_failed or 0, "total": total_messages},
                "success_rate": f"{success_rate}%",
                "campaigns": {"total": total_campaigns, "by_status": campaign_by_status},
                "proxies": total_proxies or 0,
                "templates": total_templates or 0,
                "scrape_ops": 0,  # TODO: Implement scrape ops tracking
                "per_account": per_account,
                "recent_logs": recent_logs,
            }
    
    # ========== Logs ==========
    
    async def get_logs(self, category: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Get logs with optional filtering"""
        async with async_session() as db:
            query = select(Log).order_by(Log.created_at.desc()).limit(limit)
            if category:
                query = query.where(Log.category == category)
            result = await db.execute(query)
            return [{"id": l.id, "category": l.category or "general", "level": l.level or "info",
                    "message": l.message or "", "created_at": l.created_at.isoformat() if l.created_at else None}
                   for l in result.scalars().all()]
    
    async def create_log(self, message: str, category: str = "general", level: str = "info") -> dict:
        """Create a new log entry"""
        async with async_session() as db:
            log = Log(message=message, category=category, level=level)
            db.add(log)
            await db.commit()
            await db.refresh(log)
            await self._notify("log_added", {"id": log.id, "message": message, "level": level})
            return {"id": log.id, "message": message, "category": category, "level": level}
    
    # ========== Settings ==========
    
    async def get_settings(self) -> dict:
        """Get application settings"""
        from core.config import get_settings as _get_settings
        return _get_settings()
    
    async def save_settings(self, settings: dict) -> dict:
        """Save application settings"""
        from core.config import _save_settings
        _save_settings(settings)
        return settings
    
    # ========== File Operations ==========
    
    async def save_media(self, file_path: str) -> str:
        """Save media file and return relative path"""
        import shutil
        import uuid
        
        src = Path(file_path)
        if not src.exists():
            raise Exception("File not found")
        
        ext = src.suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        dst = MEDIA_DIR / filename
        
        MEDIA_DIR.mkdir(exist_ok=True)
        shutil.copy2(src, dst)
        
        return str(dst.relative_to(BASE_DIR))
    
    async def load_sessions_from_folder(self, folder_path: str, proxy_id: Optional[int] = None) -> str:
        """Start loading sessions from folder - returns job_id"""
        import uuid
        job_id = str(uuid.uuid4())
        
        _load_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "total": 0,
            "message": "Starting..."
        }
        
        # Start in background
        asyncio.create_task(self._do_load_sessions(job_id, folder_path, proxy_id))
        return job_id
    
    async def _do_load_sessions(self, job_id: str, folder_path: str, proxy_id: Optional[int]):
        """Background task to load sessions"""
        try:
            folder = Path(folder_path)
            session_files = list(folder.glob("*.session"))
            
            _load_jobs[job_id]["total"] = len(session_files)
            
            async with async_session() as db:
                proxy = None
                if proxy_id:
                    proxy = await db.get(Proxy, proxy_id)
                
                for i, session_file in enumerate(session_files):
                    try:
                        phone = session_file.stem
                        
                        # Check if account exists
                        existing = (await db.execute(
                            select(Account).where(Account.phone == phone)
                        )).scalar_one_or_none()
                        
                        if existing:
                            _load_jobs[job_id]["message"] = f"Skipping {phone} (exists)"
                        else:
                            # Copy session file
                            dst = SESSIONS_DIR / session_file.name
                            import shutil
                            shutil.copy2(session_file, dst)
                            
                            # Verify and create account
                            try:
                                user_info = await client_manager.verify_session(phone, proxy)
                                
                                account = Account(
                                    phone=phone,
                                    name=f"{user_info['first_name']} {user_info['last_name']}".strip(),
                                    username=user_info["username"],
                                    session_file=phone,
                                    proxy_id=proxy_id,
                                    is_active=True,
                                    status="active",
                                )
                                db.add(account)
                                await db.commit()
                                
                                _load_jobs[job_id]["message"] = f"Added {user_info.get('username') or phone}"
                                await self._notify("account_added", {"phone": phone})
                            except Exception as e:
                                _load_jobs[job_id]["message"] = f"Failed {phone}: {str(e)[:30]}"
                                
                        _load_jobs[job_id]["progress"] = i + 1
                        
                    except Exception as e:
                        logger.error(f"Error loading session {session_file}: {e}")
                        
                _load_jobs[job_id]["status"] = "completed"
                _load_jobs[job_id]["message"] = f"Completed: {_load_jobs[job_id]['progress']}/{len(session_files)}"
                
        except Exception as e:
            _load_jobs[job_id]["status"] = "failed"
            _load_jobs[job_id]["message"] = str(e)
    
    async def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get job status"""
        return _load_jobs.get(job_id) or _import_jobs.get(job_id)
    
    async def import_tdata(self, folder_path: str, proxy_id: Optional[int] = None) -> str:
        """Start tdata import - returns job_id"""
        import uuid
        job_id = str(uuid.uuid4())
        
        _import_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "total": 0,
            "message": "Starting tdata import..."
        }
        
        asyncio.create_task(self._do_import_tdata(job_id, folder_path, proxy_id))
        return job_id
    
    async def _do_import_tdata(self, job_id: str, folder_path: str, proxy_id: Optional[int]):
        """Background task for tdata import"""
        try:
            # Use existing tdata import service
            result = await _import_tdata_accounts(folder_path, proxy_id)
            
            _import_jobs[job_id]["status"] = "completed"
            _import_jobs[job_id]["message"] = f"Imported {result.get('imported', 0)} accounts"
            _import_jobs[job_id]["progress"] = result.get('imported', 0)
            _import_jobs[job_id]["total"] = result.get('total', 0)
            
            await self._notify("tdata_import_completed", result)
            
        except Exception as e:
            _import_jobs[job_id]["status"] = "failed"
            _import_jobs[job_id]["message"] = str(e)


# Global service manager instance
service_manager = ServiceManager()
