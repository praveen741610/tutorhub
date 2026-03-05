from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.deps import get_db
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.auth import LogoutIn, RefreshIn, RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_session_payload(token: str) -> tuple[str, datetime]:
    claims = decode_token(token)
    jti = claims.get("jti")
    exp = claims.get("exp")
    if not jti or not exp:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc).replace(tzinfo=None)
    return str(jti), expires_at


def _store_refresh_session(db: Session, user_id: int, refresh_token: str) -> tuple[str, datetime]:
    jti, expires_at = _token_session_payload(refresh_token)
    db.add(
        RefreshSession(
            user_id=user_id,
            token_jti=jti,
            expires_at=expires_at,
        )
    )
    return jti, expires_at


def _create_auth_tokens(db: Session, user: User) -> TokenOut:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    _store_refresh_session(db, user.id, refresh_token)
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        access_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> dict:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenOut:
    # OAuth2PasswordRequestForm uses "username" field; we treat it as email
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_out = _create_auth_tokens(db, user)
    db.commit()
    return token_out


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    try:
        claims = decode_token(payload.refresh_token)
        subject = claims.get("sub")
        token_type = claims.get("type")
        refresh_jti = claims.get("jti")
        if token_type != "refresh" or not subject or not refresh_jti:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, int(subject))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session = db.execute(
        select(RefreshSession).where(
            RefreshSession.token_jti == str(refresh_jti),
            RefreshSession.user_id == user.id,
        )
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Refresh session not found")
    if session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token already revoked")
    if session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_out = _create_auth_tokens(db, user)
    new_jti, _ = _token_session_payload(token_out.refresh_token)
    session.revoked_at = datetime.utcnow()
    session.replaced_by_jti = new_jti
    db.commit()
    return token_out


@router.post("/logout")
def logout(payload: LogoutIn, db: Session = Depends(get_db)) -> dict:
    try:
        claims = decode_token(payload.refresh_token, verify_exp=False)
        subject = claims.get("sub")
        token_type = claims.get("type")
        jti = claims.get("jti")
        if token_type != "refresh" or not subject or not jti:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    session = db.execute(
        select(RefreshSession).where(
            RefreshSession.token_jti == str(jti),
            RefreshSession.user_id == int(subject),
        )
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Refresh session not found")

    if session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        db.commit()

    return {"ok": True}


@router.post("/logout-all")
def logout_all(refresh: RefreshIn, db: Session = Depends(get_db)) -> dict:
    try:
        claims = decode_token(refresh.refresh_token, verify_exp=False)
        subject = claims.get("sub")
        token_type = claims.get("type")
        if token_type != "refresh" or not subject:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    rows = db.execute(
        select(RefreshSession).where(
            RefreshSession.user_id == int(subject),
            RefreshSession.revoked_at.is_(None),
        )
    ).scalars().all()
    now = datetime.utcnow()
    for row in rows:
        row.revoked_at = now
    db.commit()
    return {"ok": True, "revoked_sessions": len(rows)}
