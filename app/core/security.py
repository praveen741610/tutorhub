from datetime import datetime, timedelta, timezone
from uuid import uuid4
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _create_token(subject: str, token_type: str, expire_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expire_minutes)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        token_type="access",
        expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        token_type="refresh",
        expire_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
    )


def decode_token(token: str, *, verify_exp: bool = True) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALG],
        options={"verify_exp": verify_exp},
    )


def get_token_subject(token: str, expected_type: str) -> str:
    payload = decode_token(token)
    token_type = payload.get("type")
    subject = payload.get("sub")
    if token_type != expected_type or not subject:
        raise JWTError("Invalid token")
    return str(subject)
