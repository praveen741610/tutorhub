from datetime import datetime, timedelta
import time


def unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}@example.com"


def register_user(client, *, name: str, email: str, password: str, role: str):
    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


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


def test_register_login_and_refresh(client):
    password = "Password123"
    email = unique_email("student_auth")
    register_user(client, name="Student Auth", email=email, password=password, role="student")

    login = login_user(client, email=email, password=password)
    assert login["role"] == "student"
    assert login["token_type"] == "bearer"
    assert "access_token" in login and login["access_token"]
    assert "refresh_token" in login and login["refresh_token"]
    assert login["access_expires_in"] > 0
    assert login["refresh_expires_in"] > login["access_expires_in"]

    refresh = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refresh.status_code == 200, refresh.text
    refreshed = refresh.json()
    assert refreshed["access_token"] != login["access_token"]
    assert refreshed["refresh_token"] != login["refresh_token"]
    assert refreshed["role"] == "student"

    invalid_refresh = client.post("/auth/refresh", json={"refresh_token": login["access_token"]})
    assert invalid_refresh.status_code == 401
    body = invalid_refresh.json()
    assert body["error"]["code"] == "http_error"
    assert "refresh token" in body["error"]["message"].lower()


def test_booking_create_and_cancel_flow(client):
    password = "Password123"

    tutor_email = unique_email("tutor_cancel")
    student_email = unique_email("student_cancel")

    tutor = register_user(client, name="Tutor Cancel", email=tutor_email, password=password, role="tutor")
    register_user(client, name="Student Cancel", email=student_email, password=password, role="student")

    tutor_login = login_user(client, email=tutor_email, password=password)
    student_login = login_user(client, email=student_email, password=password)

    profile_payload = {
        "headline": "Math Tutor",
        "bio": "Teaches algebra and calculus",
        "hourly_rate": 30,
        "subjects": "math",
        "languages": "english",
        "timezone": "UTC",
    }
    profile = client.post(
        "/tutor/profile",
        json=profile_payload,
        headers=auth_headers(tutor_login["access_token"]),
    )
    assert profile.status_code == 200, profile.text

    start = (datetime.utcnow() + timedelta(hours=2)).replace(microsecond=0)
    end = start + timedelta(hours=1)
    create = client.post(
        "/bookings/request",
        json={
            "tutor_id": tutor["id"],
            "slot_start": start.isoformat(),
            "slot_end": end.isoformat(),
            "message": "Need help with calculus",
        },
        headers=auth_headers(student_login["access_token"]),
    )
    assert create.status_code == 200, create.text
    booking_id = create.json()["id"]

    cancel = client.post(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(student_login["access_token"]),
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "canceled"

    my_bookings = client.get("/bookings/my", headers=auth_headers(student_login["access_token"]))
    assert my_bookings.status_code == 200
    rows = my_bookings.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "canceled"


def test_tutor_accept_and_reject_flow(client):
    password = "Password123"

    tutor_email = unique_email("tutor_review")
    student_email = unique_email("student_review")

    tutor = register_user(client, name="Tutor Review", email=tutor_email, password=password, role="tutor")
    register_user(client, name="Student Review", email=student_email, password=password, role="student")

    tutor_login = login_user(client, email=tutor_email, password=password)
    student_login = login_user(client, email=student_email, password=password)

    client.post(
        "/tutor/profile",
        json={
            "headline": "Physics Tutor",
            "bio": "Physics and chemistry",
            "hourly_rate": 45,
            "subjects": "physics",
            "languages": "english",
            "timezone": "UTC",
        },
        headers=auth_headers(tutor_login["access_token"]),
    )

    now = datetime.utcnow().replace(microsecond=0)
    first_req = client.post(
        "/bookings/request",
        json={
            "tutor_id": tutor["id"],
            "slot_start": (now + timedelta(hours=2)).isoformat(),
            "slot_end": (now + timedelta(hours=3)).isoformat(),
            "message": "Request one",
        },
        headers=auth_headers(student_login["access_token"]),
    )
    second_req = client.post(
        "/bookings/request",
        json={
            "tutor_id": tutor["id"],
            "slot_start": (now + timedelta(hours=4)).isoformat(),
            "slot_end": (now + timedelta(hours=5)).isoformat(),
            "message": "Request two",
        },
        headers=auth_headers(student_login["access_token"]),
    )
    assert first_req.status_code == 200
    assert second_req.status_code == 200

    req_a = first_req.json()["id"]
    req_b = second_req.json()["id"]

    tutor_requests = client.get("/tutor/requests", headers=auth_headers(tutor_login["access_token"]))
    assert tutor_requests.status_code == 200, tutor_requests.text
    rows = tutor_requests.json()
    assert len(rows) == 2
    assert "student_name" in rows[0]

    accept = client.post(f"/tutor/requests/{req_a}/accept", headers=auth_headers(tutor_login["access_token"]))
    reject = client.post(f"/tutor/requests/{req_b}/reject", headers=auth_headers(tutor_login["access_token"]))
    assert accept.status_code == 200
    assert reject.status_code == 200

    my_bookings = client.get("/bookings/my", headers=auth_headers(student_login["access_token"]))
    assert my_bookings.status_code == 200
    status_map = {row["id"]: row["status"] for row in my_bookings.json()}
    assert status_map[req_a] == "accepted"
    assert status_map[req_b] == "rejected"


def test_role_based_access_control(client):
    password = "Password123"

    tutor_email = unique_email("tutor_role")
    student_email = unique_email("student_role")

    register_user(client, name="Tutor Role", email=tutor_email, password=password, role="tutor")
    register_user(client, name="Student Role", email=student_email, password=password, role="student")

    tutor_login = login_user(client, email=tutor_email, password=password)
    student_login = login_user(client, email=student_email, password=password)

    forbidden_for_student = client.post(
        "/tutor/profile",
        json={
            "headline": "Blocked",
            "bio": "",
            "hourly_rate": 10,
            "subjects": "",
            "languages": "",
            "timezone": "UTC",
        },
        headers=auth_headers(student_login["access_token"]),
    )
    assert forbidden_for_student.status_code == 403
    assert forbidden_for_student.json()["error"]["message"] == "Forbidden"

    forbidden_for_tutor = client.get("/bookings/my", headers=auth_headers(tutor_login["access_token"]))
    assert forbidden_for_tutor.status_code == 403
    assert forbidden_for_tutor.json()["error"]["message"] == "Forbidden"
