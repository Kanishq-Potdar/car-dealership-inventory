from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.orm import Session

from app.models import User, Vehicle


@pytest.fixture
def search_context(auth_context):
    client, connection, secret = auth_context
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        user = User(full_name="Search customer", email="search@example.com",
                    password_hash="unused", role="customer")
        session.add(user)
        rows = [
            ("Toyota", "Corolla", "Sedan", 20000, 2020, "used"),
            ("Toyota", "Corolla Cross", "SUV", 30000, 2024, "new"),
            ("Honda", "Civic", "Sedan", 20000, 2022, "new"),
            ("Honda", "CR-V", "SUV", 40000, None, "used"),
        ]
        vehicles = [Vehicle(make=make, model=model, category=category, price=price,
                            year=year, condition=condition, quantity=2)
                    for make, model, category, price, year, condition in rows]
        session.add_all(vehicles)
        session.flush()
        ids = [vehicle.id for vehicle in vehicles]
        now = datetime.now(timezone.utc)
        token = jwt.encode({"sub": str(user.id), "iat": now,
                            "exp": now + timedelta(minutes=5)}, secret, algorithm="HS256")
        session.commit()
    return client, {"Authorization": f"Bearer {token}"}, ids


@pytest.mark.parametrize("params,indices", [
    ({"condition": "new"}, [1, 2]),
    ({"condition": "used"}, [0, 3]),
    ({"makes": [" TOYOTA ", "honda"]}, [0, 1, 2, 3]),
    ({"models": ["corolla", " CIVIC "]}, [0, 2]),
    ({"categories": ["sedan", "SUV"]}, [0, 1, 2, 3]),
    ({"makes": ["Toyota", "Honda"], "models": ["Corolla", "Civic"],
      "categories": ["Sedan"], "condition": "new", "min_price": 20000,
      "max_price": 20000, "q": "civ", "sort": "price_desc"}, [2]),
    ({"make": "toy", "makes": ["Honda"]}, []),
    ({"model": "cor", "models": ["Corolla Cross"], "category": "SUV"}, [1]),
    ({"makes": ["Toy"]}, []),
    ({"models": ["%", "_", "' OR 1=1 --"]}, []),
    ({"sort": "price_asc"}, [0, 2, 1, 3]),
    ({"sort": "price_desc"}, [3, 1, 0, 2]),
    ({"sort": "year_asc"}, [0, 2, 1, 3]),
    ({"sort": "year_desc"}, [1, 2, 0, 3]),
    ({"q": "corolla", "sort": "relevance"}, [0, 1]),
    ({"q": "corolla", "sort": "price_desc"}, [1, 0]),
])
def test_search_filters_and_sort(search_context, params, indices):
    client, headers, ids = search_context
    response = client.get("/api/vehicles/search", params=params, headers=headers)
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [ids[index] for index in indices]


@pytest.mark.parametrize("params", [
    {"condition": "other"}, {"condition": ""}, {"sort": "unknown"},
    {"makes": [" "]}, {"models": [" "]}, {"categories": [" "]},
    {"makes": ["x" * 101]}, {"models": ["x" * 101]},
    {"categories": ["x" * 51]}, {"makes": ["Toyota"] * 51},
    {"condition": "new", "min_price": 30000, "max_price": 20000},
])
def test_invalid_search_filters(search_context, params):
    client, headers, _ = search_context
    assert client.get("/api/vehicles/search", params=params, headers=headers).status_code == 422


def test_search_still_requires_authentication(search_context):
    client, _, _ = search_context
    response = client.get("/api/vehicles/search", params={"condition": "new", "sort": "price_asc"})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
