import os
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path(f"test_tutorhub_{uuid.uuid4().hex}.db")

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB_PATH.as_posix()}"
os.environ["DB_FALLBACK_URL"] = f"sqlite:///./{TEST_DB_PATH.as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["JWT_ALG"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "5"
os.environ["REFRESH_TOKEN_EXPIRE_MINUTES"] = "60"

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
