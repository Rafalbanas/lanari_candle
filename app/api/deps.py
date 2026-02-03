from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.deps import get_db
from app.core.config import settings
from app.core.security import JWT_ALG
from app.db.models import UserDB

bearer = HTTPBearer(auto_error=True)
bearer_optional = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> UserDB:
    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALG])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.execute(select(UserDB).where(UserDB.email == email)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found/inactive")
    return user


def require_admin(current_user: UserDB = Depends(get_current_user)) -> UserDB:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_optional),
    db: Session = Depends(get_db),
) -> UserDB | None:
    # If no Authorization header, return None gracefully
    if creds is None:
        return None
    return get_current_user(creds, db)
