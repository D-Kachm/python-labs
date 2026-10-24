from dataclasses import dataclass
from typing import Generic, NotRequired, TypeVar, TypedDict
from car_catalog.models import Car, ElectricCar, Vehicle
from car_catalog.specifications import VehicleSpecification

T = TypeVar("T")


class VehiclePayload(TypedDict):
    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: float
    currency: NotRequired[str]
    body_type: NotRequired[str]
    horsepower: NotRequired[int]


class ElectricVehiclePayload(TypedDict):
    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: float
    battery_capacity: float
    range_km: float
    currency: NotRequired[str]


@dataclass
class Result(Generic[T]):
    value: T | None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def vehicle_from_payload(payload: VehiclePayload) -> Car:
    spec: VehicleSpecification | None = None
    if "body_type" in payload or "horsepower" in payload:
        spec = VehicleSpecification(
            engine_type="ICE",
            transmission="Manual",
            horsepower=payload.get("horsepower", 150),
            fuel_type="Gasoline",
            body_type=payload.get("body_type", "Sedan"),
        )
    return Car(
        id=payload["id"],
        brand=payload["brand"],
        model=payload["model"],
        year=payload["year"],
        price=payload["price"],
        mileage=payload["mileage"],
        specification=spec,
    )


def electric_vehicle_from_payload(payload: ElectricVehiclePayload) -> ElectricCar:
    spec = VehicleSpecification(
        engine_type="Electric",
        transmission="Single-speed",
        horsepower=200,
        fuel_type="Electricity",
        body_type="SUV",
    )
    return ElectricCar(
        id=payload["id"],
        brand=payload["brand"],
        model=payload["model"],
        year=payload["year"],
        price=payload["price"],
        mileage=payload["mileage"],
        battery_capacity=payload["battery_capacity"],
        range_km=payload["range_km"],
        specification=spec,
    )


def vehicle_to_payload(vehicle: Vehicle) -> VehiclePayload:
    payload: VehiclePayload = {
        "id": vehicle.id,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "year": vehicle.year,
        "price": vehicle.price,
        "mileage": vehicle.mileage,
    }
    if vehicle.specification is not None:
        payload["body_type"] = vehicle.specification.body_type
        payload["horsepower"] = vehicle.specification.horsepower
    return payload
