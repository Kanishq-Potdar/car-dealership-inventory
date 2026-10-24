from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from app.database import DatabaseSettings, get_session
from app.main import app
from app.models import Base, User


@pytest.fixture
def auth_context(monkeypatch):
    """All DDL/data live in a unique schema in an outer rollback-only transaction."""
    secret = uuid4().hex + uuid4().hex
    monkeypatch.setenv("JWT_SECRET", secret)
    engine = create_engine(
        DatabaseSettings().database_url.get_secret_value(),
        connect_args={"connect_timeout": 5},
    )
    schema = "test_auth_" + uuid4().hex
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(CreateSchema(schema))
                connection = connection.execution_options(
                    schema_translate_map={None: schema}
                )
                Base.metadata.create_all(connection)

                def test_session():
                    with Session(
                        connection, join_transaction_mode="create_savepoint"
                    ) as session:
                        yield session

                app.dependency_overrides[get_session] = test_session
                with TestClient(app) as client:
                    yield client, connection, secret
            finally:
                app.dependency_overrides.pop(get_session, None)
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def registration():
    return {
        "full_name": "Alex Customer",
        "email": "alex@example.com",
        "password": "A long password 123!",
    }


def test_register_persists_customer_with_hashed_password(auth_context, registration):
    client, connection, _ = auth_context
    response = client.post("/api/auth/register", json=registration)
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"], "full_name": "Alex Customer",
        "email": "alex@example.com", "role": "customer",
    }
    assert isinstance(body["id"], int)
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        user = session.scalar(select(User))
        assert user.id == body["id"]
        assert user.role == "customer"
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != registration["password"]
        assert PasswordHash.recommended().verify(
            registration["password"], user.password_hash
        )


def test_duplicate_email_is_case_insensitive_and_session_recovers(auth_context, registration):
    client, connection, _ = auth_context
    assert client.post("/api/auth/register", json=registration).status_code == 201
    duplicate = {**registration, "email": " ALEX@EXAMPLE.COM "}
    assert client.post("/api/auth/register", json=duplicate).status_code == 409
    another = {**registration, "email": "other@example.com"}
    assert client.post("/api/auth/register", json=another).status_code == 201
    assert connection.scalar(select(func.count()).select_from(User)) == 2


@pytest.mark.parametrize("changes", [
    {"full_name": " "}, {"full_name": "x" * 101},
    {"email": "invalid-email"}, {"password": "short"},
    {"password": "x" * 129}, {"password": None},
    {"role": "admin"}, {"role": "customer"},
])
def test_registration_rejects_invalid_input_and_role_assignment(
    auth_context, registration, changes
):
    client, connection, _ = auth_context
    response = client.post("/api/auth/register", json={**registration, **changes})
    assert response.status_code == 422
    assert registration["password"] not in response.text
    assert '"input"' not in response.text
    assert connection.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("missing", ["full_name", "email", "password"])
def test_registration_requires_all_details(auth_context, registration, missing):
    client, _, _ = auth_context
    del registration[missing]
    assert client.post("/api/auth/register", json=registration).status_code == 422


def test_login_returns_signed_expiring_token(auth_context, registration):
    client, _, secret = auth_context
    user = client.post("/api/auth/register", json=registration).json()
    response = client.post("/api/auth/login", json={
        "email": " ALEX@EXAMPLE.COM ", "password": registration["password"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], secret, algorithms=["HS256"],
                        options={"require": ["sub", "iat", "exp"]})
    assert claims["sub"] == str(user["id"])
    assert claims["role"] == "customer"
    assert 0 < claims["exp"] - datetime.now(timezone.utc).timestamp() <= 1800
    assert claims["exp"] - claims["iat"] == 1800
    assert "password" not in claims and "password_hash" not in claims
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(body["access_token"], "different-test-secret-" * 3,
                   algorithms=["HS256"])
    expired = jwt.encode({**claims, "exp": 1}, secret, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired, secret, algorithms=["HS256"])


def test_invalid_credentials_have_identical_responses(auth_context, registration):
    client, _, _ = auth_context
    assert client.post("/api/auth/register", json=registration).status_code == 201
    responses = [client.post("/api/auth/login", json={
        "email": email, "password": "wrong password",
    }) for email in [registration["email"], "missing@example.com"]]
    for response in responses:
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("payload", [
    {}, {"email": "bad", "password": "something"},
    {"email": "alex@example.com"},
    {"email": "alex@example.com", "password": ""},
])
def test_login_rejects_invalid_input(auth_context, payload):
    client, _, _ = auth_context
    assert client.post("/api/auth/login", json=payload).status_code == 422


def test_signing_secret_is_required_and_not_defaulted(monkeypatch):
    from pydantic import ValidationError
    from app.auth import AuthSettings

    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        AuthSettings(_env_file=None)
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(ValidationError):
        AuthSettings(_env_file=None)


@pytest.fixture
def protected_context(auth_context, registration):
    from app.auth import get_current_user

    client, _, secret = auth_context
    response = client.post("/api/auth/register", json=registration)
    assert response.status_code == 201
    user = response.json()
    response = client.post("/api/auth/login", json={
        "email": registration["email"], "password": registration["password"],
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    # This route exists only on a separate test app, never the production app.
    protected_app = FastAPI()
    protected_app.dependency_overrides[get_session] = app.dependency_overrides[get_session]

    @protected_app.get("/protected")
    def protected(user: User = Depends(get_current_user)):
        return {"id": user.id, "role": user.role}

    with TestClient(protected_app) as protected_client:
        yield protected_client, token, user, secret


def test_auth_dependency_accepts_token_issued_by_login(protected_context):
    client, token, user, _ = protected_context
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "role": "customer"}


@pytest.mark.parametrize("case", [
    "expired", "malformed", "wrong_signature", "wrong_algorithm", "unsigned",
    "missing_exp", "missing_iat", "missing_sub", "invalid_sub", "oversized_sub",
    "unknown_user", "future_iat", "invalid_exp",
])
def test_auth_dependency_rejects_invalid_tokens(protected_context, case):
    client, token, _, secret = protected_context
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    key, algorithm = secret, "HS256"
    if case == "expired":
        claims["exp"] = int(datetime.now(timezone.utc).timestamp()) - 60
    elif case == "wrong_signature":
        key = uuid4().hex + uuid4().hex
    elif case == "wrong_algorithm":
        algorithm = "HS384"
    elif case == "unsigned":
        key, algorithm = "", "none"
    elif case.startswith("missing_"):
        del claims[case.removeprefix("missing_")]
    elif case == "invalid_sub":
        claims["sub"] = "not-a-user-id"
    elif case == "oversized_sub":
        claims["sub"] = "9" * 100
    elif case == "unknown_user":
        claims["sub"] = "2147483647"
    elif case == "future_iat":
        claims["iat"] = int(datetime.now(timezone.utc).timestamp()) + 3600
    elif case == "invalid_exp":
        claims["exp"] = []
    invalid_token = (
        "not.a.jwt" if case == "malformed"
        else jwt.encode(claims, key, algorithm=algorithm)
    )
    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired authentication token"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", [None, "Bearer", "Basic credentials"])
def test_auth_dependency_requires_bearer_credentials(protected_context, header):
    client, _, _, _ = protected_context
    response = client.get(
        "/protected", headers={} if header is None else {"Authorization": header}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired authentication token"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_dependency_uses_database_role_not_token_role(protected_context):
    client, token, user, secret = protected_context
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    claims["role"] = "admin"
    token = jwt.encode(claims, secret, algorithm="HS256")
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "role": "customer"}
