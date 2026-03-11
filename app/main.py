from contextlib import asynccontextmanager
import json
import logging
from time import perf_counter
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.routers import academy, auth, bookings, contact_messages, tutor_dashboard, tutors, web
from app.db.base import Base
from app.db.session import ACTIVE_DATABASE_URL, engine
from app.models import booking, contact_message, program, refresh_session, tutor, user  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OFFLINE_REDOC_FILE = STATIC_DIR / "docs" / "redoc-offline.html"
HTTP_LOGGER = logging.getLogger("tutorhub.http")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    env = settings.ENVIRONMENT.lower()
    is_dev_like = env in {"dev", "local", "test"}
    is_sqlite = ACTIVE_DATABASE_URL.startswith("sqlite")
    if settings.AUTO_CREATE_TABLES and (is_dev_like or is_sqlite):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TutorHub API", version="0.1.0", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(tutors.router)
app.include_router(tutor_dashboard.router)
app.include_router(bookings.router)
app.include_router(academy.router)
app.include_router(contact_messages.router)
app.include_router(web.router)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        HTTP_LOGGER.exception(
            json.dumps(
                {
                    "event": "request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": request.url.query,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                }
            )
        )
        raise

    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    HTTP_LOGGER.info(
        json.dumps(
            {
                "event": "request_complete",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


def _error_response(status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _error_response(
        status_code=exc.status_code,
        code="http_error",
        message=message,
        details=exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="validation_error",
        message="Invalid request payload",
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return _error_response(
        status_code=500,
        code="internal_server_error",
        message="Internal server error",
    )


@app.get("/docs", include_in_schema=False)
def custom_docs() -> HTMLResponse:
    swagger = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_ui_parameters={"persistAuthorization": True},
    )

    auth_sync_js = """
<script>
(function () {
  var accessKey = "tutorhub_access_token";
  var refreshKey = "tutorhub_refresh_token";

  function parseTokenPayload(token) {
    try {
      var body = token.split(".")[1];
      var base64 = body.replace(/-/g, "+").replace(/_/g, "/");
      var json = window.atob(base64);
      return JSON.parse(json);
    } catch (_err) {
      return null;
    }
  }

  function isExpired(token, skewSeconds) {
    if (!token) {
      return true;
    }
    var payload = parseTokenPayload(token);
    if (!payload || !payload.exp) {
      return true;
    }
    var now = Math.floor(Date.now() / 1000);
    return payload.exp <= (now + (skewSeconds || 0));
  }

  async function refreshAccessToken() {
    var refreshToken = window.localStorage.getItem(refreshKey);
    if (!refreshToken || isExpired(refreshToken, 30)) {
      return null;
    }

    try {
      var response = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      if (!response.ok) {
        return null;
      }
      var data = await response.json();
      if (!data || !data.access_token) {
        return null;
      }
      window.localStorage.setItem(accessKey, data.access_token);
      if (data.refresh_token) {
        window.localStorage.setItem(refreshKey, data.refresh_token);
      }
      if (data.role) {
        window.localStorage.setItem("tutorhub_user_role", data.role);
      }
      return data.access_token;
    } catch (_err) {
      return null;
    }
  }

  async function getValidAccessToken() {
    var accessToken = window.localStorage.getItem(accessKey);
    if (accessToken && !isExpired(accessToken, 30)) {
      return accessToken;
    }
    return await refreshAccessToken();
  }

  async function applyToken() {
    var token = await getValidAccessToken();
    if (!token || !window.ui || typeof window.ui.preauthorizeApiKey !== "function") {
      return;
    }
    try {
      window.ui.preauthorizeApiKey("HTTPBearer", token);
    } catch (_err) {}
  }

  var checks = 0;
  var timer = window.setInterval(async function () {
    checks += 1;
    if (window.ui) {
      await applyToken();
      window.clearInterval(timer);
      return;
    }
    if (checks > 40) {
      window.clearInterval(timer);
    }
  }, 250);

  window.addEventListener("storage", function (event) {
    if (event.key === accessKey || event.key === refreshKey) {
      applyToken();
    }
  });
})();
</script>
"""

    return HTMLResponse(swagger.body.decode("utf-8") + auth_sync_js)


@app.get("/redoc", include_in_schema=False)
def offline_redoc():
    return FileResponse(OFFLINE_REDOC_FILE)


@app.get("/health", tags=["default"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok", "database": "up", "environment": settings.ENVIRONMENT.lower()}


@app.get("/api")
def root():
    return {"message": "TutorHub API is running"}
