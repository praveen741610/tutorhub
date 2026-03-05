from datetime import datetime
from pydantic import BaseModel, Field


class BookingRequestIn(BaseModel):
    tutor_id: int
    slot_start: datetime
    slot_end: datetime
    message: str = Field(default="", max_length=1000)


class BookingOut(BaseModel):
    id: int
    tutor_id: int
    student_id: int
    slot_start: datetime
    slot_end: datetime
    status: str
    message: str