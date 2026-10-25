from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update
from pydantic_settings import BaseSettings

from app.auth import DatabaseSession, get_current_user, require_admin
from app.models import Vehicle
from app.database import DatabaseSettings
from app.vehicle_search import search_statement


class VehicleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    year: int | None = Field(default=None, strict=True, ge=1886)
    category: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    quantity: int = Field(strict=True, ge=0, le=2**31 - 1)
    condition: Literal["new", "used"] = "used"

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


class StockAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delta: int = Field(strict=True, ge=-(2**31 - 1), le=2**31 - 1)

    @field_validator("delta")
    @classmethod
    def nonzero(cls, value):
        if value == 0:
            raise ValueError("Stock adjustment must be nonzero")
        return value


class InventorySettings(BaseSettings):
    model_config = DatabaseSettings.model_config
    low_stock_threshold: int = Field(default=3, ge=0, le=2**31 - 1)


class StockAlerts(BaseModel):
    threshold: int
    vehicles: list[VehicleResponse]


class VehicleSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    q: str | None = Field(default=None, min_length=1, max_length=200)
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
    return session.scalars(search_statement(session, filters)).all()


@router.get("/alerts", response_model=StockAlerts, dependencies=[Depends(require_admin)])
def stock_alerts(session: DatabaseSession, out_of_stock: bool = False):
    threshold = InventorySettings().low_stock_threshold
    vehicles = session.scalars(select(Vehicle).where(
        Vehicle.quantity <= (0 if out_of_stock else threshold)
    ).order_by(Vehicle.quantity, Vehicle.id)).all()
    return StockAlerts(threshold=threshold, vehicles=vehicles)


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
        if name == "condition" and name not in payload.model_fields_set:
            continue
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


@router.post("/{vehicle_id}/adjust-stock", response_model=VehicleResponse,
             dependencies=[Depends(require_admin)])
def adjust_stock(vehicle_id: VehicleId, payload: StockAdjustment, session: DatabaseSession):
    return change_stock(session, vehicle_id, payload.delta)
