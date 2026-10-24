from datetime import datetime, timezone
from decimal import Decimal

import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User


@pytest.fixture
def vehicle_payload():
    return {
        "make": "Toyota", "model": "Corolla", "year": 2024,
        "category": "Sedan", "price": "25000.50", "quantity": 3,
    }


@pytest.fixture
def vehicle_context(auth_context):
    client, connection, secret = auth_context
    headers = {}
    for role in ["admin", "customer"]:
        email = f"{role}@example.com"
        password = "Vehicle tests password 123!"
        response = client.post("/api/auth/register", json={
            "full_name": role.title(), "email": email, "password": password,
        })
        assert response.status_code == 201
        if role == "admin":
            # Only this isolated fixture promotes a user; there is no public role API.
            with Session(connection, join_transaction_mode="create_savepoint") as session:
                user = session.get(User, response.json()["id"])
                user.role = "admin"
                session.commit()
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        headers[role] = {"Authorization": "Bearer " + response.json()["access_token"]}
    return client, connection, secret, headers


def create_vehicle(context, payload):
    client, _, _, headers = context
    response = client.post("/api/vehicles", json=payload, headers=headers["admin"])
    assert response.status_code == 201
    return response.json()


def test_admin_creates_persisted_vehicles_with_unique_ids(vehicle_context, vehicle_payload):
    first = create_vehicle(vehicle_context, vehicle_payload)
    second = create_vehicle(vehicle_context, vehicle_payload)
    assert first == {"id": first["id"], **vehicle_payload}
    assert isinstance(first["id"], int) and first["id"] > 0
    assert first["id"] != second["id"]
    from app.models import Vehicle

    _, connection, _, _ = vehicle_context
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        stored = session.get(Vehicle, first["id"])
        assert stored.make == "Toyota"
        assert stored.price == Decimal("25000.50")
        assert stored.quantity == 3


def test_database_rejects_duplicate_vehicle_id_and_can_rollback(vehicle_context, vehicle_payload):
    vehicle = create_vehicle(vehicle_context, vehicle_payload)
    from app.models import Vehicle

    _, connection, _, _ = vehicle_context
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        session.add(Vehicle(id=vehicle["id"], **vehicle_payload))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.get(Vehicle, vehicle["id"]).price == Decimal("25000.50")


@pytest.mark.parametrize("role", ["admin", "customer"])
def test_authenticated_users_list_empty_and_populated_inventory(vehicle_context, vehicle_payload, role):
    client, _, _, headers = vehicle_context
    response = client.get("/api/vehicles", headers=headers[role])
    assert response.status_code == 200
    assert response.json() == []
    first = create_vehicle(vehicle_context, vehicle_payload)
    second = create_vehicle(vehicle_context, {**vehicle_payload, "make": "Honda"})
    response = client.get("/api/vehicles", headers=headers[role])
    assert response.status_code == 200
    assert response.json() == [first, second]


def test_admin_replaces_and_deletes_vehicle(vehicle_context, vehicle_payload):
    client, connection, _, headers = vehicle_context
    vehicle = create_vehicle(vehicle_context, vehicle_payload)
    updated = {"make": "Honda", "model": "Civic", "year": 2025,
               "category": "Hatchback", "price": "31000.25", "quantity": 0}
    response = client.put(f"/api/vehicles/{vehicle['id']}", json=updated, headers=headers["admin"])
    assert response.status_code == 200
    assert response.json() == {"id": vehicle["id"], **updated}
    from app.models import Vehicle

    with Session(connection, join_transaction_mode="create_savepoint") as session:
        assert session.get(Vehicle, vehicle["id"]).price == Decimal("31000.25")
    response = client.delete(f"/api/vehicles/{vehicle['id']}", headers=headers["admin"])
    assert response.status_code == 204 and response.content == b""
    assert client.get("/api/vehicles", headers=headers["customer"]).json() == []
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        assert session.get(Vehicle, vehicle["id"]) is None


