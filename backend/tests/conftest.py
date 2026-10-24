from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from app.database import DatabaseSettings, get_session
from app.main import app
from app.models import Base


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
