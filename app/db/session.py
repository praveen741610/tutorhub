from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DEV_ENVIRONMENTS = {"dev", "local", "test"}


def _connect_args(db_url: str) -> dict:
    return {"check_same_thread": False} if db_url.startswith("sqlite") else {}


def _build_engine(db_url: str):
    return create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=_connect_args(db_url),
    )


def _resolve_engine():
    primary_engine = _build_engine(settings.DATABASE_URL)
    env = settings.ENVIRONMENT.lower()
    allow_fallback = env in DEV_ENVIRONMENTS and bool(settings.DB_FALLBACK_URL)
    if not allow_fallback:
        return primary_engine, settings.DATABASE_URL

    try:
        with primary_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return primary_engine, settings.DATABASE_URL
    except SQLAlchemyError:
        primary_engine.dispose()
        fallback_engine = _build_engine(settings.DB_FALLBACK_URL)
        return fallback_engine, settings.DB_FALLBACK_URL


engine, ACTIVE_DATABASE_URL = _resolve_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
