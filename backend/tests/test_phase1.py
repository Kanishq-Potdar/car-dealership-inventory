from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import jwt
import pytest
from pwdlib import PasswordHash
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.models import Base, User, Vehicle
from app.database import DatabaseSettings


@pytest.fixture
def phase_context(auth_context):
    client, connection, secret = auth_context
    headers = {}
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        for role in ("admin", "customer"):
            user = User(full_name=role, email=f"{role}@example.com", role=role, password_hash="unused")
            session.add(user)
            session.flush()
            now = datetime.now(timezone.utc)
            token = jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=5)}, secret, algorithm="HS256")
            headers[role] = {"Authorization": f"Bearer {token}"}
        session.commit()
    return client, connection, headers


def add_vehicle(context, **changes):
    client, _, headers = context
    payload = dict(make="Tata", model="Nexon", category="SUV", price="1200000.00", quantity=3, year=2024)
    response = client.post("/api/vehicles", json={**payload, **changes}, headers=headers["admin"])
    assert response.status_code == 201
    return response.json()


def test_condition_defaults_and_preserves_omitted_update(phase_context):
    client, _, headers = phase_context
    assert add_vehicle(phase_context)["condition"] == "used"
    vehicle = add_vehicle(phase_context, condition="new")
    assert vehicle["condition"] == "new"
    payload = {key: value for key, value in vehicle.items() if key not in ("id", "condition")}
    response = client.put(f"/api/vehicles/{vehicle['id']}", json=payload, headers=headers["admin"])
    assert response.status_code == 200
    assert response.json()["condition"] == "new"
    response = client.put(f"/api/vehicles/{vehicle['id']}", json={**payload, "condition": "used"}, headers=headers["admin"])
    assert response.json()["condition"] == "used"


@pytest.mark.parametrize("condition", [None, "damaged", "NEW", ""])
def test_invalid_condition(phase_context, condition):
    client, _, headers = phase_context
    payload = dict(make="Tata", model="Nexon", category="SUV", price="100.00", quantity=1, condition=condition)
    assert client.post("/api/vehicles", json=payload, headers=headers["admin"]).status_code == 422


def test_migration_backfills_and_is_repeatable(auth_context):
    from app.migrate import migrate

    _, connection, _ = auth_context
    schema = "test_legacy_" + uuid4().hex
    connection.execute(CreateSchema(schema))
    connection = connection.execution_options(schema_translate_map={None: schema})
    table = f'"{schema}".vehicles'
    connection.execute(text(f'''CREATE TABLE {table} (
        id SERIAL PRIMARY KEY, make varchar(100) NOT NULL, model varchar(100) NOT NULL,
        category varchar(50) NOT NULL, year integer, price numeric(12,2) NOT NULL, quantity integer NOT NULL
    )'''))
    connection.execute(text(f"INSERT INTO {table} (make, model, category, year, price, quantity) VALUES ('Honda', 'City', 'Sedan', 2020, 700000, 4)"))
    migrate(connection)
    assert connection.execute(text(f"SELECT id, make, price, quantity, condition FROM {table}")).one() == (1, "Honda", 700000, 4, "used")
    connection.execute(text(f"UPDATE {table} SET condition='new' WHERE id=1"))
    migrate(connection)
    assert connection.scalar(text(f"SELECT condition FROM {table}")) == "new"
    columns = {column["name"]: column for column in inspect(connection).get_columns("vehicles", schema=schema)}
    assert columns["condition"]["nullable"] is False
    assert "sample_key" in columns
    indexes = {item["name"] for item in inspect(connection).get_indexes("vehicles", schema=schema)}
    assert {"ix_vehicles_quantity", "ix_vehicles_price", "ix_vehicles_category"} <= indexes
    with connection.begin_nested() as savepoint:
        with pytest.raises(IntegrityError):
            connection.execute(text(f"UPDATE {table} SET condition='bad'"))
        savepoint.rollback()


