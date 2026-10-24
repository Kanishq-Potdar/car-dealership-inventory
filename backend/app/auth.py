from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import DatabaseSettings, get_session
from app.models import User


class AuthSettings(BaseSettings):
    jwt_secret: SecretStr = Field(min_length=32)
    model_config = DatabaseSettings.model_config


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(LoginRequest):
    full_name: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


router = APIRouter(prefix="/api/auth", tags=["auth"])
password_hasher = PasswordHash.recommended()
# Also verify a hash for unknown emails, avoiding a fast account-existence path.
dummy_password_hash = password_hasher.hash("unused dummy password")
DatabaseSession = Annotated[Session, Depends(get_session)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    session: DatabaseSession,
) -> User:
    """Use Depends(get_current_user) to require a valid token and existing user."""
    unauthorized = HTTPException(
        401,
        "Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    settings = AuthSettings()
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
        user_id = int(claims["sub"])
        # User.id is a PostgreSQL INTEGER; reject out-of-range IDs before querying.
        if not 1 <= user_id <= 2**31 - 1:
            raise ValueError("Invalid user ID")
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise unauthorized from None
    user = session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


@router.post("/register", status_code=201, response_model=UserResponse)
def register(payload: RegisterRequest, session: DatabaseSession):
    user = User(
        full_name=payload.full_name,
        email=str(payload.email),
        password_hash=password_hasher.hash(payload.password.get_secret_value()),
        role="customer",
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # The unique constraint handles simultaneous registrations too.
        if (
            getattr(error.orig, "sqlstate", None) == "23505"
            and getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            == "uq_users_email"
        ):
            raise HTTPException(409, "Email is already registered") from None
        raise
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: DatabaseSession):
    settings = AuthSettings()
    user = session.scalar(select(User).where(User.email == str(payload.email)))
    stored_hash = user.password_hash if user else dummy_password_hash
    valid_password = password_hasher.verify(
        payload.password.get_secret_value(), stored_hash
    )
    if user is None or not valid_password:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return TokenResponse(access_token=token)
