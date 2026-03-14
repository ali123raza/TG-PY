from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Account, Proxy, Campaign, MessageTemplate, Log

router = APIRouter()


@router.get("/")
async def get_stats(db: AsyncSession = Depends(get_db)):
    accounts_total = (await db.execute(select(func.count(Account.id)))).scalar() or 0
    accounts_active = (await db.execute(select(func.count(Account.id)).where(Account.is_active == True))).scalar() or 0
    proxies_total = (await db.execute(select(func.count(Proxy.id)))).scalar() or 0
    campaigns_total = (await db.execute(select(func.count(Campaign.id)))).scalar() or 0
    templates_total = (await db.execute(select(func.count(MessageTemplate.id)))).scalar() or 0

    # Message stats from logs
    msg_sent = (await db.execute(
        select(func.count(Log.id)).where(Log.category == "message", Log.level == "info")
    )).scalar() or 0
    msg_failed = (await db.execute(
        select(func.count(Log.id)).where(Log.category == "message", Log.level == "error")
    )).scalar() or 0

    # Scrape stats
    scrape_ops = (await db.execute(
        select(func.count(Log.id)).where(Log.category == "scrape", Log.level == "info")
    )).scalar() or 0

    # Campaign status breakdown
    campaign_statuses = {}
    result = await db.execute(
        select(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status)
    )
    for status, count in result.all():
        campaign_statuses[status] = count

    # Per-account message stats
    per_account = []
    result = await db.execute(
        select(
            Log.account_id,
            func.count(case((Log.level == "info", 1))).label("sent"),
            func.count(case((Log.level == "error", 1))).label("failed"),
        ).where(Log.category == "message", Log.account_id.isnot(None))
        .group_by(Log.account_id)
    )
    for account_id, sent, failed in result.all():
        acc = await db.get(Account, account_id)
        per_account.append({
            "account_id": account_id,
            "phone": acc.phone if acc else "?",
            "name": acc.name if acc else "?",
            "sent": sent, "failed": failed,
        })

    # Recent activity (last 10 logs)
    recent = await db.execute(select(Log).order_by(Log.id.desc()).limit(10))
    recent_logs = [
        {"id": l.id, "level": l.level, "category": l.category,
         "message": l.message, "created_at": l.created_at.isoformat()}
        for l in recent.scalars().all()
    ]

    return {
        "accounts": {"total": accounts_total, "active": accounts_active},
        "proxies": proxies_total,
        "campaigns": {"total": campaigns_total, "by_status": campaign_statuses},
        "templates": templates_total,
        "messages": {"sent": msg_sent, "failed": msg_failed, "total": msg_sent + msg_failed},
        "scrape_ops": scrape_ops,
        "per_account": per_account,
        "recent_logs": recent_logs,
    }
