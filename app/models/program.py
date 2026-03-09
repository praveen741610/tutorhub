from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrialBooking(Base):
    __tablename__ = "trial_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    booking_kind: Mapped[str] = mapped_column(String(20), default="trial")
    program_slug: Mapped[str] = mapped_column(String(64))
    child_name: Mapped[str] = mapped_column(String(120), default="")
    child_grade: Mapped[str] = mapped_column(String(40), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    slot_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    slot_end: Mapped[datetime] = mapped_column(DateTime)
    meeting_link: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    notes: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProgramEnrollment(Base):
    __tablename__ = "program_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    program_slug: Mapped[str] = mapped_column(String(64), index=True)
    child_name: Mapped[str] = mapped_column(String(120))
    child_grade: Mapped[str] = mapped_column(String(40))
    plan_type: Mapped[str] = mapped_column(String(20))
    billing_cycle_months: Mapped[int] = mapped_column(Integer)
    list_price_usd: Mapped[int] = mapped_column(Integer)
    plan_discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    bundle_discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    final_price_usd: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    next_billing_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionNote(Base):
    __tablename__ = "session_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), index=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    session_end: Mapped[datetime] = mapped_column(DateTime)
    attendance_status: Mapped[str] = mapped_column(String(20), default="attended")
    note_summary: Mapped[str] = mapped_column(String(1000), default="")
    homework: Mapped[str] = mapped_column(String(1000), default="")
    meeting_link: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
