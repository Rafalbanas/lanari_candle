from datetime import datetime, timedelta, UTC
import jwt
import bcrypt
from app.core.config import settings

JWT_ALG = "HS256"
JWT_EXPIRES_MIN = 60 * 24  # 24h


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(sub: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MIN)).timestamp()),
    }
    # Używamy secret_key z configu
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALG)