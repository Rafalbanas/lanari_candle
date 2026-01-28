import shutil
import os
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.db.models import MediaDB
from app.schemas.media import MediaOut
from app.db.models import UserDB
from app.core.config import settings

router = APIRouter(prefix="/media", tags=["media"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_ext(filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    return f".{ext}" if ext else ""

@router.post("", response_model=MediaOut, status_code=201)
def upload_media(
    file: UploadFile = File(...),
    caption: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    # Generowanie unikalnej nazwy
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Zapis pliku
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # URL do pliku (zakładamy, że /static jest zamontowane w main.py)
    # Jeśli używasz proxy/nginxa, tu może być potrzebny pełny URL
    url = f"{settings.api_prefix}/static/uploads/{filename}"
    # Uwaga: w main.py montujemy static pod "/static", ale api_prefix to "/api".
    # Żeby było prościej, w main.py zamontujemy static pod "/static" (bez api prefixu)
    # albo zwrócimy relatywny URL. Tutaj przyjmijmy konwencję:
    url = f"/static/uploads/{filename}"

    media = MediaDB(
        owner_id=current_user.id,
        filename=filename,
        url=url,
        caption=caption
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return media


@router.get("", response_model=list[MediaOut])
def list_media(db: Session = Depends(get_db)):
    stmt = select(MediaDB).order_by(desc(MediaDB.created_at))
    return db.execute(stmt).scalars().all()