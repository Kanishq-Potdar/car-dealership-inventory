"""Run `python -m app.init_db` from backend to create missing tables.

This does not drop tables or migrate existing ones.
"""

from app.database import get_engine
from app.models import Base


def main():
    engine = get_engine()
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
