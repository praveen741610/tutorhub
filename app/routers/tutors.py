from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.deps import get_db
from app.models.user import User
from app.models.tutor import TutorProfile
from app.schemas.tutor import TutorPublic

router = APIRouter(prefix="/tutors", tags=["tutors"])


@router.get("", response_model=list[TutorPublic])
def search_tutors(
    subject: str | None = None,
    language: str | None = None,
    min_rate: int | None = None,
    max_rate: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(User.id, User.name, TutorProfile.headline, TutorProfile.hourly_rate,
               TutorProfile.subjects, TutorProfile.languages, TutorProfile.timezone)
        .join(TutorProfile, TutorProfile.user_id == User.id)
        .where(and_(User.role == "tutor", TutorProfile.is_active == True))
    )

    if min_rate is not None:
        stmt = stmt.where(TutorProfile.hourly_rate >= min_rate)
    if max_rate is not None:
        stmt = stmt.where(TutorProfile.hourly_rate <= max_rate)
    if subject:
        stmt = stmt.where(TutorProfile.subjects.ilike(f"%{subject}%"))
    if language:
        stmt = stmt.where(TutorProfile.languages.ilike(f"%{language}%"))

    rows = db.execute(stmt).all()
    return [
        TutorPublic(
            tutor_id=r[0],
            name=r[1],
            headline=r[2],
            hourly_rate=r[3],
            subjects=r[4],
            languages=r[5],
            timezone=r[6],
        )
        for r in rows
    ]


@router.get("/{tutor_id}", response_model=TutorPublic)
def tutor_details(tutor_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(User.id, User.name, TutorProfile.headline, TutorProfile.hourly_rate,
               TutorProfile.subjects, TutorProfile.languages, TutorProfile.timezone)
        .join(TutorProfile, TutorProfile.user_id == User.id)
        .where(and_(User.id == tutor_id, User.role == "tutor"))
    )
    row = db.execute(stmt).first()
    if not row:
        return TutorPublic(
            tutor_id=tutor_id, name="", headline="", hourly_rate=0, subjects="", languages="", timezone="UTC"
        )
    r = row
    return TutorPublic(
        tutor_id=r[0], name=r[1], headline=r[2], hourly_rate=r[3], subjects=r[4], languages=r[5], timezone=r[6]
    )