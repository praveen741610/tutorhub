from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ContactMessageCreateIn(BaseModel):
    parent_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    country: str = Field(min_length=2, max_length=120)
    preferred_contact_window: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=5, max_length=2000)
    source_page: str = Field(default="/contact", max_length=120)


class ContactMessageStatusIn(BaseModel):
    status: str = Field(pattern="^(new|read|replied)$")


class ContactMessageOut(BaseModel):
    id: int
    parent_name: str
    email: EmailStr
    country: str
    preferred_contact_window: str
    message: str
    source_page: str
    status: str
    created_at: datetime


class ContactMessageStatsOut(BaseModel):
    total_messages: int
    new_messages: int
    today_messages: int
    last_7_days_messages: int
