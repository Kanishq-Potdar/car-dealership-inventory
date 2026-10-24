from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text


class DatabaseSettings(BaseSettings):
    database_url: SecretStr

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )


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
