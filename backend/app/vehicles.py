from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select, update

from app.auth import DatabaseSession, get_current_user, require_admin
from app.models import Vehicle


class VehicleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    year: int | None = Field(default=None, strict=True, ge=1886)
    category: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    quantity: int = Field(strict=True, ge=0, le=2**31 - 1)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value):
        if value is not None and value > datetime.now(timezone.utc).year + 1:
            raise ValueError("Year cannot be later than next year")
        return value


class VehicleResponse(VehicleRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RestockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(strict=True, gt=0, le=2**31 - 1)


class VehicleSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    min_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    max_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must not exceed max_price")
        return self


router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])
VehicleId = Annotated[int, Path(ge=1, le=2**31 - 1)]


@router.post("", status_code=201, response_model=VehicleResponse, dependencies=[Depends(require_admin)])
def create_vehicle(payload: VehicleRequest, session: DatabaseSession):
    vehicle = Vehicle(**payload.model_dump())
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleResponse], dependencies=[Depends(get_current_user)])
def list_vehicles(session: DatabaseSession):
    return session.scalars(select(Vehicle).order_by(Vehicle.id)).all()


@router.get("/search", response_model=list[VehicleResponse], dependencies=[Depends(get_current_user)])
def search_vehicles(filters: Annotated[VehicleSearch, Query()], session: DatabaseSession):
    statement = select(Vehicle)
    for name in ("make", "model", "category"):
        value = getattr(filters, name)
        if value is not None:
            statement = statement.where(func.lower(getattr(Vehicle, name)) == value.lower())
    if filters.min_price is not None:
        statement = statement.where(Vehicle.price >= filters.min_price)
    if filters.max_price is not None:
        statement = statement.where(Vehicle.price <= filters.max_price)
    return session.scalars(statement.order_by(Vehicle.id)).all()


def get_vehicle_for_update(session, vehicle_id):
    # Lock the row until commit so concurrent edits/deletes cannot remove it mid-request.
    vehicle = session.get(Vehicle, vehicle_id, with_for_update=True)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse, dependencies=[Depends(require_admin)])
def update_vehicle(vehicle_id: VehicleId, payload: VehicleRequest, session: DatabaseSession):
    """Replace all editable fields; the generated ID remains unchanged."""
    vehicle = get_vehicle_for_update(session, vehicle_id)
    for name, value in payload.model_dump().items():
        setattr(vehicle, name, value)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_vehicle(vehicle_id: VehicleId, session: DatabaseSession):
    vehicle = get_vehicle_for_update(session, vehicle_id)
    session.delete(vehicle)
    session.commit()
    return Response(status_code=204)


def change_stock(session, vehicle_id, delta):
    # PostgreSQL checks this predicate while updating the row, including after
    # waiting for a concurrent writer. No separate read/check/write race exists.
    stock_condition = (
        Vehicle.quantity >= -delta if delta < 0
        else Vehicle.quantity <= (2**31 - 1) - delta
    )
    vehicle = session.scalar(
        update(Vehicle)
        .where(Vehicle.id == vehicle_id, stock_condition)
        .values(quantity=Vehicle.quantity + delta)
        .returning(Vehicle)
    )
    if vehicle is None:
        if session.get(Vehicle, vehicle_id) is None:
            raise HTTPException(404, "Vehicle not found")
        detail = "Vehicle out of stock" if delta < 0 else "Stock quantity limit exceeded"
        raise HTTPException(409, detail)
    # Capture this operation's result before commit expires the ORM instance.
    response = VehicleResponse.model_validate(vehicle)
    session.commit()
    return response


@router.post("/{vehicle_id}/purchase", response_model=VehicleResponse,
             dependencies=[Depends(get_current_user)])
def purchase_vehicle(vehicle_id: VehicleId, session: DatabaseSession):
    """Purchase one vehicle; authentication is required for every purchase."""
    return change_stock(session, vehicle_id, -1)


@router.post("/{vehicle_id}/restock", response_model=VehicleResponse,
             dependencies=[Depends(require_admin)])
def restock_vehicle(vehicle_id: VehicleId, payload: RestockRequest, session: DatabaseSession):
    return change_stock(session, vehicle_id, payload.quantity)
