from app.database import check_database_connection


def test_database_connection_returns_true():
    """Requires the PostgreSQL service from the root docker-compose.yml."""
    assert check_database_connection() is True
