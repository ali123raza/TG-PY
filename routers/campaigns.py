import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import MEDIA_DIR
from core.database import get_db, async_session
from core.models import Campaign, MessageTemplate, Log
from services.scheduler import schedule_campaign, unschedule_campaign

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    account_ids: list[int] = []
    targets: list[str] = []
    template_id: int | None = None
    message_text: str = ""
    media_path: str = ""
    media_type: str = ""
    delay_min: int = 30
    delay_max: int = 60
    schedule_cron: str = ""
    rotate_accounts: bool = True
    rotate_proxies: bool = True
    max_per_account: int = 0
    auto_retry: bool = False
    max_retries: int = 3


class CampaignUpdate(BaseModel):
    name: str | None = None
    account_ids: list[int] | None = None
    targets: list[str] | None = None
    template_id: int | None = None
    message_text: str | None = None
    media_path: str | None = None
    media_type: str | None = None
    delay_min: int | None = None
    delay_max: int | None = None
    schedule_cron: str | None = None
    rotate_accounts: bool | None = None
    rotate_proxies: bool | None = None
    max_per_account: int | None = None
    auto_retry: bool | None = None
    max_retries: int | None = None


def _serialize(c: Campaign) -> dict:
    return {
        "id": c.id, "name": c.name,
        "account_ids": json.loads(c.account_ids) if c.account_ids else [],
        "targets": json.loads(c.targets) if c.targets else [],
        "template_id": c.template_id,
        "message_text": c.message_text,
        "media_path": c.media_path,
        "media_type": c.media_type,
        "delay_min": c.delay_min, "delay_max": c.delay_max,
        "status": c.status, "schedule_cron": c.schedule_cron,
        "rotate_accounts": c.rotate_accounts,
        "rotate_proxies": c.rotate_proxies,
        "max_per_account": c.max_per_account,
        "auto_retry": c.auto_retry,
        "max_retries": c.max_retries,
        "created_at": c.created_at.isoformat(),
    }


def _resolve_media(campaign, template):
    """Resolve media path and type from campaign or its template."""
    media_path = campaign.media_path or ""
    media_type = campaign.media_type or ""
    if not media_path and template:
        media_path = template.media_path or ""
        media_type = template.media_type or ""
    if media_path:
        abs_path = str(MEDIA_DIR / media_path)
        return abs_path, media_type
    return None, ""


@router.get("/")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.id.desc()))
    return [_serialize(c) for c in result.scalars().all()]


@router.post("/")
async def create_campaign(req: CampaignCreate, db: AsyncSession = Depends(get_db)):
    c = Campaign(
        name=req.name,
        account_ids=json.dumps(req.account_ids),
        targets=json.dumps(req.targets),
        template_id=req.template_id,
        message_text=req.message_text,
        media_path=req.media_path,
        media_type=req.media_type,
        delay_min=req.delay_min, delay_max=req.delay_max,
        schedule_cron=req.schedule_cron,
        rotate_accounts=req.rotate_accounts,
        rotate_proxies=req.rotate_proxies,
        max_per_account=req.max_per_account,
        auto_retry=req.auto_retry,
        max_retries=req.max_retries,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    return _serialize(c)


@router.patch("/{campaign_id}")
async def update_campaign(campaign_id: int, req: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    data = req.model_dump(exclude_unset=True)
    if "account_ids" in data:
        data["account_ids"] = json.dumps(data["account_ids"])
    if "targets" in data:
        data["targets"] = json.dumps(data["targets"])
    for field, value in data.items():
        setattr(c, field, value)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    unschedule_campaign(campaign_id)
    await db.delete(c)
    await db.commit()
    return {"ok": True}


@router.post("/{campaign_id}/run")
async def run_campaign(campaign_id: int, background_tasks: BackgroundTasks,
                       db: AsyncSession = Depends(get_db)):
    """Run a campaign immediately."""
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")

    account_ids = json.loads(c.account_ids) if c.account_ids else []
    targets = json.loads(c.targets) if c.targets else []

    if not account_ids or not targets:
        raise HTTPException(400, "Campaign has no accounts or targets")
    if not c.message_text and not c.template_id:
        raise HTTPException(400, "Campaign has no message")

    # Resolve template
    template = None
    template_text = None
    media_path = c.media_path or ""
    media_type = c.media_type or ""
    
    if c.template_id:
        template = await db.get(MessageTemplate, c.template_id)
        if template:
            template_text = template.text
            # Use campaign media if set, otherwise use template media
            if not media_path and template.media_path:
                media_path = template.media_path
                media_type = template.media_type or ""
    
    # Convert to absolute path
    if media_path:
        media_path = str(MEDIA_DIR / media_path)
        print(f"Running campaign with media: {media_path} ({media_type})")
    else:
        print("Running campaign without media")

    from routers.messaging import _send_bulk, _active_jobs
    import random
    job_id = f"campaign_{campaign_id}_{random.randint(1000, 9999)}"
    _active_jobs[job_id] = {"status": "starting", "sent": 0, "failed": 0, "total": 0,
                            "campaign_id": campaign_id}

    c.status = "running"
    await db.commit()

    async def _run():
        await _send_bulk(
            job_id, account_ids, targets,
            c.message_text, template_text, {},
            media_path, c.delay_min, c.delay_max, "round-robin",
            c.max_per_account, c.rotate_proxies, c.auto_retry, campaign_id,
            media_type,
        )
        async with async_session() as db2:
            camp = await db2.get(Campaign, campaign_id)
            if camp:
                camp.status = "completed"
                await db2.commit()

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "running"}


@router.post("/{campaign_id}/schedule")
async def schedule(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Schedule a campaign using its cron expression."""
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    if not c.schedule_cron:
        raise HTTPException(400, "No cron schedule set")
    try:
        schedule_campaign(campaign_id, c.schedule_cron)
    except Exception as e:
        raise HTTPException(400, f"Invalid cron: {e}")
    c.status = "scheduled"
    await db.commit()
    return {"status": "scheduled", "cron": c.schedule_cron}


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    unschedule_campaign(campaign_id)
    c.status = "paused"
    await db.commit()
    return {"status": "paused"}
