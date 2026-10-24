from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


class DatabaseSettings(BaseSettings):
    database_url: SecretStr

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )


@lru_cache
def get_engine():
    """Reuse the connection pool; open connections only when needed."""
    return create_engine(
        DatabaseSettings().database_url.get_secret_value(),
        connect_args={"connect_timeout": 5},
        pool_pre_ping=True,
    )


def get_session():
    """Give each request its own session and roll back unfinished work on close."""
    with Session(get_engine()) as session:
        yield session


def check_database_connection() -> bool:
    """Return True if PostgreSQL responds; raise on configuration/connection errors."""
    settings = DatabaseSettings()
    engine = create_engine(
        settings.database_url.get_secret_value(),
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
