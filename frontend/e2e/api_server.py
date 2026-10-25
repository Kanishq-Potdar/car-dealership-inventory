"""Test-only server; never writes to the development tables."""
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import DatabaseSettings, get_session
from app.main import app

schema = os.environ["E2E_SCHEMA"]
assert re.fullmatch(r"test_frontend_[0-9a-f]{32}", schema)
engine = create_engine(DatabaseSettings().database_url.get_secret_value(),
                       connect_args={"connect_timeout": 5},
                       execution_options={"schema_translate_map": {None: schema}})

def test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = test_session
try:
    uvicorn.run(app, host="127.0.0.1", port=8011, log_level="warning", access_log=False)
finally:
    engine.dispose()
