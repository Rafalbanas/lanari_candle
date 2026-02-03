import shutil
import os
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.deps import get_db
from app.db.models import MediaDB
from app.schemas.media import MediaOut
from app.core.config import settings
from app.api.deps import get_current_user_optional, require_admin
from app.db.models import UserDB

router = APIRouter(prefix="/media", tags=["media"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("", response_model=MediaOut, status_code=201)
def upload_media(
    file: UploadFile = File(...),
    caption: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserDB | None = Depends(get_current_user_optional),
):
    # Walidacja typu pliku (prosta)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generowanie unikalnej nazwy
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
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
        filename=filename,
        url=url,
        caption=caption,
        owner_id=current_user.id if current_user else None,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return media


@router.get("", response_model=list[MediaOut])
def list_media(db: Session = Depends(get_db)):
    stmt = select(MediaDB).order_by(MediaDB.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.delete("/{media_id}", status_code=204)
def delete_media(media_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    media = db.get(MediaDB, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    # try remove file
    file_path = os.path.join(UPLOAD_DIR, media.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass

    db.delete(media)
    db.commit()
    return
