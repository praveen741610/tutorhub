from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, require_role
from app.models.user import User
from app.models.tutor import TutorProfile, AvailabilitySlot
from app.models.booking import BookingRequest
from app.schemas.tutor import TutorProfileOut, TutorProfileUpsert, SlotCreate

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.get("/profile", response_model=TutorProfileOut)
def get_profile(
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    profile = db.execute(select(TutorProfile).where(TutorProfile.user_id == tutor.id)).scalar_one_or_none()
    if not profile:
        return TutorProfileOut()

    return TutorProfileOut(
        headline=profile.headline,
        bio=profile.bio,
        hourly_rate=profile.hourly_rate,
        subjects=profile.subjects,
        languages=profile.languages,
        timezone=profile.timezone,
        is_active=profile.is_active,
    )


@router.post("/profile")
def upsert_profile(
    payload: TutorProfileUpsert,
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    profile = db.execute(select(TutorProfile).where(TutorProfile.user_id == tutor.id)).scalar_one_or_none()
    if not profile:
        profile = TutorProfile(user_id=tutor.id)
        db.add(profile)

    profile.headline = payload.headline
    profile.bio = payload.bio
    profile.hourly_rate = payload.hourly_rate
    profile.subjects = payload.subjects
    profile.languages = payload.languages
    profile.timezone = payload.timezone

    db.commit()
    return {"ok": True}


@router.post("/availability")
def add_slot(
    payload: SlotCreate,
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    slot = AvailabilitySlot(
        tutor_id=tutor.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_booked=False,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return {"id": slot.id}


@router.get("/requests")
def my_requests(
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(BookingRequest, User.name)
        .join(User, User.id == BookingRequest.student_id)
        .where(BookingRequest.tutor_id == tutor.id)
    ).all()
    return [
        {
            "id": r[0].id,
            "student_id": r[0].student_id,
            "student_name": r[1],
            "slot_start": r[0].slot_start,
            "slot_end": r[0].slot_end,
            "status": r[0].status,
            "message": r[0].message,
        }
        for r in rows
    ]


@router.post("/requests/{request_id}/accept")
def accept_request(
    request_id: int,
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    req = db.get(BookingRequest, request_id)
    if not req or req.tutor_id != tutor.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "requested":
        raise HTTPException(status_code=400, detail="Only requested bookings can be accepted")

    req.status = "accepted"
    db.commit()
    return {"ok": True}


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    tutor: User = Depends(require_role("tutor")),
    db: Session = Depends(get_db),
):
    req = db.get(BookingRequest, request_id)
    if not req or req.tutor_id != tutor.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "requested":
        raise HTTPException(status_code=400, detail="Only requested bookings can be rejected")

    req.status = "rejected"
    db.commit()
    return {"ok": True}
