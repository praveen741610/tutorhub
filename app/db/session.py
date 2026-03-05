from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DEV_ENVIRONMENTS = {"dev", "local", "test"}


def _normalize_db_url(db_url: str) -> str:
    # Render and other hosts often provide postgres:// or postgresql:// URLs.
    # Our runtime uses psycopg v3, so normalize to the SQLAlchemy psycopg dialect.
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+psycopg://", 1)
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return db_url


def _connect_args(db_url: str) -> dict:
    return {"check_same_thread": False} if db_url.startswith("sqlite") else {}


def _build_engine(db_url: str):
    normalized_url = _normalize_db_url(db_url)
    return create_engine(
        normalized_url,
        pool_pre_ping=True,
        connect_args=_connect_args(normalized_url),
    )


def _resolve_engine():
    primary_url = _normalize_db_url(settings.DATABASE_URL)
    primary_engine = _build_engine(primary_url)
    env = settings.ENVIRONMENT.lower()
    allow_fallback = env in DEV_ENVIRONMENTS and bool(settings.DB_FALLBACK_URL)
    if not allow_fallback:
        return primary_engine, primary_url

    try:
        with primary_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return primary_engine, primary_url
    except SQLAlchemyError:
        primary_engine.dispose()
        fallback_url = _normalize_db_url(settings.DB_FALLBACK_URL)
        fallback_engine = _build_engine(fallback_url)
        return fallback_engine, fallback_url


engine, ACTIVE_DATABASE_URL = _resolve_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