@pytest.mark.parametrize("method,path", [
    ("POST", "/api/vehicles"), ("GET", "/api/vehicles"),
    ("GET", "/api/vehicles/search"), ("PUT", "/api/vehicles/1"),
    ("DELETE", "/api/vehicles/1"),
])
@pytest.mark.parametrize("authorization", [None, "Bearer not.a.jwt"])
def test_vehicle_endpoints_require_valid_authentication(
    auth_context, vehicle_payload, method, path, authorization
):
    client, _, _ = auth_context
    response = client.request(method, path, json=vehicle_payload,
                              headers={} if authorization is None else {"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_customer_cannot_modify_inventory(vehicle_context, vehicle_payload, method):
    client, _, _, headers = vehicle_context
    vehicle = create_vehicle(vehicle_context, vehicle_payload)
    path = "/api/vehicles" if method == "POST" else f"/api/vehicles/{vehicle['id']}"
    response = client.request(method, path, json=vehicle_payload, headers=headers["customer"])
    assert response.status_code == 403
    assert client.get("/api/vehicles", headers=headers["customer"]).json() == [vehicle]


def test_admin_permission_uses_current_database_role(vehicle_context, vehicle_payload):
    client, connection, secret, headers = vehicle_context
    vehicle = create_vehicle(vehicle_context, vehicle_payload)
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        admin.role = "customer"
        session.commit()
    for method, path in [("POST", "/api/vehicles"), ("PUT", f"/api/vehicles/{vehicle['id']}"),
                         ("DELETE", f"/api/vehicles/{vehicle['id']}")]:
        assert client.request(method, path, json=vehicle_payload, headers=headers["admin"]).status_code == 403
    token = headers["customer"]["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    claims["role"] = "admin"
    forged_role = jwt.encode(claims, secret, algorithm="HS256")
    assert client.post("/api/vehicles", json=vehicle_payload,
                       headers={"Authorization": f"Bearer {forged_role}"}).status_code == 403


@pytest.mark.parametrize("changes", [
    {"make": " "}, {"model": " "}, {"category": " "},
    {"make": "x" * 101}, {"model": "x" * 101}, {"category": "x" * 51},
    {"price": "0"}, {"price": "-1"}, {"price": "1.234"},
    {"price": "NaN"}, {"price": "Infinity"}, {"price": "10000000000.00"},
    {"quantity": -1}, {"quantity": 1.5}, {"quantity": True}, {"quantity": 2147483648},
    {"year": 1885}, {"year": datetime.now(timezone.utc).year + 2}, {"year": True},
    {"id": 1}, {"unexpected": "field"},
])
def test_vehicle_creation_rejects_invalid_fields(vehicle_context, vehicle_payload, changes):
    client, _, _, headers = vehicle_context
    response = client.post("/api/vehicles", json={**vehicle_payload, **changes}, headers=headers["admin"])
    assert response.status_code == 422
    assert client.get("/api/vehicles", headers=headers["admin"]).json() == []


@pytest.mark.parametrize("field", ["make", "model", "category", "price", "quantity"])
def test_vehicle_creation_requires_all_fields(vehicle_context, vehicle_payload, field):
    client, _, _, headers = vehicle_context
    del vehicle_payload[field]
    assert client.post("/api/vehicles", json=vehicle_payload, headers=headers["admin"]).status_code == 422


@pytest.mark.parametrize("payload", [{"price": "10.00"}, {"price": "-1"}, {"id": 99}])
def test_invalid_update_does_not_change_vehicle(vehicle_context, vehicle_payload, payload):
    client, _, _, headers = vehicle_context
    vehicle = create_vehicle(vehicle_context, vehicle_payload)
    request_body = payload if len(payload) == 1 and payload.get("price") == "10.00" else {**vehicle_payload, **payload}
    response = client.put(f"/api/vehicles/{vehicle['id']}", json=request_body, headers=headers["admin"])
    assert response.status_code == 422
    assert client.get("/api/vehicles", headers=headers["customer"]).json() == [vehicle]


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_missing_vehicle_returns_404(vehicle_context, vehicle_payload, method):
    client, _, _, headers = vehicle_context
    response = client.request(method, "/api/vehicles/2147483647", json=vehicle_payload, headers=headers["admin"])
    assert response.status_code == 404
    assert response.json() == {"detail": "Vehicle not found"}


@pytest.mark.parametrize("vehicle_id", ["0", "-1", "2147483648", "invalid"])
@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_invalid_vehicle_id_returns_422(vehicle_context, vehicle_payload, method, vehicle_id):
    client, _, _, headers = vehicle_context
    response = client.request(method, f"/api/vehicles/{vehicle_id}", json=vehicle_payload, headers=headers["admin"])
    assert response.status_code == 422


def test_search_filters_are_combined_case_insensitive_and_price_inclusive(vehicle_context, vehicle_payload):
    client, _, _, headers = vehicle_context
    first = create_vehicle(vehicle_context, vehicle_payload)
    second = create_vehicle(vehicle_context, {**vehicle_payload, "model": "RAV4", "category": "SUV", "price": "40000.00"})
    third = create_vehicle(vehicle_context, {**vehicle_payload, "make": "Honda", "model": "Civic", "price": "30000.00"})
    cases = [
        ({}, [first, second, third]),
        ({"make": " TOYOTA "}, [first, second]),
        ({"model": "corolla"}, [first]),
        ({"category": "sedan"}, [first, third]),
        ({"min_price": "30000"}, [second, third]),
        ({"max_price": "30000"}, [first, third]),
        ({"min_price": "25000.50", "max_price": "25000.50"}, [first]),
        ({"make": "toyota", "model": "rav4", "category": "suv", "min_price": "30000", "max_price": "40000"}, [second]),
        ({"make": "Missing"}, []), ({"make": "%"}, []),
        ({"make": "' OR 1=1 --"}, []),
    ]
    for params, expected in cases:
        response = client.get("/api/vehicles/search", params=params, headers=headers["customer"])
        assert response.status_code == 200
        assert response.json() == expected, params


@pytest.mark.parametrize("params", [
    {"min_price": "20", "max_price": "10"}, {"min_price": "-1"},
    {"max_price": "-1"}, {"min_price": "NaN"}, {"max_price": "Infinity"},
    {"min_price": "not-a-price"}, {"make": " "}, {"model": " "}, {"category": " "},
])
def test_search_rejects_invalid_filters(vehicle_context, params):
    client, _, _, headers = vehicle_context
    response = client.get("/api/vehicles/search", params=params, headers=headers["customer"])
    assert response.status_code == 422
