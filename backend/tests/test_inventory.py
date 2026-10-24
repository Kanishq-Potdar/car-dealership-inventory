from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.database import DatabaseSettings, get_session
from app.main import app
from app.models import Base, User, Vehicle


@pytest.fixture
def inventory(monkeypatch):
    """Committed test-only schema permits real, independent concurrent transactions."""
    schema = "test_inventory_" + uuid4().hex
    secret = uuid4().hex + uuid4().hex
    monkeypatch.setenv("JWT_SECRET", secret)
    engine = create_engine(
        DatabaseSettings().database_url.get_secret_value(),
        connect_args={"connect_timeout": 5},
        execution_options={"schema_translate_map": {None: schema}},
    )
    state = {"barrier": None, "pids": []}
    created = False
    try:
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        Base.metadata.create_all(engine)
        headers = {}
        with Session(engine) as session:
            for role in ("customer", "admin"):
                user = User(full_name=role, email=f"{role}@example.com",
                            password_hash="unused: these tests authenticate with JWT", role=role)
                session.add(user)
                session.flush()
                now = datetime.now(timezone.utc)
                token = jwt.encode({"sub": str(user.id), "iat": now,
                                    "exp": now + timedelta(minutes=5)}, secret, algorithm="HS256")
                headers[role] = {"Authorization": "Bearer " + token}
            vehicle = Vehicle(make="Toyota", model="Corolla", category="Sedan",
                              year=2024, price="25000.00", quantity=1)
            session.add(vehicle)
            session.commit()
            vehicle_id = vehicle.id

        def test_session():
            with Session(engine) as session:
                if state["barrier"] is not None:
                    state["pids"].append(session.scalar(text("SELECT pg_backend_pid()")))
                    state["barrier"].wait(timeout=15)
                yield session

        app.dependency_overrides[get_session] = test_session
        with TestClient(app) as client:
            yield client, engine, vehicle_id, headers, state
    finally:
        app.dependency_overrides.pop(get_session, None)
        if created:
            # Only the UUID-named schema created by this fixture is ever dropped.
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


@pytest.mark.parametrize("year", ["omitted", None])
def test_year_is_optional_on_create_and_replace(inventory, year):
    client, engine, _, headers, _ = inventory
    payload = dict(make="Honda", model="Civic", category="Sedan", price="10.00", quantity=2)
    if year is None:
        payload["year"] = None
    response = client.post("/api/vehicles", json=payload, headers=headers["admin"])
    assert response.status_code == 201
    vehicle_id = response.json()["id"]
    assert response.json()["year"] is None
    response = client.put(f"/api/vehicles/{vehicle_id}", json=payload, headers=headers["admin"])
    assert response.status_code == 200
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).year is None


@pytest.mark.parametrize("role", ["customer", "admin"])
def test_purchase_one_then_reject_empty_stock(inventory, role):
    client, engine, vehicle_id, headers, _ = inventory
    url = f"/api/vehicles/{vehicle_id}/purchase"
    response = client.post(url, headers=headers[role])
    assert response.status_code == 200
    assert response.json()["quantity"] == 0
    response = client.post(url, headers=headers[role])
    assert response.status_code == 409
    assert response.json() == {"detail": "Vehicle out of stock"}
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).quantity == 0


def test_admin_restocks_by_requested_amount(inventory):
    client, engine, vehicle_id, headers, _ = inventory
    response = client.post(f"/api/vehicles/{vehicle_id}/restock", json={"quantity": 3}, headers=headers["admin"])
    assert response.status_code == 200
    assert response.json()["quantity"] == 4
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).quantity == 4


def test_customer_cannot_restock(inventory):
    client, engine, vehicle_id, headers, _ = inventory
    response = client.post(f"/api/vehicles/{vehicle_id}/restock", json={"quantity": 3}, headers=headers["customer"])
    assert response.status_code == 403
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).quantity == 1


@pytest.mark.parametrize("action", ["purchase", "restock"])
@pytest.mark.parametrize("authorization", [None, "Bearer invalid"])
def test_inventory_requires_authentication(inventory, action, authorization):
    client, _, vehicle_id, _, _ = inventory
    response = client.post(f"/api/vehicles/{vehicle_id}/{action}", json={"quantity": 1},
                           headers={} if authorization is None else {"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("action", ["purchase", "restock"])
def test_missing_vehicle(inventory, action):
    client, _, _, headers, _ = inventory
    response = client.post(f"/api/vehicles/2147483647/{action}", json={"quantity": 1}, headers=headers["admin"])
    assert response.status_code == 404
    assert response.json() == {"detail": "Vehicle not found"}


@pytest.mark.parametrize("payload", [{}, {"quantity": 0}, {"quantity": -1},
    {"quantity": True}, {"quantity": 1.5}, {"quantity": "2"},
    {"quantity": 2147483648}, {"quantity": 1, "extra": 2}])
def test_restock_rejects_invalid_amount(inventory, payload):
    client, engine, vehicle_id, headers, _ = inventory
    response = client.post(f"/api/vehicles/{vehicle_id}/restock", json=payload, headers=headers["admin"])
    assert response.status_code == 422
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).quantity == 1


def test_restock_rejects_integer_overflow(inventory):
    client, engine, vehicle_id, headers, _ = inventory
    response = client.post(f"/api/vehicles/{vehicle_id}/restock", json={"quantity": 2147483647}, headers=headers["admin"])
    assert response.status_code == 409
    with Session(engine) as session:
        assert session.get(Vehicle, vehicle_id).quantity == 1


@pytest.mark.parametrize("action,expected_statuses,expected_stock", [
    ("purchase", [200, 409], 0), ("restock", [200, 200], 3),
])
def test_concurrent_inventory_requests(inventory, action, expected_statuses, expected_stock):
    _, engine, vehicle_id, headers, state = inventory
    state["barrier"] = Barrier(2)

    def request():
        with TestClient(app) as client:
            return client.post(f"/api/vehicles/{vehicle_id}/{action}",
                               json={"quantity": 1}, headers=headers["admin"]).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: request(), range(2)))
    state["barrier"] = None
    assert sorted(statuses) == expected_statuses
    assert len(set(state["pids"])) == 2
    with Session(engine) as session:
        assert session.scalar(select(Vehicle.quantity).where(Vehicle.id == vehicle_id)) == expected_stock
