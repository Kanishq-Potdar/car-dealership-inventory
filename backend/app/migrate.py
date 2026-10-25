"""Explicit, transactional Phase 1 upgrade. Does not reset tables or seed data."""
import argparse

from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from app.database import get_engine


def migrate(connection, enable_trigram=False):
    schema = connection.get_execution_options().get("schema_translate_map", {}).get(None)
    schema = schema or inspect(connection).default_schema_name
    quote = connection.dialect.identifier_preparer.quote
    table = f"{quote(schema)}.vehicles"
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text("SET LOCAL statement_timeout = '60s'"))
    connection.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"motorhaus.phase1:{schema}"})
    if not inspect(connection).has_table("vehicles", schema=schema):
        raise ValueError("Vehicle table is missing. Run python -m app.init_db first.")
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS condition varchar(4) DEFAULT 'used'"))
    connection.execute(text(f"UPDATE {table} SET condition='used' WHERE condition IS NULL"))
    connection.execute(text(f"ALTER TABLE {table} ALTER COLUMN condition SET DEFAULT 'used', ALTER COLUMN condition SET NOT NULL"))
    checks = {item["name"] for item in inspect(connection).get_check_constraints("vehicles", schema=schema)}
    if "ck_vehicles_condition" not in checks:
        connection.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT ck_vehicles_condition CHECK (condition IN ('new', 'used'))"))
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS sample_key varchar(100)"))
    unique = {item["name"] for item in inspect(connection).get_unique_constraints("vehicles", schema=schema)}
    if "uq_vehicles_sample_key" not in unique:
        connection.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT uq_vehicles_sample_key UNIQUE (sample_key)"))
    for name, expression in (("price", "price"), ("quantity", "quantity"), ("category", "lower(category)")):
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_vehicles_{name} ON {table} ({expression})"))

    warnings = []
    if enable_trigram:
        try:
            with connection.begin_nested():
                connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA {quote(schema)}"))
        except DBAPIError:
            warnings.append("pg_trgm could not be enabled; partial search remains available.")
    extension_schema = connection.scalar(text(
        "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='pg_trgm'"
    ))
    if extension_schema:
        # Match the lower(...) expressions used by search. Tiny catalogues may
        # still use sequential scans; GIN supports growth and leading wildcards.
        operator_class = f"{quote(extension_schema)}.gin_trgm_ops"
        for name, expression in (("make", "lower(make)"), ("model", "lower(model)"),
                                 ("name", "lower(make || ' ' || model)")):
            connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_vehicles_{name}_trgm ON {table} USING gin (({expression}) {operator_class})"))
    return {"trigram_enabled": bool(extension_schema), "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-trigram", action="store_true", help="Optionally install pg_trgm if permissions allow")
    args = parser.parse_args()
    engine = get_engine()
    try:
        with engine.begin() as connection:
            result = migrate(connection, args.enable_trigram)
        print("Phase 1 migration complete. Existing data preserved.")
        print("Trigram search:", "enabled" if result["trigram_enabled"] else "unavailable; using partial matches")
        for warning in result["warnings"]:
            print(warning)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