def test_repeatable_seed_preserves_user_and_edited_sample_data(auth_context):
    from app.seed_catalogue import load_catalogue, seed_catalogue

    _, connection, _ = auth_context
    data = load_catalogue()
    assert 50 <= len(data) <= 100
    assert {row["condition"] for row in data} == {"new", "used"}
    assert len({row["make"] for row in data}) >= 15
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        original = Vehicle(make="Owner", model="Personal", category="Sedan", price="100.00", quantity=7)
        session.add(original)
        session.commit()
        assert seed_catalogue(session) == len(data)
        sample = session.scalar(select(Vehicle).where(Vehicle.sample_key.is_not(None)))
        sample.quantity = 0
        sample.price = 123
        session.commit()
        assert seed_catalogue(session) == 0
        assert session.scalar(select(func.count()).select_from(Vehicle)) == len(data) + 1
        session.refresh(sample)
        session.refresh(original)
        assert sample.quantity == 0 and sample.price == 123
        assert original.quantity == 7 and original.price == 100


def test_partial_search_and_rank_with_filters(phase_context):
    client, _, headers = phase_context
    suffix = add_vehicle(phase_context, model="Grand Nexon")
    prefix = add_vehicle(phase_context, model="Nexon EV", price="1500000.00")
    exact = add_vehicle(phase_context)
    add_vehicle(phase_context, make="Honda", model="City", category="Sedan")
    response = client.get("/api/vehicles/search", params={"make": " AT ", "model": "nexon", "category": "suv", "min_price": "1200000", "max_price": "1500000"}, headers=headers["customer"])
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [exact["id"], prefix["id"], suffix["id"]]
    response = client.get("/api/vehicles/search", params={"q": "tata nexon", "max_price": "1200000"}, headers=headers["customer"])
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [exact["id"]]
    for literal in ("%", "_", "' OR 1=1 --"):
        assert client.get("/api/vehicles/search", params={"q": literal}, headers=headers["customer"]).json() == []


def test_search_without_trigram(phase_context, monkeypatch):
    from app import vehicle_search

    monkeypatch.setattr(vehicle_search, "trigram_schema", lambda session: None)
    client, _, headers = phase_context
    vehicle = add_vehicle(phase_context)
    response = client.get("/api/vehicles/search", params={"q": "nex"}, headers=headers["customer"])
    assert [row["id"] for row in response.json()] == [vehicle["id"]]
    assert client.get("/api/vehicles/search", params={"q": "nexonnn"}, headers=headers["customer"]).json() == []


def test_optional_trigram_typo_search(phase_context):
    from app.migrate import migrate

    client, connection, headers = phase_context
    # PostgreSQL extension creation is transactional: auth_context rolls it back.
    result = migrate(connection, enable_trigram=True)
    assert result["trigram_enabled"], result
    exact = add_vehicle(phase_context, make="Toyota", model="Corolla")
    response = client.get("/api/vehicles/search", params={"make": "toyotaa", "model": "corola", "category": "SUV"}, headers=headers["customer"])
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [exact["id"]]


def test_signed_stock_adjustment(phase_context):
    client, _, headers = phase_context
    vehicle = add_vehicle(phase_context)
    url = f"/api/vehicles/{vehicle['id']}/adjust-stock"
    for delta, expected in ((2, 5), (-5, 0), (1, 1)):
        response = client.post(url, json={"delta": delta}, headers=headers["admin"])
        assert response.status_code == 200
        assert response.json()["quantity"] == expected
    for delta in (-2, 2147483647):
        assert client.post(url, json={"delta": delta}, headers=headers["admin"]).status_code == 409
    assert client.get("/api/vehicles", headers=headers["admin"]).json()[0]["quantity"] == 1


