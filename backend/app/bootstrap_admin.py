"""Create the first administrator without public role assignment or plaintext storage."""
from getpass import GetPassWarning, getpass
import warnings

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import RegisterRequest, password_hasher
from app.database import get_engine
from app.models import User


def create_first_admin(session, full_name, email, password):
    data = RegisterRequest(full_name=full_name, email=email, password=password)
    try:
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        # Serializes bootstrap commands and conflicts with concurrent registrations.
        table = User.__table__
        schema = session.connection().get_execution_options().get("schema_translate_map", {}).get(None)
        quote = session.get_bind().dialect.identifier_preparer.quote
        name = f"{quote(schema)}.{quote(table.name)}" if schema else quote(table.name)
        session.execute(text(f"LOCK TABLE {name} IN SHARE ROW EXCLUSIVE MODE"))
        if session.scalar(select(User.id).where(User.role == "admin").limit(1)) is not None:
            raise ValueError("An admin already exists; bootstrap will not create another.")
        if session.scalar(select(User.id).where(User.email == str(data.email))) is not None:
            raise ValueError("That email already exists; no account was changed.")
        user = User(full_name=data.full_name, email=str(data.email), role="admin",
                    password_hash=password_hasher.hash(data.password.get_secret_value()))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except Exception:
        session.rollback()
        raise


def main():
    engine = None
    try:
        name = input("Full name: ")
        email = input("Email: ")
        # Refuse getpass's echoing fallback when no secure terminal is available.
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Password (12-128 characters): ")
            confirmation = getpass("Confirm password: ")
        if password != confirmation:
            print("Passwords do not match. Nothing was created.")
            return 1
        engine = get_engine()
        with Session(engine) as session:
            create_first_admin(session, name, email, password)
        print("First administrator created.")
        return 0
    except ValidationError:
        print("Invalid name, email or password. Nothing was created.")
    except ValueError as error:
        print(str(error))
    except (GetPassWarning, EOFError, KeyboardInterrupt):
        print("A secure interactive terminal is required; bootstrap cancelled.")
    except SQLAlchemyError:
        print("Database operation failed. Check configuration, schema and concurrent activity; no credentials are displayed.")
    finally:
        if engine is not None:
            engine.dispose()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
