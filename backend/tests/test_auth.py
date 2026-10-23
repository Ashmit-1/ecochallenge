"""Authentication and account endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_returns_token_and_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "New.Student@Example.com",
            "password": "a-good-password",
            "display_name": "New Student",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "new.student@example.com"  # normalised
    assert body["user"]["points_total"] == 0


def test_duplicate_email_is_rejected_case_insensitively(client: TestClient, register):
    existing = register("First Person", email="taken@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "TAKEN@example.com",
            "password": "another-password",
            "display_name": "Someone Else",
        },
    )
    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()
    assert existing.user["email"] == "taken@example.com"


def test_duplicate_display_name_is_rejected_case_insensitively(client: TestClient, register):
    register("Ashmit")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "password": "another-password",
            "display_name": "ashmit",
        },
    )
    assert response.status_code == 409
    assert "display name" in response.json()["detail"].lower()


def test_short_password_is_rejected(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short", "display_name": "Short Pass"},
    )
    assert response.status_code == 422


def test_login_success_and_failure(client: TestClient, register):
    user = register("Login User", email="login@example.com")

    ok = client.post(
        "/api/v1/auth/login",
        data={"username": "LOGIN@example.com", "password": user.password},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Incorrect email or password."


def test_unknown_email_login_is_401_without_leaking_existence(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_me_requires_a_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_invalid_token_is_401(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, register):
    user = register("Me User")
    response = client.get("/api/v1/auth/me", headers=user.headers)
    assert response.status_code == 200
    assert response.json()["display_name"] == "Me User"


def test_patch_display_name(client: TestClient, register):
    user = register("Old Name")
    response = client.patch(
        "/api/v1/auth/me", headers=user.headers, json={"display_name": "New Name"}
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"


def test_patch_to_taken_name_is_409(client: TestClient, register):
    register("Taken Name")
    other = register("Other Name")
    response = client.patch(
        "/api/v1/auth/me", headers=other.headers, json={"display_name": "taken name"}
    )
    assert response.status_code == 409
