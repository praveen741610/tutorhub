from collections import defaultdict
from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.academy_catalog import (
    BOOKING_KIND_DURATION_MINUTES,
    BUNDLE_DISCOUNT_PERCENT,
    PLAN_DISCOUNT_PERCENT,
    PLAN_TO_MONTHS,
    PROGRAM_BY_SLUG,
    PROGRAM_CATALOG,
)
from app.core.deps import get_db, require_role
from app.models.program import ProgramEnrollment, SessionNote, TrialBooking
from app.models.tutor import AvailabilitySlot, TutorProfile
from app.models.user import User
from app.schemas.academy import (
    EnrollmentCreateIn,
    EnrollmentOut,
    ProgramCatalogOut,
    TrialBookingIn,
    TrialBookingOut,
)

router = APIRouter(prefix="/academy", tags=["academy"])


def _require_parent_consent(parent: User) -> None:
    if not parent.coppa_consent_given:
        raise HTTPException(status_code=400, detail="COPPA consent is required before storing child data")


def _serialize_trial(trial: TrialBooking) -> TrialBookingOut:
    return TrialBookingOut(
        id=trial.id,
        parent_id=trial.parent_id,
        tutor_id=trial.tutor_id,
        booking_kind=trial.booking_kind,
        program_slug=trial.program_slug,
        child_name=trial.child_name,
        child_grade=trial.child_grade,
        timezone=trial.timezone,
        slot_start=trial.slot_start,
        slot_end=trial.slot_end,
        meeting_link=trial.meeting_link,
        status=trial.status,
        notes=trial.notes,
    )


def _serialize_enrollment(enrollment: ProgramEnrollment) -> EnrollmentOut:
    return EnrollmentOut(
        id=enrollment.id,
        parent_id=enrollment.parent_id,
        program_slug=enrollment.program_slug,
        child_name=enrollment.child_name,
        child_grade=enrollment.child_grade,
        plan_type=enrollment.plan_type,
        billing_cycle_months=enrollment.billing_cycle_months,
        list_price_usd=enrollment.list_price_usd,
        plan_discount_percent=enrollment.plan_discount_percent,
        bundle_discount_percent=enrollment.bundle_discount_percent,
        final_price_usd=enrollment.final_price_usd,
        status=enrollment.status,
        start_date=enrollment.start_date,
        next_billing_date=enrollment.next_billing_date,
    )


@router.get("/programs", response_model=ProgramCatalogOut)
def list_program_catalog() -> ProgramCatalogOut:
    return ProgramCatalogOut(
        verticals=PROGRAM_CATALOG,
        plans={
            "monthly": {"cycle_months": 1, "discount_percent": PLAN_DISCOUNT_PERCENT["monthly"]},
            "quarterly": {"cycle_months": 3, "discount_percent": PLAN_DISCOUNT_PERCENT["quarterly"]},
            "annual": {"cycle_months": 12, "discount_percent": PLAN_DISCOUNT_PERCENT["annual"]},
        },
        bundle_discount_percent=BUNDLE_DISCOUNT_PERCENT,
    )


