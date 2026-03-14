import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import MEDIA_DIR
from core.database import get_db
from core.models import MessageTemplate

router = APIRouter()

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".flac", ".m4a"}


def _detect_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in PHOTO_EXTS:
        return "photo"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return "document"


def _serialize(t: MessageTemplate) -> dict:
    return {
        "id": t.id, "name": t.name, "text": t.text,
        "media_path": t.media_path, "media_type": t.media_type,
        "created_at": t.created_at.isoformat(),
    }


class TemplateCreate(BaseModel):
    name: str
    text: str
    media_path: str = ""
    media_type: str = ""


class TemplateUpdate(BaseModel):
    name: str | None = None
    text: str | None = None
    media_path: str | None = None
    media_type: str | None = None


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = MEDIA_DIR / unique_name
    content = await file.read()
    dest.write_bytes(content)
    media_type = _detect_media_type(file.filename)
    return {"filename": unique_name, "media_type": media_type, "size": len(content)}


@router.get("/")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessageTemplate).order_by(MessageTemplate.id.desc()))
    return [_serialize(t) for t in result.scalars().all()]


@router.post("/")
async def create_template(req: TemplateCreate, db: AsyncSession = Depends(get_db)):
    t = MessageTemplate(name=req.name, text=req.text, media_path=req.media_path, media_type=req.media_type)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.get("/{template_id}")
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    t = await db.get(MessageTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return _serialize(t)


@router.patch("/{template_id}")
async def update_template(template_id: int, req: TemplateUpdate, db: AsyncSession = Depends(get_db)):
    t = await db.get(MessageTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    data = req.model_dump(exclude_unset=True)
    # If media_path is being cleared, delete old file
    if "media_path" in data and data["media_path"] == "" and t.media_path:
        old_file = MEDIA_DIR / t.media_path
        if old_file.exists():
            old_file.unlink()
    for field, value in data.items():
        setattr(t, field, value)
    await db.commit()
    await db.refresh(t)
    return _serialize(t)


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    t = await db.get(MessageTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    # Cleanup media file
    if t.media_path:
        media_file = MEDIA_DIR / t.media_path
        if media_file.exists():
            media_file.unlink()
    await db.delete(t)
    await db.commit()
    return {"ok": True}


@router.post("/{template_id}/preview")
async def preview_template(template_id: int, variables: dict = {}, db: AsyncSession = Depends(get_db)):
    """Preview a template with placeholder substitution."""
    t = await db.get(MessageTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    text = t.text
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", str(value))
    return {"preview": text}
