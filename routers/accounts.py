import asyncio
import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload
from core.config import SESSIONS_DIR, BASE_DIR
from core.database import get_db, async_session
from core.models import Account, Proxy, Log
from services.telegram import client_manager
from services.tdata_import import import_tdata_accounts

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job tracking for session loading
_load_jobs: dict[str, dict] = {}
_import_jobs: dict[str, dict] = {}


class LoginStartRequest(BaseModel):
    phone: str
    proxy_id: int | None = None


class LoginCompleteRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    password: str | None = None
    proxy_id: int | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    proxy_id: int | None = None
    is_active: bool | None = None


@router.post("/login/start")
async def login_start(req: LoginStartRequest, db: AsyncSession = Depends(get_db)):
    proxy = None
    if req.proxy_id:
        proxy = await db.get(Proxy, req.proxy_id)
    try:
        phone_code_hash = await client_manager.start_login(req.phone, proxy)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"phone_code_hash": phone_code_hash}


@router.post("/login/complete")
async def login_complete(req: LoginCompleteRequest, db: AsyncSession = Depends(get_db)):
    proxy = None
    if req.proxy_id:
        proxy = await db.get(Proxy, req.proxy_id)
    try:
        user_info = await client_manager.complete_login(
            req.phone, req.code, req.phone_code_hash, req.password
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))

    existing = (await db.execute(select(Account).where(Account.phone == req.phone))).scalar_one_or_none()
    if existing:
        existing.name = f"{user_info['first_name']} {user_info['last_name']}".strip()
        existing.username = user_info["username"]
        existing.session_file = req.phone.replace("+", "").replace(" ", "")
        existing.proxy_id = req.proxy_id
        existing.is_active = True
        existing.status = "active"
        account = existing
    else:
        account = Account(
            phone=req.phone,
            name=f"{user_info['first_name']} {user_info['last_name']}".strip(),
            username=user_info["username"],
            session_file=req.phone.replace("+", "").replace(" ", ""),
            proxy_id=req.proxy_id,
            is_active=True,
            status="active",
        )
        db.add(account)
    await db.commit()
    await db.refresh(account)
    return {"id": account.id, "phone": account.phone, "name": account.name, "username": account.username}


def _serialize_account(a: Account) -> dict:
    return {
        "id": a.id, "phone": a.phone, "name": a.name, "username": a.username,
        "proxy_id": a.proxy_id, "is_active": a.is_active, "status": a.status,
        "messages_sent": a.messages_sent,
        "last_checked": a.last_checked.isoformat() if a.last_checked else None,
        "created_at": a.created_at.isoformat(),
    }


async def _load_sessions_task(job_id: str, session_phones: list[str], proxies: list[dict]):
    """Background task: verify each session file and create Account records."""
    job = _load_jobs[job_id]
    job["status"] = "running"

    for i, phone in enumerate(session_phones):
        proxy_dict = proxies[i % len(proxies)] if proxies else None
        proxy_id = proxy_dict["id"] if proxy_dict else None
        result_entry = {"phone": phone, "status": "pending"}

        try:
            user_info = await client_manager.verify_session(phone, proxy_dict)
            name = f"{user_info['first_name']} {user_info['last_name']}".strip()
            session_file = phone.replace("+", "").replace(" ", "")

            async with async_session() as db:
                # Double-check not already in DB
                existing = (await db.execute(
                    select(Account).where(Account.phone == phone)
                )).scalar_one_or_none()
                if existing:
                    result_entry["status"] = "skipped"
                    result_entry["reason"] = "already in database"
                else:
                    account = Account(
                        phone=phone,
                        name=name,
                        username=user_info.get("username", ""),
                        session_file=session_file,
                        proxy_id=proxy_id,
                        is_active=True,
                        status="active",
                    )
                    db.add(account)
                    db.add(Log(
                        level="info", category="auth",
                        message=f"Session loaded: {phone} ({name})",
                    ))
                    await db.commit()
                    result_entry["status"] = "success"
                    result_entry["name"] = name
                    result_entry["username"] = user_info.get("username", "")

            job["completed"] += 1
            logger.info(f"[load-sessions] {phone}: {result_entry['status']}")

        except Exception as e:
            result_entry["status"] = "failed"
            result_entry["error"] = str(e)
            job["failed"] += 1
            logger.error(f"[load-sessions] {phone}: failed - {e}")

        job["results"].append(result_entry)

        # Anti-flood delay between accounts
        if i < len(session_phones) - 1:
            await asyncio.sleep(1.5)

    job["status"] = "completed"


