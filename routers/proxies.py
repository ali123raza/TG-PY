import asyncio
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Proxy

router = APIRouter()


class ProxyCreate(BaseModel):
    scheme: str = "socks5"
    host: str
    port: int
    username: str = ""
    password: str = ""


class ProxyUpdate(BaseModel):
    scheme: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None


class BulkProxyImport(BaseModel):
    text: str


def _parse_proxy_line(line: str) -> dict | None:
    """Parse a single proxy line into {scheme, host, port, username, password}.

    Supported formats:
      - socks5://host:port
      - socks5://user:pass@host:port
      - host:port              (defaults to socks5)
      - host:port:user:pass    (alternate format)
    """
    line = line.strip()
    if not line:
        return None

    # Format: scheme://[user:pass@]host:port
    m = re.match(
        r'^(socks5|socks4|http|https)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$',
        line, re.IGNORECASE,
    )
    if m:
        return {
            "scheme": m.group(1).lower(),
            "host": m.group(4),
            "port": int(m.group(5)),
            "username": m.group(2) or "",
            "password": m.group(3) or "",
        }

    # Format: host:port:user:pass
    parts = line.split(":")
    if len(parts) == 4:
        try:
            return {
                "scheme": "socks5",
                "host": parts[0],
                "port": int(parts[1]),
                "username": parts[2],
                "password": parts[3],
            }
        except ValueError:
            return None

    # Format: host:port
    if len(parts) == 2:
        try:
            return {
                "scheme": "socks5",
                "host": parts[0],
                "port": int(parts[1]),
            }
        except ValueError:
            return None

    return None


@router.post("/bulk")
async def bulk_import_proxies(req: BulkProxyImport, db: AsyncSession = Depends(get_db)):
    """Import proxies from multi-line text. Returns counts of imported/skipped/failed."""
    lines = req.text.strip().splitlines()
    imported = 0
    skipped = 0
    failed = 0

    for line in lines:
        parsed = _parse_proxy_line(line)
        if parsed is None:
            if line.strip():
                failed += 1
            continue

        # Check for duplicate (same scheme+host+port)
        existing = await db.execute(
            select(Proxy).where(
                and_(
                    Proxy.scheme == parsed["scheme"],
                    Proxy.host == parsed["host"],
                    Proxy.port == parsed["port"],
                )
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        proxy = Proxy(
            scheme=parsed["scheme"],
            host=parsed["host"],
            port=parsed["port"],
            username=parsed.get("username", ""),
            password=parsed.get("password", ""),
        )
        db.add(proxy)
        imported += 1

    if imported > 0:
        await db.commit()

    return {"imported": imported, "skipped": skipped, "failed": failed}


@router.get("/")
async def list_proxies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Proxy).order_by(Proxy.id))
    return [
        {
            "id": p.id, "scheme": p.scheme, "host": p.host, "port": p.port,
            "username": p.username, "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
        }
        for p in result.scalars().all()
    ]


@router.post("/")
async def create_proxy(req: ProxyCreate, db: AsyncSession = Depends(get_db)):
    proxy = Proxy(**req.model_dump())
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return {"id": proxy.id, "host": proxy.host, "port": proxy.port}


@router.patch("/{proxy_id}")
async def update_proxy(proxy_id: int, req: ProxyUpdate, db: AsyncSession = Depends(get_db)):
    proxy = await db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(proxy, field, value)
    await db.commit()
    await db.refresh(proxy)
    return {"id": proxy.id, "host": proxy.host, "port": proxy.port}


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int, db: AsyncSession = Depends(get_db)):
    proxy = await db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    await db.delete(proxy)
    await db.commit()
    return {"ok": True}


@router.post("/{proxy_id}/test")
async def test_proxy(proxy_id: int, db: AsyncSession = Depends(get_db)):
    proxy = await db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(404, "Proxy not found")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(proxy.host, proxy.port), timeout=10
        )
        writer.close()
        await writer.wait_closed()
        return {"ok": True, "message": f"Connected to {proxy.host}:{proxy.port}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
