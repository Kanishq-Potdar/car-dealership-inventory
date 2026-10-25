"""Run browser tests against real FastAPI in a disposable PostgreSQL schema."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema
from pwdlib import PasswordHash
from app.database import DatabaseSettings
from app.models import Base, User, Vehicle

schema = "test_frontend_" + uuid4().hex
engine = create_engine(DatabaseSettings().database_url.get_secret_value(),
                       connect_args={"connect_timeout": 5},
                       execution_options={"schema_translate_map": {None: schema}})
created = False
try:
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    created = True
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(full_name="Test Admin", email="admin@example.com", role="admin",
                         password_hash=PasswordHash.recommended().hash("Browser tests password 123!")))
        session.add(User(full_name="Test Customer", email="shopper@example.com", role="customer",
                         password_hash=PasswordHash.recommended().hash("Browser tests password 123!")))
        session.add_all([
            Vehicle(make="Toyota", model="Corolla", category="Sedan", price="25000.50", quantity=1, year=2024),
            Vehicle(make="Honda", model="Civic", category="Sedan", price="30000.00", quantity=0, year=2025),
            Vehicle(make="Toyota", model="RAV4", category="SUV", price="40000.00", quantity=4, year=2025, condition="new"),
        ])
        session.commit()
    env = dict(os.environ, E2E_SCHEMA=schema, JWT_SECRET=uuid4().hex + uuid4().hex,
               E2E_PYTHON=sys.executable, LOW_STOCK_THRESHOLD="3", PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test", *sys.argv[1:]], env=env)
    sys.exit(result.returncode)
finally:
    if created:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
    engine.dispose()