@router.post("/load-sessions")
async def load_sessions(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Scan sessions/ folder for .session files and bulk-load them as accounts."""
    # Scan session files
    session_files = list(Path(SESSIONS_DIR).glob("*.session"))
    if not session_files:
        return {"job_id": None, "total": 0, "message": "No session files found"}

    # Get existing phones to skip duplicates
    result = await db.execute(select(Account.phone))
    existing_phones = set()
    for row in result.scalars().all():
        existing_phones.add(row.replace("+", "").replace(" ", ""))

    # Build list of new session phones
    session_phones = []
    for f in session_files:
        stem = f.stem  # filename without .session
        if stem not in existing_phones:
            session_phones.append("+" + stem)

    if not session_phones:
        return {"job_id": None, "total": 0, "message": "All sessions already loaded"}

    # Get active proxies
    proxy_result = await db.execute(select(Proxy).where(Proxy.is_active == True).order_by(Proxy.id))
    proxies = [
        {"id": p.id, "scheme": p.scheme, "host": p.host, "port": p.port,
         "username": p.username, "password": p.password}
        for p in proxy_result.scalars().all()
    ]

    # Create job
    job_id = str(uuid.uuid4())[:8]
    _load_jobs[job_id] = {
        "status": "starting",
        "total": len(session_phones),
        "completed": 0,
        "failed": 0,
        "results": [],
    }

    background_tasks.add_task(_load_sessions_task, job_id, session_phones, proxies)
    return {"job_id": job_id, "total": len(session_phones)}


@router.get("/load-sessions/status/{job_id}")
async def load_sessions_status(job_id: str):
    """Get the status of a session loading job."""
    job = _load_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status": job["status"],
        "total": job["total"],
        "completed": job["completed"],
        "failed": job["failed"],
        "results": job["results"][-20:],  # last 20 entries
    }


class ImportTdataRequest(BaseModel):
    assign_proxies: bool = True  # Auto-assign proxies round-robin


async def _import_tdata_task(job_id: str, assign_proxies: bool):
    """Background task for tdata import."""
    job = _import_jobs[job_id]
    job["status"] = "running"

    tgdata_dir = BASE_DIR / "tgdata"

    try:
        results = await import_tdata_accounts(tgdata_dir, assign_proxies)

        if "error" in results:
            job["status"] = "failed"
            job["error"] = results["error"]
        else:
            job["status"] = "completed"
            job["total"] = results["total"]
            job["imported"] = results["imported"]
            job["skipped"] = results["skipped"]
            job["failed"] = results["failed"]
            job["results"] = results["accounts"]

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.error(f"[import-tdata] Job {job_id} failed: {e}")


@router.post("/cleanup-fake")
async def cleanup_fake_accounts(db: AsyncSession = Depends(get_db)):
    """
    Delete accounts with status='needs_verification' (from failed tdata import).
    These are placeholder entries without valid sessions.
    """
    result = await db.execute(
        select(Account).where(Account.status == "needs_verification")
    )
    fake_accounts = result.scalars().all()

    count = len(fake_accounts)
    for acc in fake_accounts:
        await db.delete(acc)

    await db.commit()

    return {"deleted": count, "message": f"Deleted {count} fake accounts"}


@router.post("/import-tdata")
async def import_tdata(
    req: ImportTdataRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Import accounts from tgdata/ folder.
    Auto-assigns proxies round-robin if assign_proxies=True and proxies exist.
    """
    if req is None:
        req = ImportTdataRequest(assign_proxies=True)

    tgdata_dir = BASE_DIR / "tgdata"
    if not tgdata_dir.exists():
        return {"job_id": None, "message": "tgdata folder not found"}

    # Check if any tdata folders exist
    tdata_folders = [f for f in tgdata_dir.iterdir() if f.is_dir() and (f / "tdata").exists()]
    if not tdata_folders:
        return {"job_id": None, "message": "No tdata folders found"}

    # Create job
    job_id = str(uuid.uuid4())[:8]
    _import_jobs[job_id] = {
        "status": "starting",
        "total": len(tdata_folders),
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "results": [],
    }

    background_tasks.add_task(_import_tdata_task, job_id, req.assign_proxies)

    return {"job_id": job_id, "total": len(tdata_folders)}


@router.get("/import-tdata/status/{job_id}")
async def import_tdata_status(job_id: str):
    """Get the status of a tdata import job."""
    job = _import_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status": job["status"],
        "total": job.get("total", 0),
        "imported": job.get("imported", 0),
        "skipped": job.get("skipped", 0),
        "failed": job.get("failed", 0),
        "results": job.get("results", [])[-20:],  # last 20 entries
        "error": job.get("error"),
    }


