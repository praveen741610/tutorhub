from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, require_role
from app.models.user import User
from app.models.booking import BookingRequest
from app.models.tutor import TutorProfile
from app.schemas.booking import BookingRequestIn, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/request", response_model=BookingOut)
def request_booking(
    payload: BookingRequestIn,
    student: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    tutor = db.get(User, payload.tutor_id)
    if not tutor or tutor.role != "tutor":
        raise HTTPException(status_code=404, detail="Tutor not found")

    profile = db.execute(select(TutorProfile).where(TutorProfile.user_id == tutor.id)).scalar_one_or_none()
    if not profile or not profile.is_active:
        raise HTTPException(status_code=400, detail="Tutor is not available")

    if payload.slot_end <= payload.slot_start:
        raise HTTPException(status_code=400, detail="slot_end must be after slot_start")

    req = BookingRequest(
        student_id=student.id,
        tutor_id=payload.tutor_id,
        slot_start=payload.slot_start,
        slot_end=payload.slot_end,
        message=payload.message,
        status="requested",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return BookingOut(
        id=req.id,
        tutor_id=req.tutor_id,
        student_id=req.student_id,
        slot_start=req.slot_start,
        slot_end=req.slot_end,
        status=req.status,
        message=req.message,
    )


@router.get("/my", response_model=list[BookingOut])
def my_booking_requests(
    student: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    rows = db.execute(select(BookingRequest).where(BookingRequest.student_id == student.id)).scalars().all()
    return [
        BookingOut(
            id=r.id,
            tutor_id=r.tutor_id,
            student_id=r.student_id,
            slot_start=r.slot_start,
            slot_end=r.slot_end,
            status=r.status,
            message=r.message,
        )
        for r in rows
    ]


@router.post("/{request_id}/cancel", response_model=BookingOut)
def cancel_booking_request(
    request_id: int,
    student: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    req = db.get(BookingRequest, request_id)
    if not req or req.student_id != student.id:
        raise HTTPException(status_code=404, detail="Booking request not found")
    if req.status != "requested":
        raise HTTPException(status_code=400, detail="Only requested bookings can be canceled")

    req.status = "canceled"
    db.commit()
    db.refresh(req)
    return BookingOut(
        id=req.id,
        tutor_id=req.tutor_id,
        student_id=req.student_id,
        slot_start=req.slot_start,
        slot_end=req.slot_end,
        status=req.status,
        message=req.message,
    )
