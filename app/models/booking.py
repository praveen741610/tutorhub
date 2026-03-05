from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    slot_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    slot_end: Mapped[datetime] = mapped_column(DateTime)

    message: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(20), default="requested")  # requested/accepted/rejected/canceled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)