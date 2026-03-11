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


def test_contact_message_submission_and_stats(client):
    submit = client.post(
        "/contact/messages",
        json={
            "parent_name": "Priya Sharma",
            "email": "priya@example.com",
            "country": "USA",
            "preferred_contact_window": "USA/Canada timing",
            "message": "Need CBSE math and science classes.",
            "source_page": "/contact",
        },
    )
    assert submit.status_code == 201, submit.text
    row = submit.json()
    assert row["id"] >= 1
    assert row["status"] == "new"
    assert row["email"] == "priya@example.com"

    tutor_email = unique_email("tutor_contact_stats")
    register_user(client, name="Tutor Contact", email=tutor_email, password="Password123", role="tutor")
    tutor_login = login_user(client, email=tutor_email, password="Password123")

    stats = client.get("/contact/messages/stats", headers=auth_headers(tutor_login["access_token"]))
    assert stats.status_code == 200, stats.text
    metrics = stats.json()
    assert metrics["total_messages"] == 1
    assert metrics["new_messages"] == 1
    assert metrics["today_messages"] == 1
    assert metrics["last_7_days_messages"] == 1


def test_contact_message_stats_forbidden_for_student(client):
    submit = client.post(
        "/contact/messages",
        json={
            "parent_name": "Meena Gupta",
            "email": "meena@example.com",
            "country": "USA",
            "preferred_contact_window": "USA/Canada timing",
            "message": "Looking for inclusive learning consultation.",
            "source_page": "/contact",
        },
    )
    assert submit.status_code == 201

    student_email = unique_email("student_contact_stats")
    register_user(client, name="Student Contact", email=student_email, password="Password123", role="student")
    student_login = login_user(client, email=student_email, password="Password123")

    stats = client.get("/contact/messages/stats", headers=auth_headers(student_login["access_token"]))
    assert stats.status_code == 403, stats.text
    assert stats.json()["error"]["message"] == "Forbidden"


def test_contact_message_returns_502_when_delivery_fails(client, monkeypatch):
    def _boom(_message):
        raise RuntimeError("smtp timeout")

    monkeypatch.setattr("app.routers.contact_messages.send_contact_alerts", _boom)
    submit = client.post(
        "/contact/messages",
        json={
            "parent_name": "Delivery Failure",
            "email": "failure@example.com",
            "country": "USA",
            "preferred_contact_window": "USA/Canada timing",
            "message": "Please contact us about science classes.",
            "source_page": "/contact",
        },
    )
    assert submit.status_code == 502, submit.text
    body = submit.json()
    assert body["error"]["code"] == "http_error"
    assert "Message saved" in body["error"]["message"]
    assert "delivery failed" in body["error"]["message"]
