from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(include_in_schema=False)

BASE_DIR = Path(__file__).resolve().parent.parent
PAGES_DIR = BASE_DIR / "static" / "pages"
SITE_PAGES_DIR = PAGES_DIR / "site"


@router.get("/")
def site_home_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "home.html")


@router.get("/about")
def site_about_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "about.html")


@router.get("/programs")
def site_programs_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "programs.html")


@router.get("/methodology")
def site_methodology_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "methodology.html")


@router.get("/faculty")
def site_faculty_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "faculty.html")


@router.get("/admissions")
def site_admissions_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "admissions.html")


@router.get("/testimonials")
def site_testimonials_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "testimonials.html")


@router.get("/contact")
def site_contact_page() -> FileResponse:
    return FileResponse(SITE_PAGES_DIR / "contact.html")


@router.get("/login")
def login_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "login.html")


@router.get("/register")
def register_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "register.html")


@router.get("/student/home")
def student_home_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "student-home.html")


@router.get("/tutor/home")
def tutor_home_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "tutor-home.html")
