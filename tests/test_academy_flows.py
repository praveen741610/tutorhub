from datetime import datetime, timedelta
import time


def unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}@example.com"


def register_user(client, *, name: str, email: str, password: str, role: str, coppa_consent: bool = False):
    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": role,
            "coppa_consent": coppa_consent,
        },
    )
    return response


def login_user(client, *, email: str, password: str):
    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_parent_registration_requires_coppa_consent(client):
    password = "Password123"
    email = unique_email("parent_no_consent")

    no_consent = register_user(
        client,
        name="Parent No Consent",
        email=email,
        password=password,
        role="parent",
        coppa_consent=False,
    )
    assert no_consent.status_code == 400, no_consent.text
    assert "coppa" in no_consent.json()["error"]["message"].lower()

    with_consent = register_user(
        client,
        name="Parent Consent",
        email=unique_email("parent_consent"),
        password=password,
        role="parent",
        coppa_consent=True,
    )
    assert with_consent.status_code == 200, with_consent.text
    payload = with_consent.json()
    assert payload["role"] == "parent"
    assert payload["coppa_consent_given"] is True


def test_academy_trial_and_consultation_booking_flow(client):
    password = "Password123"

    tutor_email = unique_email("academy_tutor")
    parent_email = unique_email("academy_parent")

    tutor = register_user(
        client, name="Academy Tutor", email=tutor_email, password=password, role="tutor"
    )
    assert tutor.status_code == 200, tutor.text

    parent = register_user(
        client,
        name="Academy Parent",
        email=parent_email,
        password=password,
        role="parent",
        coppa_consent=True,
    )
    assert parent.status_code == 200, parent.text

    tutor_login = login_user(client, email=tutor_email, password=password)
    parent_login = login_user(client, email=parent_email, password=password)

    profile = client.post(
        "/tutor/profile",
        json={
            "headline": "Math and Inclusive Tutor",
            "bio": "Experienced educator",
            "hourly_rate": 40,
            "subjects": "math,inclusive",
            "languages": "english,hindi",
            "timezone": "America/New_York",
        },
        headers=auth_headers(tutor_login["access_token"]),
    )
    assert profile.status_code == 200, profile.text

    now = datetime.utcnow().replace(second=0, microsecond=0)
    trial_start = now + timedelta(hours=2)
    trial_end = trial_start + timedelta(minutes=45)
    consult_start = now + timedelta(hours=4)
    consult_end = consult_start + timedelta(minutes=30)

    slot_one = client.post(
        "/tutor/availability",
        json={"start_time": trial_start.isoformat(), "end_time": trial_end.isoformat()},
        headers=auth_headers(tutor_login["access_token"]),
    )
    slot_two = client.post(
        "/tutor/availability",
        json={"start_time": consult_start.isoformat(), "end_time": consult_end.isoformat()},
        headers=auth_headers(tutor_login["access_token"]),
    )
    assert slot_one.status_code == 200, slot_one.text
    assert slot_two.status_code == 200, slot_two.text

    catalog = client.get("/academy/programs")
    assert catalog.status_code == 200, catalog.text
    verticals = catalog.json()["verticals"]
    assert len(verticals) == 5
    assert any(v["slug"] == "inclusive-learning" for v in verticals)

    trial = client.post(
        "/academy/trials/book",
        json={
            "program_slug": "academic-excellence",
            "booking_kind": "trial",
            "slot_start": trial_start.isoformat(),
            "slot_end": trial_end.isoformat(),
            "child_name": "Arjun",
            "child_grade": "Grade 4",
            "timezone": "America/New_York",
            "preferred_tutor_id": tutor.json()["id"],
            "notes": "Needs support in fractions",
        },
        headers=auth_headers(parent_login["access_token"]),
    )
    assert trial.status_code == 200, trial.text
    trial_data = trial.json()
    assert trial_data["booking_kind"] == "trial"
    assert trial_data["meeting_link"].startswith("https://meet.aviacademy.live/")

    consultation = client.post(
        "/academy/trials/book",
        json={
            "program_slug": "inclusive-learning",
            "booking_kind": "consultation",
            "slot_start": consult_start.isoformat(),
            "slot_end": consult_end.isoformat(),
            "child_name": "",
            "child_grade": "Grade 2",
            "timezone": "America/New_York",
            "preferred_tutor_id": tutor.json()["id"],
            "notes": "Discuss focus and attention needs",
        },
        headers=auth_headers(parent_login["access_token"]),
    )
    assert consultation.status_code == 200, consultation.text
    consult_data = consultation.json()
    assert consult_data["booking_kind"] == "consultation"

    my_trials = client.get("/academy/trials/my", headers=auth_headers(parent_login["access_token"]))
    assert my_trials.status_code == 200, my_trials.text
    assert len(my_trials.json()) == 2


def test_parent_enrollment_bundle_discount_and_dashboard_progress(client):
    password = "Password123"
    tutor_email = unique_email("progress_tutor")
    parent_email = unique_email("progress_parent")

    tutor = register_user(client, name="Progress Tutor", email=tutor_email, password=password, role="tutor")
    parent = register_user(
        client,
        name="Progress Parent",
        email=parent_email,
        password=password,
        role="parent",
        coppa_consent=True,
    )
    assert tutor.status_code == 200, tutor.text
    assert parent.status_code == 200, parent.text

    tutor_login = login_user(client, email=tutor_email, password=password)
    parent_login = login_user(client, email=parent_email, password=password)

    first_enrollment = client.post(
        "/academy/enrollments",
        json={
            "program_slug": "academic-excellence",
            "child_name": "Ira",
            "child_grade": "Grade 5",
            "plan_type": "monthly",
        },
        headers=auth_headers(parent_login["access_token"]),
    )
    second_enrollment = client.post(
        "/academy/enrollments",
        json={
            "program_slug": "chess",
            "child_name": "Ira",
            "child_grade": "Grade 5",
            "plan_type": "monthly",
        },
        headers=auth_headers(parent_login["access_token"]),
    )
    assert first_enrollment.status_code == 200, first_enrollment.text
    assert second_enrollment.status_code == 200, second_enrollment.text
    assert first_enrollment.json()["bundle_discount_percent"] == 0
    assert second_enrollment.json()["bundle_discount_percent"] == 10

    enrollment_id = first_enrollment.json()["id"]
    note_response = client.post(
        "/tutor/session-notes",
        json={
            "enrollment_id": enrollment_id,
            "session_start": (datetime.utcnow() - timedelta(days=2, hours=1)).isoformat(),
            "session_end": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "attendance_status": "attended",
            "note_summary": "Strong improvement in number sense.",
            "homework": "Practice multiplication table 6 and 7.",
            "meeting_link": "https://zoom.example/session-1",
        },
        headers=auth_headers(tutor_login["access_token"]),
    )
    assert note_response.status_code == 200, note_response.text

    dashboard = client.get("/academy/dashboard", headers=auth_headers(parent_login["access_token"]))
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()

    assert body["parent"]["coppa_consent_given"] is True
    assert len(body["enrolled_programs"]) == 2
    assert body["billing"]["active_subscriptions"] == 2
    assert body["billing"]["current_cycle_total_usd"] > 0
    assert len(body["session_history"]) >= 1
    assert any(report["attended_sessions"] >= 1 for report in body["progress_reports"])
