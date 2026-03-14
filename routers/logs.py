from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Log

router = APIRouter()


@router.get("/")
async def list_logs(
    limit: int = 100,
    offset: int = 0,
    level: str | None = None,
    category: str | None = None,
    account_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Log).order_by(Log.id.desc())
    if level:
        q = q.where(Log.level == level)
    if category:
        q = q.where(Log.category == category)
    if account_id:
        q = q.where(Log.account_id == account_id)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    return [
        {
            "id": l.id, "level": l.level, "category": l.category,
            "account_id": l.account_id, "message": l.message,
            "created_at": l.created_at.isoformat(),
        }
        for l in result.scalars().all()
    ]


@router.get("/count")
async def log_count(
    level: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(func.count(Log.id))
    if level:
        q = q.where(Log.level == level)
    if category:
        q = q.where(Log.category == category)
    result = await db.execute(q)
    return {"count": result.scalar()}


@router.delete("/clear")
async def clear_logs(category: str | None = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    q = delete(Log)
    if category:
        q = q.where(Log.category == category)
    await db.execute(q)
    await db.commit()
    return {"ok": True}
