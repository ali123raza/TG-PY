import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, async_session
from core.models import Account, Log
from services.telegram import client_manager
from services.scraper import scrape_members, join_group

router = APIRouter()

_scrape_results: dict[str, dict] = {}
_join_jobs: dict[str, dict] = {}


class ScrapeRequest(BaseModel):
    account_id: int
    group: str
    limit: int = 0
    filter_type: str = "all"
    keyword: str = ""


class JoinRequest(BaseModel):
    account_ids: list[int]
    groups: list[str]
    delay_min: int = 10
    delay_max: int = 30


@router.post("/scrape")
async def scrape(req: ScrapeRequest, background_tasks: BackgroundTasks,
                 db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Account).options(selectinload(Account.proxy)).where(Account.id == req.account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    job_id = f"scrape_{random.randint(10000, 99999)}"
    _scrape_results[job_id] = {"status": "running", "members": [], "count": 0, "error": None}

    # Capture proxy before background task (avoid lazy load)
    proxy = account.proxy
    phone = account.phone
    acc_id = account.id

    async def _do():
        try:
            client = await client_manager.get_client(acc_id, phone, proxy)
            members = await scrape_members(client, req.group, req.limit, req.filter_type, req.keyword)
            _scrape_results[job_id]["members"] = members
            _scrape_results[job_id]["count"] = len(members)
            _scrape_results[job_id]["status"] = "completed"
            async with async_session() as db2:
                db2.add(Log(level="info", category="scrape", account_id=acc_id,
                            message=f"Scraped {len(members)} from {req.group} via proxy:{proxy.host if proxy else 'direct'}"))
                await db2.commit()
        except Exception as e:
            _scrape_results[job_id]["status"] = "failed"
            _scrape_results[job_id]["error"] = str(e)

    background_tasks.add_task(_do)
    return {"job_id": job_id}


@router.get("/scrape/{job_id}")
async def get_scrape_result(job_id: str):
    if job_id not in _scrape_results:
        raise HTTPException(404, "Job not found")
    return _scrape_results[job_id]


@router.post("/join")
async def join_groups(req: JoinRequest, background_tasks: BackgroundTasks,
                      db: AsyncSession = Depends(get_db)):
    if not req.account_ids or not req.groups:
        raise HTTPException(400, "No accounts or groups provided")

    job_id = f"join_{random.randint(10000, 99999)}"
    _join_jobs[job_id] = {"status": "running", "joined": 0, "failed": 0, "total": len(req.groups), "results": []}

    async def _do():
        job = _join_jobs[job_id]
        async with async_session() as db2:
            result = await db2.execute(
                select(Account)
                .options(selectinload(Account.proxy))
                .where(Account.id.in_(req.account_ids), Account.is_active == True)
            )
            accounts = list(result.scalars().all())

        if not accounts:
            job["status"] = "failed"
            job["error"] = "No active accounts"
            return

        # Connect all accounts with their proxies
        clients = []
        for acc in accounts:
            try:
                c = await client_manager.get_client(acc.id, acc.phone, acc.proxy)
                clients.append((acc, c))
            except Exception:
                pass

        if not clients:
            job["status"] = "failed"
            job["error"] = "Could not connect any account"
            return

        for i, group in enumerate(req.groups):
            acc, client = clients[i % len(clients)]
            res = await join_group(client, group)
            job["results"].append({"group": group, **res})

            async with async_session() as db2:
                if res["ok"]:
                    job["joined"] += 1
                    db2.add(Log(level="info", category="scrape", account_id=acc.id,
                                message=f"Joined {group} via proxy:{acc.proxy.host if acc.proxy else 'direct'}"))
                else:
                    job["failed"] += 1
                    db2.add(Log(level="error", category="scrape", account_id=acc.id,
                                message=f"Failed to join {group}: {res.get('error', '')}"))
                await db2.commit()

            if i < len(req.groups) - 1:
                await asyncio.sleep(random.uniform(req.delay_min, req.delay_max))

        job["status"] = "completed"

    background_tasks.add_task(_do)
    return {"job_id": job_id}


@router.get("/join/{job_id}")
async def get_join_result(job_id: str):
    if job_id not in _join_jobs:
        raise HTTPException(404, "Job not found")
    return _join_jobs[job_id]


@router.get("/logs")
async def get_scrape_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Log).where(Log.category == "scrape").order_by(Log.id.desc()).limit(limit)
    )
    return [
        {"id": l.id, "level": l.level, "account_id": l.account_id,
         "message": l.message, "created_at": l.created_at.isoformat()}
        for l in result.scalars().all()
    ]
