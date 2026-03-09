from datetime import datetime
from pydantic import BaseModel, Field


class TutorProfileUpsert(BaseModel):
    headline: str = Field(default="", max_length=120)
    bio: str = Field(default="", max_length=2000)
    hourly_rate: int = Field(default=0, ge=0, le=1000)
    subjects: str = Field(default="", description="comma-separated e.g. math,physics")
    languages: str = Field(default="", description="comma-separated e.g. english,hindi")
    timezone: str = Field(default="UTC")


class TutorProfileOut(TutorProfileUpsert):
    is_active: bool = True


class TutorPublic(BaseModel):
    tutor_id: int
    name: str
    headline: str
    hourly_rate: int
    subjects: str
    languages: str
    timezone: str


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SessionNoteCreate(BaseModel):
    enrollment_id: int = Field(ge=1)
    session_start: datetime
    session_end: datetime
    attendance_status: str = Field(pattern="^(attended|missed|rescheduled)$")
    note_summary: str = Field(default="", max_length=1000)
    homework: str = Field(default="", max_length=1000)
    meeting_link: str = Field(default="", max_length=255)