@router.get("/")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).order_by(Account.id))
    return [_serialize_account(a) for a in result.scalars().all()]


@router.get("/{account_id}")
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    return _serialize_account(account)


@router.patch("/{account_id}")
async def update_account(account_id: int, req: AccountUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return _serialize_account(account)


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    await client_manager.disconnect(account_id)
    await db.delete(account)
    await db.commit()
    return {"ok": True}


@router.post("/{account_id}/health")
async def check_health(account_id: int, db: AsyncSession = Depends(get_db)):
    """Check if an account's session is valid and detect bans."""
    result = await db.execute(
        select(Account).options(selectinload(Account.proxy)).where(Account.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    try:
        client = await client_manager.get_client(account.id, account.phone, account.proxy)
        me = await client.get_me()

        if me.is_restricted:
            account.status = "restricted"
            account.is_active = False
        elif me.is_scam or me.is_fake:
            account.status = "banned"
            account.is_active = False
        else:
            account.status = "active"
            account.is_active = True

        account.last_checked = datetime.utcnow()
        db.add(Log(level="info", category="auth", account_id=account.id,
                    message=f"Health check: {account.status}"))
        await db.commit()

        return {"status": account.status, "is_active": account.is_active, "username": me.username or ""}

    except Exception as e:
        err_str = str(e).lower()
        if "deactivated" in err_str or "banned" in err_str or "deleted" in err_str:
            account.status = "banned"
            account.is_active = False
        elif "auth" in err_str or "session" in err_str:
            account.status = "disconnected"
            account.is_active = False
        else:
            account.status = "disconnected"

        account.last_checked = datetime.utcnow()
        db.add(Log(level="error", category="auth", account_id=account.id,
                    message=f"Health check failed: {e}"))
        await db.commit()

        return {"status": account.status, "is_active": account.is_active, "error": str(e)}


@router.post("/health/all")
async def check_all_health(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Check health of all accounts in background."""
    result = await db.execute(select(Account).order_by(Account.id))
    account_ids = [a.id for a in result.scalars().all()]

    async def _check_all():
        for aid in account_ids:
            async with async_session() as db2:
                result = await db2.execute(
                    select(Account).options(selectinload(Account.proxy)).where(Account.id == aid)
                )
                acc = result.scalar_one_or_none()
                if not acc:
                    continue
                try:
                    client = await client_manager.get_client(acc.id, acc.phone, acc.proxy)
                    me = await client.get_me()
                    if me.is_restricted:
                        acc.status = "restricted"
                        acc.is_active = False
                    elif me.is_scam or me.is_fake:
                        acc.status = "banned"
                        acc.is_active = False
                    else:
                        acc.status = "active"
                        acc.is_active = True
                except Exception as e:
                    err_str = str(e).lower()
                    if "deactivated" in err_str or "banned" in err_str:
                        acc.status = "banned"
                        acc.is_active = False
                    else:
                        acc.status = "disconnected"
                acc.last_checked = datetime.utcnow()
                await db2.commit()

    background_tasks.add_task(_check_all)
    return {"ok": True, "checking": len(account_ids)}
