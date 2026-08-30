"""File upload API: stores files under uploads/ and serves them statically."""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.deps import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path("uploads")
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".doc", ".docx",
               ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".zip", ".rar"}
MAX_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("", summary="上传文件(图片/附件), 返回访问URL")
async def upload(file: UploadFile, user: User = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"不支持的文件类型 {ext}")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "文件超过 20MB 限制")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / name).write_bytes(content)
    return {"url": f"/uploads/{name}", "name": file.filename, "size": len(content)}
