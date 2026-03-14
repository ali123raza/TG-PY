from fastapi import APIRouter
from pydantic import BaseModel

from core.config import get_settings, _save_settings

router = APIRouter()


class SettingsUpdate(BaseModel):
    api_id: int | None = None
    api_hash: str | None = None
    default_delay_min: int | None = None
    default_delay_max: int | None = None
    max_per_account: int | None = None
    flood_wait_cap: int | None = None


@router.get("/")
async def get_all_settings():
    s = get_settings()
    # Mask api_hash for display
    masked = dict(s)
    if masked.get("api_hash"):
        h = masked["api_hash"]
        masked["api_hash_preview"] = h[:4] + "..." + h[-4:] if len(h) > 8 else "***"
    return masked


@router.patch("/")
async def update_settings(req: SettingsUpdate):
    data = req.model_dump(exclude_unset=True)
    _save_settings(data)
    return {"ok": True, "updated": list(data.keys())}
