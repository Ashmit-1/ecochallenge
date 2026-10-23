"""Health, metadata, and configuration parsing."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, Settings


def test_health_reports_ok(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"]


def test_meta_exposes_disclaimers_and_provider(client: TestClient):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["verification_provider"] == "mock"
    assert "can make mistakes" in body["verification_disclaimer"]
    assert "estimates" in body["environmental_disclaimer"]


def test_root_redirects_to_docs(client: TestClient):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/docs"


def test_openapi_document_lists_the_api(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/challenges" in schema["paths"]
    assert "/api/v1/challenges/{slug}/submissions" in schema["paths"]
    assert "/api/v1/leaderboard" in schema["paths"]


def test_comma_separated_cors_origins_are_parsed():
    settings = Settings(
        _env_file=None,
        secret_key="x",
        cors_origins="http://one.test, http://two.test",
    )
    assert settings.cors_origins == ["http://one.test", "http://two.test"]


def test_json_cors_origins_are_parsed():
    settings = Settings(
        _env_file=None,
        secret_key="x",
        cors_origins='["http://one.test", "http://two.test"]',
    )
    assert settings.cors_origins == ["http://one.test", "http://two.test"]


def test_relative_sqlite_url_is_resolved_against_the_backend_directory():
    settings = Settings(
        _env_file=None, secret_key="x", database_url="sqlite:///./data/test.db"
    )
    assert settings.sqlalchemy_url == f"sqlite:///{BACKEND_DIR / 'data' / 'test.db'}"


def test_upload_limit_is_converted_to_bytes():
    settings = Settings(_env_file=None, secret_key="x", max_upload_mb=6)
    assert settings.max_upload_bytes == 6 * 1024 * 1024
