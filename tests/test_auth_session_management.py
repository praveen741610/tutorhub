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


def assert_error_envelope(response, status_code: int):
    assert response.status_code == status_code
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"]
    assert payload["error"]["message"]


def test_refresh_rotation_logout_and_logout_all(client):
    password = "Password123"
    email = unique_email("session_flow")
    register_user(client, name="Session User", email=email, password=password, role="student")

    login_one = login_user(client, email=email, password=password)
    refresh_one = login_one["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_one})
    assert refresh_response.status_code == 200, refresh_response.text
    refresh_two = refresh_response.json()["refresh_token"]

    replay_old_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_one})
    assert_error_envelope(replay_old_refresh, 401)
    assert "revoked" in replay_old_refresh.json()["error"]["message"].lower()

    logout = client.post("/auth/logout", json={"refresh_token": refresh_two})
    assert logout.status_code == 200
    assert logout.json()["ok"] is True

    after_logout_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_two})
    assert_error_envelope(after_logout_refresh, 401)
    assert "revoked" in after_logout_refresh.json()["error"]["message"].lower()

    login_two = login_user(client, email=email, password=password)
    refresh_three = login_two["refresh_token"]
    logout_all = client.post("/auth/logout-all", json={"refresh_token": refresh_three})
    assert logout_all.status_code == 200, logout_all.text
    assert logout_all.json()["ok"] is True
    assert logout_all.json()["revoked_sessions"] >= 1

    after_logout_all_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_three})
    assert_error_envelope(after_logout_all_refresh, 401)
    assert "revoked" in after_logout_all_refresh.json()["error"]["message"].lower()


def test_error_envelope_and_health_header(client):
    invalid_login = client.post(
        "/auth/login",
        data={
            "username": "missing@example.com",
            "password": "Password123",
        },
    )
    assert_error_envelope(invalid_login, 401)

    invalid_register = client.post(
        "/auth/register",
        json={
            "name": "A",
            "email": "bad_email",
            "password": "123",
            "role": "admin",
        },
    )
    assert_error_envelope(invalid_register, 422)
    assert invalid_register.json()["error"]["code"] == "validation_error"

    unauthenticated_bookings = client.get("/bookings/my")
    assert_error_envelope(unauthenticated_bookings, 401)

    health = client.get("/health")
    assert health.status_code == 200, health.text
    body = health.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert health.headers.get("x-request-id")


def test_logout_rejects_access_token_payload(client):
    password = "Password123"
    email = unique_email("logout_token_type")
    register_user(client, name="Logout Type", email=email, password=password, role="student")
    login = login_user(client, email=email, password=password)

    invalid_logout = client.post("/auth/logout", json={"refresh_token": login["access_token"]})
    assert_error_envelope(invalid_logout, 401)
    assert "invalid refresh token" in invalid_logout.json()["error"]["message"].lower()
