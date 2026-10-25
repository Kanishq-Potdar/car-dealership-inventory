import json

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.cors import CorsSettings, configure_cors
from app.main import app


ORIGIN = "https://motorhaus-test.vercel.app"


def cors_client(monkeypatch, origins):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", json.dumps(origins))
    test_app = FastAPI()
    configure_cors(test_app)
    # Use real routes/dependencies without changing the shared production app.
    test_app.include_router(app.router)
    return TestClient(test_app)


def test_main_installs_cors():
    assert any(middleware.cls is CORSMiddleware for middleware in app.user_middleware)


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_allowed_preflight(monkeypatch, method):
    with cors_client(monkeypatch, [ORIGIN]) as client:
        response = client.options("/api/vehicles", headers={
            "Origin": ORIGIN, "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        })
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Access-Control-Allow-Credentials" not in response.headers
    assert "Origin" in response.headers["Vary"]


@pytest.mark.parametrize("origin", ["https://other.vercel.app", "https://motorhaus-test.vercel.app.evil.example", "null"])
def test_other_origins_rejected(monkeypatch, origin):
    with cors_client(monkeypatch, [ORIGIN]) as client:
        response = client.options("/api/vehicles", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
        })
    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


def test_default_denies_cross_origin_and_local_health_works(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert CorsSettings(_env_file=None).cors_allowed_origins == []
    with cors_client(monkeypatch, []) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/health", headers={"Origin": ORIGIN})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_does_not_bypass_authentication(monkeypatch):
    with cors_client(monkeypatch, [ORIGIN]) as client:
        response = client.get("/api/vehicles", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN


@pytest.mark.parametrize("method,headers", [("PATCH", "authorization"), ("POST", "x-unapproved")])
def test_unapproved_method_or_headers(monkeypatch, method, headers):
    with cors_client(monkeypatch, [ORIGIN]) as client:
        response = client.options("/api/vehicles", headers={
            "Origin": ORIGIN, "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        })
    assert response.status_code == 400


@pytest.mark.parametrize("origin", ["*", "https://*.vercel.app", "null", "ftp://example.com",
                                    "https://example.com/path", "https://user:pass@example.com",
                                    "https://example.com?x=1", "https://example.com#hash",
                                    "https://example.com:invalid"])
def test_invalid_configuration_rejected(origin):
    with pytest.raises(ValidationError):
        CorsSettings(_env_file=None, cors_allowed_origins=[origin])


def test_multiple_explicit_origins_and_trailing_slash(monkeypatch):
    with cors_client(monkeypatch, [ORIGIN + "/", "https://shop.example.com"]) as client:
        for origin in [ORIGIN, "https://shop.example.com"]:
            response = client.get("/health", headers={"Origin": origin})
            assert response.headers["Access-Control-Allow-Origin"] == origin


def test_cors_headers_present_on_unexpected_server_exception(monkeypatch):
    """Regression: HTTP 500 from an unhandled exception must carry CORS headers.

    The ASGI middleware stack places ServerErrorMiddleware *outside*
    CORSMiddleware.  Without _UnhandledExceptionMiddleware sitting inside
    CORSMiddleware, the 500 response bypasses CORS header injection and the
    browser blocks the response entirely.
    """
    test_app = FastAPI()
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", json.dumps([ORIGIN]))
    configure_cors(test_app)

    @test_app.get("/explode")
    def explode():
        raise RuntimeError("Simulated unexpected server error")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/explode", headers={"Origin": ORIGIN})

    assert response.status_code == 500
    assert response.headers.get("Access-Control-Allow-Origin") == ORIGIN
    # Response body must not expose internal exception details.
    body = response.json()
    assert "detail" in body
    assert "RuntimeError" not in body["detail"]
    assert "Simulated" not in body["detail"]


def test_cors_headers_absent_on_unexpected_exception_disallowed_origin(monkeypatch):
    """Disallowed origins must not receive CORS headers even on HTTP 500."""
    test_app = FastAPI()
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", json.dumps([ORIGIN]))
    configure_cors(test_app)

    @test_app.get("/explode")
    def explode():
        raise RuntimeError("Simulated unexpected server error")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/explode", headers={"Origin": "https://evil.example.com"})

    assert response.status_code == 500
    assert "Access-Control-Allow-Origin" not in response.headers
