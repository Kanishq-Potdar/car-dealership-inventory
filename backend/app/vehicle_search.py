"""Parameterized partial search, with optional PostgreSQL trigram matching."""
from sqlalchemy import case, func, or_, select, text
from sqlalchemy.sql import quoted_name

from app.models import Vehicle


def trigram_schema(session):
    return session.scalar(text(
        "SELECT n.nspname FROM pg_extension e "
        "JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='pg_trgm'"
    ))


def search_statement(session, filters):
    statement = select(Vehicle)
    ranks = []
    schema = trigram_schema(session) if any((filters.make, filters.model, filters.q)) else None
    if schema:
        session.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.3', true)"))
    quoted_schema = session.get_bind().dialect.identifier_preparer.quote(schema) if schema else None

    def match(column, value):
        column = func.lower(column)
        value = value.lower()
        contains = column.contains(value, autoescape=True)
        prefix = column.startswith(value, autoescape=True)
        similarity = 0
        predicate = contains
        if schema and len(value) >= 3 and any(char.isalnum() for char in value):
            similarity = getattr(func, quoted_name(schema, True)).similarity(column, value)
            predicate = or_(contains, column.bool_op(f"OPERATOR({quoted_schema}.%)")(value))
        rank = case((column == value, 100), (prefix, 70), (contains, 50), else_=similarity * 20)
        return predicate, rank

    for name in ("make", "model"):
        if value := getattr(filters, name):
            predicate, rank = match(getattr(Vehicle, name), value)
            statement = statement.where(predicate)
            ranks.append(rank)
    if filters.q:
        matches = [match(column, filters.q) for column in
                   (Vehicle.make, Vehicle.model, Vehicle.make + " " + Vehicle.model)]
        statement = statement.where(or_(*(predicate for predicate, _ in matches)))
        ranks.append(func.greatest(*(rank for _, rank in matches)))
    if filters.category is not None:
        statement = statement.where(func.lower(Vehicle.category) == filters.category.lower())
    if filters.min_price is not None:
        statement = statement.where(Vehicle.price >= filters.min_price)
    if filters.max_price is not None:
        statement = statement.where(Vehicle.price <= filters.max_price)
    if ranks:
        statement = statement.order_by(sum(ranks).desc())
    return statement.order_by(Vehicle.id)
