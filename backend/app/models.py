from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('customer', 'admin')", name="ck_users_role"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), server_default="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("condition IN ('new', 'used')", name="ck_vehicles_condition"),
        UniqueConstraint("sample_key", name="uq_vehicles_sample_key"),
        Index("ix_vehicles_price", "price"),
        Index("ix_vehicles_quantity", "quantity"),
        CheckConstraint("price > 0 AND price <= 9999999999.99", name="ck_vehicles_price"),
        CheckConstraint("quantity >= 0", name="ck_vehicles_quantity"),
        CheckConstraint("year >= 1886 AND year <= 9999", name="ck_vehicles_year"),
        CheckConstraint(
            "length(trim(make)) > 0 AND length(trim(model)) > 0 "
            "AND length(trim(category)) > 0",
            name="ck_vehicles_nonempty_text",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int | None]
    category: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int]
    condition: Mapped[str] = mapped_column(String(4), server_default="used")
    # Internal provenance key: never accepted from public API requests.
    sample_key: Mapped[str | None] = mapped_column(String(100))


Index("ix_vehicles_category", func.lower(Vehicle.category))