@router.post("/trials/book", response_model=TrialBookingOut)
def book_trial_or_consultation(
    payload: TrialBookingIn,
    parent: User = Depends(require_role("parent")),
    db: Session = Depends(get_db),
) -> TrialBookingOut:
    _require_parent_consent(parent)
    if payload.program_slug not in PROGRAM_BY_SLUG:
        raise HTTPException(status_code=404, detail="Program not found")
    if payload.slot_end <= payload.slot_start:
        raise HTTPException(status_code=400, detail="slot_end must be after slot_start")
    if payload.booking_kind == "trial" and not payload.child_name.strip():
        raise HTTPException(status_code=400, detail="child_name is required for trial bookings")

    duration_minutes = (payload.slot_end - payload.slot_start).total_seconds() / 60.0
    expected_minutes = BOOKING_KIND_DURATION_MINUTES[payload.booking_kind]
    if abs(duration_minutes - expected_minutes) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"{payload.booking_kind} bookings must be exactly {expected_minutes} minutes",
        )

    slot_stmt = (
        select(AvailabilitySlot)
        .join(User, User.id == AvailabilitySlot.tutor_id)
        .join(TutorProfile, TutorProfile.user_id == User.id)
        .where(
            User.role == "tutor",
            TutorProfile.is_active.is_(True),
            AvailabilitySlot.is_booked.is_(False),
            AvailabilitySlot.start_time <= payload.slot_start,
            AvailabilitySlot.end_time >= payload.slot_end,
        )
        .order_by(AvailabilitySlot.start_time.asc())
    )
    if payload.preferred_tutor_id is not None:
        slot_stmt = slot_stmt.where(AvailabilitySlot.tutor_id == payload.preferred_tutor_id)

    chosen_slot = db.execute(slot_stmt).scalars().first()
    if not chosen_slot:
        raise HTTPException(status_code=409, detail="No tutor slot available for the selected time")

    chosen_slot.is_booked = True
    booking = TrialBooking(
        parent_id=parent.id,
        tutor_id=chosen_slot.tutor_id,
        booking_kind=payload.booking_kind,
        program_slug=payload.program_slug,
        child_name=payload.child_name.strip(),
        child_grade=payload.child_grade.strip(),
        timezone=payload.timezone.strip() or "America/New_York",
        slot_start=payload.slot_start,
        slot_end=payload.slot_end,
        meeting_link=f"https://meet.aviacademy.live/{uuid4().hex[:12]}",
        status="scheduled",
        notes=payload.notes.strip(),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return _serialize_trial(booking)


@router.get("/trials/my", response_model=list[TrialBookingOut])
def my_trials(
    parent: User = Depends(require_role("parent")),
    db: Session = Depends(get_db),
) -> list[TrialBookingOut]:
    rows = db.execute(
        select(TrialBooking)
        .where(TrialBooking.parent_id == parent.id)
        .order_by(TrialBooking.slot_start.desc())
    ).scalars().all()
    return [_serialize_trial(row) for row in rows]


@router.post("/trials/{trial_id}/cancel", response_model=TrialBookingOut)
def cancel_trial(
    trial_id: int,
    parent: User = Depends(require_role("parent")),
    db: Session = Depends(get_db),
) -> TrialBookingOut:
    trial = db.get(TrialBooking, trial_id)
    if not trial or trial.parent_id != parent.id:
        raise HTTPException(status_code=404, detail="Trial booking not found")
    if trial.status != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled trial bookings can be canceled")

    trial.status = "canceled"
    db.commit()
    db.refresh(trial)
    return _serialize_trial(trial)


@router.post("/enrollments", response_model=EnrollmentOut)
def create_program_enrollment(
    payload: EnrollmentCreateIn,
    parent: User = Depends(require_role("parent")),
    db: Session = Depends(get_db),
) -> EnrollmentOut:
    _require_parent_consent(parent)
    program = PROGRAM_BY_SLUG.get(payload.program_slug)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    cycle_months = PLAN_TO_MONTHS[payload.plan_type]
    plan_discount = PLAN_DISCOUNT_PERCENT[payload.plan_type]
    list_price = program["starting_monthly_usd"] * cycle_months
    after_plan_discount = round(list_price * (100 - plan_discount) / 100)

    active_count = db.execute(
        select(func.count(ProgramEnrollment.id)).where(
            ProgramEnrollment.parent_id == parent.id,
            ProgramEnrollment.status == "active",
        )
    ).scalar_one()
    bundle_discount = BUNDLE_DISCOUNT_PERCENT if active_count >= 1 else 0
    final_price = round(after_plan_discount * (100 - bundle_discount) / 100)

    start = payload.start_date or date.today()
    enrollment = ProgramEnrollment(
        parent_id=parent.id,
        program_slug=payload.program_slug,
        child_name=payload.child_name.strip(),
        child_grade=payload.child_grade.strip(),
        plan_type=payload.plan_type,
        billing_cycle_months=cycle_months,
        list_price_usd=list_price,
        plan_discount_percent=plan_discount,
        bundle_discount_percent=bundle_discount,
        final_price_usd=final_price,
        status="active",
        start_date=start,
        next_billing_date=start + timedelta(days=30 * cycle_months),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _serialize_enrollment(enrollment)


@router.get("/dashboard")
def parent_dashboard(
    parent: User = Depends(require_role("parent")),
    db: Session = Depends(get_db),
) -> dict:
    enrollments = db.execute(
        select(ProgramEnrollment)
        .where(ProgramEnrollment.parent_id == parent.id)
        .order_by(ProgramEnrollment.created_at.desc())
    ).scalars().all()
    notes = db.execute(
        select(SessionNote)
        .where(SessionNote.parent_id == parent.id)
        .order_by(SessionNote.session_start.desc())
    ).scalars().all()
    trials = db.execute(
        select(TrialBooking)
        .where(TrialBooking.parent_id == parent.id)
        .order_by(TrialBooking.slot_start.desc())
    ).scalars().all()

    now = datetime.utcnow()
    month_start = datetime(year=now.year, month=now.month, day=1)
    notes_by_enrollment: dict[int, list[SessionNote]] = defaultdict(list)
    for note in notes:
        notes_by_enrollment[note.enrollment_id].append(note)

    progress_reports = []
    for enrollment in enrollments:
        monthly_notes = [
            note
            for note in notes_by_enrollment.get(enrollment.id, [])
            if note.session_start >= month_start
        ]
        attended_count = sum(1 for note in monthly_notes if note.attendance_status == "attended")
        missed_count = sum(1 for note in monthly_notes if note.attendance_status == "missed")
        latest_summary = monthly_notes[0].note_summary if monthly_notes else ""
        progress_reports.append(
            {
                "enrollment_id": enrollment.id,
                "program_slug": enrollment.program_slug,
                "child_name": enrollment.child_name,
                "month": month_start.strftime("%Y-%m"),
                "attended_sessions": attended_count,
                "missed_sessions": missed_count,
                "latest_summary": latest_summary,
            }
        )

    upcoming_sessions = []
    session_history = []
    for trial in trials:
        row = {
            "type": trial.booking_kind,
            "id": trial.id,
            "program_slug": trial.program_slug,
            "child_name": trial.child_name,
            "slot_start": trial.slot_start,
            "slot_end": trial.slot_end,
            "status": trial.status,
            "meeting_link": trial.meeting_link,
        }
        if trial.slot_start >= now and trial.status == "scheduled":
            upcoming_sessions.append(row)
        else:
            session_history.append(row)

    for note in notes:
        row = {
            "type": "session_note",
            "id": note.id,
            "enrollment_id": note.enrollment_id,
            "attendance_status": note.attendance_status,
            "session_start": note.session_start,
            "session_end": note.session_end,
            "summary": note.note_summary,
            "homework": note.homework,
            "meeting_link": note.meeting_link,
        }
        if note.session_start >= now:
            upcoming_sessions.append(row)
        else:
            session_history.append(row)

    active_enrollments = [enrollment for enrollment in enrollments if enrollment.status == "active"]

    return {
        "parent": {
            "id": parent.id,
            "name": parent.name,
            "email": parent.email,
            "coppa_consent_given": parent.coppa_consent_given,
            "coppa_consent_at": parent.coppa_consent_at,
        },
        "enrolled_programs": [
            {
                **_serialize_enrollment(enrollment).model_dump(),
                "program_name": PROGRAM_BY_SLUG.get(enrollment.program_slug, {}).get("name", enrollment.program_slug),
            }
            for enrollment in enrollments
        ],
        "upcoming_sessions": sorted(upcoming_sessions, key=lambda row: row.get("slot_start") or row.get("session_start")),
        "session_history": sorted(
            session_history,
            key=lambda row: row.get("slot_start") or row.get("session_start"),
            reverse=True,
        ),
        "progress_reports": progress_reports,
        "billing": {
            "active_subscriptions": len(active_enrollments),
            "current_cycle_total_usd": sum(enrollment.final_price_usd for enrollment in active_enrollments),
            "discounted_subscriptions": sum(
                1
                for enrollment in active_enrollments
                if enrollment.plan_discount_percent > 0 or enrollment.bundle_discount_percent > 0
            ),
        },
    }
