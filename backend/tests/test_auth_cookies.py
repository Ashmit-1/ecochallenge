"""Cookie session and CSRF behaviour used by the browser frontend."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

ACCESS_COOKIE = "ecochallenge_access"
CSRF_COOKIE = "ecochallenge_csrf"


def _register_cookie_session(client: TestClient):
    suffix = uuid4().hex[:8]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"cookie-{suffix}@example.com",
            "password": "a-cookie-password",
            "display_name": f"Cookie {suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response


def _set_cookie_header(response, name: str) -> str:
    headers = response.headers.get_list("set-cookie")
    return next(header for header in headers if header.startswith(f"{name}="))


def test_registration_sets_http_only_session_and_readable_csrf(client: TestClient):
    response = _register_cookie_session(client)

    access_header = _set_cookie_header(response, ACCESS_COOKIE)
    csrf_header = _set_cookie_header(response, CSRF_COOKIE)

    assert "HttpOnly" in access_header
    assert "HttpOnly" not in csrf_header  # the SPA must be able to read this one
    assert client.cookies.get(ACCESS_COOKIE)
    assert client.cookies.get(CSRF_COOKIE)

    me = client.get("/api/v1/auth/me")  # no Authorization header
    assert me.status_code == 200


def test_login_sets_a_cookie_session(client: TestClient, register):
    user = register("Cookie Login")
    client.cookies.clear()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": user.user["email"], "password": user.password},
    )
    assert response.status_code == 200
    assert client.cookies.get(ACCESS_COOKIE)
    assert client.get("/api/v1/auth/me").status_code == 200


def test_cookie_writes_require_the_csrf_header(client: TestClient, png):
    _register_cookie_session(client)
    csrf = client.cookies.get(CSRF_COOKIE)

    without_header = client.post(
        "/api/v1/challenges/bike-to-campus/submissions",
        files={"image": ("proof.png", png(), "image/png")},
    )
    assert without_header.status_code == 403
    assert "CSRF" in without_header.json()["detail"]

    wrong_header = client.post(
        "/api/v1/challenges/bike-to-campus/submissions",
        headers={"X-CSRF-Token": "not-the-token"},
        files={"image": ("proof.png", png(), "image/png")},
    )
    assert wrong_header.status_code == 403

    accepted = client.post(
        "/api/v1/challenges/bike-to-campus/submissions",
        headers={"X-CSRF-Token": csrf},
        files={"image": ("proof.png", png(), "image/png")},
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["submission"]["status"] == "approved"


def test_patch_requires_csrf_too(client: TestClient):
    _register_cookie_session(client)
    csrf = client.cookies.get(CSRF_COOKIE)

    assert client.patch("/api/v1/auth/me", json={"display_name": "No Csrf"}).status_code == 403
    assert (
        client.patch(
            "/api/v1/auth/me",
            json={"display_name": "With Csrf"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 200
    )


def test_logout_clears_the_session(client: TestClient):
    _register_cookie_session(client)
    csrf = client.cookies.get(CSRF_COOKIE)

    assert client.post("/api/v1/auth/logout").status_code == 403  # missing CSRF
    assert (
        client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me").status_code == 401


def test_bearer_auth_does_not_require_csrf(client: TestClient, register, submit):
    user = register("Bearer Client")
    # The fixture cleared cookies; bearer is the only credential.
    assert submit(user, "bike-to-campus").status_code == 201
