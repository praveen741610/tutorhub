from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contact_notifications import send_contact_alerts
from app.core.deps import get_current_user, get_db
from app.models.contact_message import ContactMessage
from app.models.user import User
from app.schemas.contact import (
    ContactMessageCreateIn,
    ContactMessageOut,
    ContactMessageStatsOut,
    ContactMessageStatusIn,
)

router = APIRouter(prefix="/contact/messages", tags=["contact"])


def _serialize_message(row: ContactMessage) -> ContactMessageOut:
    return ContactMessageOut(
        id=row.id,
        parent_name=row.parent_name,
        email=row.email,
        country=row.country,
        preferred_contact_window=row.preferred_contact_window,
        message=row.message,
        source_page=row.source_page,
        status=row.status,
        created_at=row.created_at,
    )


def _require_contact_dashboard_access(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"parent", "tutor"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.post("", response_model=ContactMessageOut, status_code=201)
def submit_contact_message(
    payload: ContactMessageCreateIn,
    db: Session = Depends(get_db),
) -> ContactMessageOut:
    row = ContactMessage(
        parent_name=payload.parent_name.strip(),
        email=str(payload.email).strip().lower(),
        country=payload.country.strip(),
        preferred_contact_window=payload.preferred_contact_window.strip(),
        message=payload.message.strip(),
        source_page=payload.source_page.strip() or "/contact",
        status="new",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        send_contact_alerts(row)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Message saved (Ref #{row.id}) but delivery failed: {exc}",
        ) from exc

    return _serialize_message(row)


@router.get("/stats", response_model=ContactMessageStatsOut)
def contact_message_stats(
    _user: User = Depends(_require_contact_dashboard_access),
    db: Session = Depends(get_db),
) -> ContactMessageStatsOut:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)

    total_messages = db.execute(select(func.count(ContactMessage.id))).scalar_one()
    new_messages = db.execute(
        select(func.count(ContactMessage.id)).where(ContactMessage.status == "new")
    ).scalar_one()
    today_messages = db.execute(
        select(func.count(ContactMessage.id)).where(ContactMessage.created_at >= today_start)
    ).scalar_one()
    last_7_days_messages = db.execute(
        select(func.count(ContactMessage.id)).where(ContactMessage.created_at >= week_start)
    ).scalar_one()

    return ContactMessageStatsOut(
        total_messages=total_messages,
        new_messages=new_messages,
        today_messages=today_messages,
        last_7_days_messages=last_7_days_messages,
    )


@router.get("", response_model=list[ContactMessageOut])
def list_contact_messages(
    _user: User = Depends(_require_contact_dashboard_access),
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, pattern="^(new|read|replied)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ContactMessageOut]:
    stmt = select(ContactMessage).order_by(ContactMessage.created_at.desc())
    if status:
        stmt = stmt.where(ContactMessage.status == status)
    rows = db.execute(stmt.offset(offset).limit(limit)).scalars().all()
    return [_serialize_message(row) for row in rows]


@router.post("/{message_id}/status", response_model=ContactMessageOut)
def update_contact_message_status(
    message_id: int,
    payload: ContactMessageStatusIn,
    _user: User = Depends(_require_contact_dashboard_access),
    db: Session = Depends(get_db),
) -> ContactMessageOut:
    row = db.get(ContactMessage, message_id)
    if not row:
        raise HTTPException(status_code=404, detail="Contact message not found")

    row.status = payload.status
    db.commit()
    db.refresh(row)
    return _serialize_message(row)