@pytest.mark.parametrize("payload", [{}, {"delta": 0}, {"delta": True}, {"delta": 1.5}, {"delta": "2"}, {"delta": -2147483648}, {"delta": 2147483648}, {"delta": 1, "extra": 1}])
def test_invalid_adjustments(phase_context, payload):
    client, _, headers = phase_context
    vehicle = add_vehicle(phase_context)
    assert client.post(f"/api/vehicles/{vehicle['id']}/adjust-stock", json=payload, headers=headers["admin"]).status_code == 422


@pytest.mark.parametrize("role,expected", [(None, 401), ("customer", 403)])
def test_adjustment_and_alerts_admin_only(phase_context, role, expected):
    client, _, headers = phase_context
    auth = {} if role is None else headers[role]
    assert client.post("/api/vehicles/1/adjust-stock", json={"delta": 1}, headers=auth).status_code == expected
    assert client.get("/api/vehicles/alerts", headers=auth).status_code == expected


def test_alert_threshold_and_out_of_stock(phase_context, monkeypatch):
    client, _, headers = phase_context
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "2")
    vehicles = [add_vehicle(phase_context, quantity=n) for n in (0, 1, 2, 3)]
    response = client.get("/api/vehicles/alerts", headers=headers["admin"])
    assert response.status_code == 200
    assert response.json()["threshold"] == 2
    assert [row["id"] for row in response.json()["vehicles"]] == [v["id"] for v in vehicles[:3]]
    response = client.get("/api/vehicles/alerts?out_of_stock=true", headers=headers["admin"])
    assert [row["id"] for row in response.json()["vehicles"]] == [vehicles[0]["id"]]
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "0")
    assert len(client.get("/api/vehicles/alerts", headers=headers["admin"]).json()["vehicles"]) == 1


def test_missing_adjustment_and_demoted_admin(phase_context):
    client, connection, headers = phase_context
    response = client.post("/api/vehicles/2147483647/adjust-stock", json={"delta": 1}, headers=headers["admin"])
    assert response.status_code == 404 and response.json() == {"detail": "Vehicle not found"}
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        session.scalar(select(User).where(User.role == "admin")).role = "customer"
        session.commit()
    assert client.get("/api/vehicles/alerts", headers=headers["admin"]).status_code == 403
    assert client.post("/api/vehicles/1/adjust-stock", json={"delta": 1}, headers=headers["admin"]).status_code == 403


def test_admin_bootstrap_hashes_password_and_refuses_second_admin(auth_context):
    from app.bootstrap_admin import create_first_admin

    client, connection, _ = auth_context
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        user = create_first_admin(session, " First Admin ", " ADMIN@example.com ", "Bootstrap password 123!")
        assert user.role == "admin" and user.email == "admin@example.com" and user.full_name == "First Admin"
        assert PasswordHash.recommended().verify("Bootstrap password 123!", user.password_hash)
        with pytest.raises(ValueError, match="admin already exists"):
            create_first_admin(session, "Second", "second@example.com", "Bootstrap password 123!")
        assert session.scalar(select(func.count()).select_from(User)) == 1
    assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Bootstrap password 123!"}).status_code == 200


