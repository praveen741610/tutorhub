from datetime import datetime
from sqlalchemy import ForeignKey, String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TutorProfile(Base):
    __tablename__ = "tutor_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    headline: Mapped[str] = mapped_column(String(120), default="")
    bio: Mapped[str] = mapped_column(String(2000), default="")
    hourly_rate: Mapped[int] = mapped_column(Integer, default=0)

    # MVP: store as comma-separated text (easy). Later: migrate to JSON/relations.
    subjects: Mapped[str] = mapped_column(String(500), default="")   # "math,physics"
    languages: Mapped[str] = mapped_column(String(200), default="")  # "english,hindi"
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # tutor user_id
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False)