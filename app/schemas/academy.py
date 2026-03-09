from datetime import date, datetime
from pydantic import BaseModel, Field


class TrialBookingIn(BaseModel):
    program_slug: str = Field(min_length=2, max_length=64)
    booking_kind: str = Field(pattern="^(trial|consultation)$")
    slot_start: datetime
    slot_end: datetime
    child_name: str = Field(default="", max_length=120)
    child_grade: str = Field(default="", max_length=40)
    timezone: str = Field(default="America/New_York", max_length=64)
    preferred_tutor_id: int | None = Field(default=None, ge=1)
    notes: str = Field(default="", max_length=1000)


class TrialBookingOut(BaseModel):
    id: int
    parent_id: int
    tutor_id: int
    booking_kind: str
    program_slug: str
    child_name: str
    child_grade: str
    timezone: str
    slot_start: datetime
    slot_end: datetime
    meeting_link: str
    status: str
    notes: str


class EnrollmentCreateIn(BaseModel):
    program_slug: str = Field(min_length=2, max_length=64)
    child_name: str = Field(min_length=2, max_length=120)
    child_grade: str = Field(min_length=1, max_length=40)
    plan_type: str = Field(pattern="^(monthly|quarterly|annual)$")
    start_date: date | None = None


class EnrollmentOut(BaseModel):
    id: int
    parent_id: int
    program_slug: str
    child_name: str
    child_grade: str
    plan_type: str
    billing_cycle_months: int
    list_price_usd: int
    plan_discount_percent: int
    bundle_discount_percent: int
    final_price_usd: int
    status: str
    start_date: date
    next_billing_date: date


class ProgramCatalogOut(BaseModel):
    verticals: list[dict]
    plans: dict[str, dict]
    bundle_discount_percent: int