def test_bootstrap_does_not_promote_existing_customer(auth_context):
    from app.bootstrap_admin import create_first_admin

    client, connection, _ = auth_context
    payload = {"full_name": "Customer", "email": "existing@example.com", "password": "Customer password 123!"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        with pytest.raises(ValueError, match="email already exists"):
            create_first_admin(session, "Admin", "EXISTING@example.com", "Bootstrap password 123!")
        user = session.scalar(select(User))
        assert user.role == "customer"
        assert PasswordHash.recommended().verify(payload["password"], user.password_hash)


def test_bootstrap_validation_does_not_insert(auth_context):
    from app.bootstrap_admin import create_first_admin

    _, connection, _ = auth_context
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        for name, email, password in [(" ", "admin@example.com", "Long password 123!"), ("Admin", "bad", "Long password 123!"), ("Admin", "admin@example.com", "short")]:
            with pytest.raises(ValueError):
                create_first_admin(session, name, email, password)
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_cli_password_confirmation_uses_hidden_prompts(monkeypatch, capsys):
    from app import bootstrap_admin

    answers = iter(["Admin", "admin@example.com"])
    passwords = iter(["Do not print this 123!", "Different secret 123!"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    prompts = []
    def hidden(prompt):
        prompts.append(prompt)
        return next(passwords)
    monkeypatch.setattr(bootstrap_admin, "getpass", hidden)
    assert bootstrap_admin.main() == 1
    assert len(prompts) == 2
    assert "Do not print" not in capsys.readouterr().out


def test_migration_survives_extension_install_failure(auth_context, monkeypatch):
    from app.migrate import migrate

    _, connection, _ = auth_context
    execute = connection.execute
    def denied(statement, *args, **kwargs):
        if str(statement).startswith("CREATE EXTENSION"):
            # A real PostgreSQL error puts the savepoint in the failed state.
            return execute(text("SELECT 1 / 0"))
        return execute(statement, *args, **kwargs)
    monkeypatch.setattr(connection, "execute", denied)
    result = migrate(connection, enable_trigram=True)
    assert result["warnings"]
    assert connection.scalar(text("SELECT 1")) == 1


def test_alert_settings_validate_threshold(monkeypatch):
    from app.vehicles import InventorySettings

    for value in ("-1", "2147483648", "abc"):
        monkeypatch.setenv("LOW_STOCK_THRESHOLD", value)
        with pytest.raises(ValueError):
            InventorySettings()


@pytest.fixture
def committed_database():
    schema = "test_phase1_" + uuid4().hex
    engine = create_engine(DatabaseSettings().database_url.get_secret_value(),
                           connect_args={"connect_timeout": 5},
                           execution_options={"schema_translate_map": {None: schema}})
    created = False
    try:
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        Base.metadata.create_all(engine)
        yield engine
    finally:
        if created:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


def test_concurrent_seed_is_idempotent(committed_database):
    from app.seed_catalogue import load_catalogue, seed_catalogue

    barrier = Barrier(2)
    def seed(_):
        with Session(committed_database) as session:
            barrier.wait(timeout=10)
            return seed_catalogue(session)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(seed, range(2)))
    count = len(load_catalogue())
    assert sorted(results) == [0, count]
    with Session(committed_database) as session:
        assert session.scalar(select(func.count()).select_from(Vehicle)) == count


def test_concurrent_bootstrap_creates_only_one_admin(committed_database):
    from app.bootstrap_admin import create_first_admin

    barrier = Barrier(2)
    def bootstrap(number):
        with Session(committed_database) as session:
            barrier.wait(timeout=10)
            try:
                create_first_admin(session, "Admin", f"admin{number}@example.com", "Bootstrap password 123!")
                return "created"
            except ValueError as error:
                assert "admin already exists" in str(error)
                return "refused"
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(bootstrap, range(2))) == ["created", "refused"]
    with Session(committed_database) as session:
        assert session.scalar(select(func.count()).select_from(User).where(User.role == "admin")) == 1


def test_concurrent_adjustment_and_purchase_never_go_negative(committed_database):
    from app.vehicles import change_stock
    from fastapi import HTTPException

    with Session(committed_database) as session:
        vehicle = Vehicle(make="Tata", model="Nexon", category="SUV", price="1200000.00", quantity=2)
        session.add(vehicle)
        session.commit()
        vehicle_id = vehicle.id
    barrier = Barrier(2)
    def adjust(delta):
        with Session(committed_database) as session:
            barrier.wait(timeout=10)
            try:
                change_stock(session, vehicle_id, delta)
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(adjust, [-2, -1])) == [200, 409]
    with Session(committed_database) as session:
        assert session.get(Vehicle, vehicle_id).quantity in (0, 1)
