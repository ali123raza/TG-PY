import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()
_started = False


def ensure_started():
    global _started
    if not _started:
        scheduler.start()
        _started = True


async def run_campaign_job(campaign_id: int):
    """Execute a scheduled campaign run."""
    from core.config import MEDIA_DIR
    from core.database import async_session
    from core.models import Campaign, MessageTemplate
    from routers.messaging import _send_bulk, _active_jobs
    import random

    async with async_session() as db:
        campaign = await db.get(Campaign, campaign_id)
        if not campaign or campaign.status != "scheduled":
            return

        account_ids = json.loads(campaign.account_ids) if campaign.account_ids else []
        targets = json.loads(campaign.targets) if campaign.targets else []

        if not account_ids or not targets:
            return

        # Resolve template
        template_text = None
        media_path = campaign.media_path or ""
        media_type = campaign.media_type or ""

        if campaign.template_id:
            template = await db.get(MessageTemplate, campaign.template_id)
            if template:
                template_text = template.text
                if not media_path and template.media_path:
                    media_path = template.media_path
                    media_type = template.media_type or ""

        resolved_media = str(MEDIA_DIR / media_path) if media_path else None

        job_id = f"campaign_{campaign_id}_{random.randint(1000, 9999)}"
        _active_jobs[job_id] = {"status": "starting", "sent": 0, "failed": 0, "total": 0,
                                "campaign_id": campaign_id}

        campaign.status = "running"
        await db.commit()

        await _send_bulk(
            job_id, account_ids, targets,
            campaign.message_text, template_text, {},
            resolved_media, campaign.delay_min, campaign.delay_max, "round-robin",
            campaign.max_per_account, campaign.rotate_proxies, campaign.auto_retry, campaign_id,
            media_type,
        )

        campaign.status = "completed"
        await db.commit()


def schedule_campaign(campaign_id: int, cron_expression: str):
    """Add a campaign to the scheduler with a cron expression."""
    ensure_started()
    job_id = f"campaign_{campaign_id}"
    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    scheduler.add_job(
        run_campaign_job, CronTrigger.from_crontab(cron_expression),
        id=job_id, args=[campaign_id], replace_existing=True,
    )


def unschedule_campaign(campaign_id: int):
    try:
        scheduler.remove_job(f"campaign_{campaign_id}")
    except Exception:
        pass
