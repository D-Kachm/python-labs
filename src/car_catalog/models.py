from abc import ABC
from typing import Any, Iterator, Sequence
from car_catalog.protocols import SearchCriteria
from car_catalog.specifications import VehicleSpecification
from car_catalog.value_objects import Mileage, Money


class Vehicle(ABC):
    def __init__(
        self,
        id: int,
        brand: str,
        model: str,
        year: int,
        price: float,
        mileage: float,
        specification: VehicleSpecification | None = None,
    ) -> None:
        if id <= 0:
            raise ValueError("ID must be positive")
        if not brand or not model:
            raise ValueError("Brand and model cannot be empty")
        if year < 1886:
            raise ValueError("Invalid manufacturing year")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if mileage < 0:
            raise ValueError("Mileage cannot be negative")

        self.id = id
        self.brand = brand
        self.model = model
        self.year = year
        self._price = float(price)
        self._mileage = float(mileage)
        self.specification = specification

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        if value < 0:
            raise ValueError("Price cannot be negative")
        self._price = float(value)

    @property
    def mileage(self) -> float:
        return self._mileage

    @mileage.setter
    def mileage(self, value: float) -> None:
        if value < 0:
            raise ValueError("Mileage cannot be negative")
        self._mileage = float(value)

    @property
    def price_money(self) -> Money:
        return Money(self._price, "USD")

    @property
    def mileage_vo(self) -> Mileage:
        return Mileage(self._mileage, "km")

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"

    @property
    def age(self) -> int:
        return 2026 - self.year

    def to_tuple(self) -> tuple[int, str, str, int, float, float]:
        return (self.id, self.brand, self.model, self.year, self._price, self._mileage)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "price": self._price,
            "mileage": self._mileage,
        }
        if self.specification is not None:
            data["specification"] = self.specification.to_dict()
        return data

    def to_csv_row(self) -> list[str]:
        return [
            str(self.id),
            self.brand,
            self.model,
            str(self.year),
            f"{self._price:.2f}",
            f"{self._mileage:.1f}",
        ]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vehicle):
            return NotImplemented
        return (
            self.id == other.id
            and self.brand == other.brand
            and self.model == other.model
            and self.year == other.year
            and self._price == other._price
            and self._mileage == other._mileage
        )

    def __lt__(self, other: "Vehicle") -> bool:
        if not isinstance(other, Vehicle):
            return NotImplemented
        return self._price < other._price

    def __hash__(self) -> int:
        return hash((self.id, self.brand, self.model, self.year))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id!r}, brand={self.brand!r}, "
            f"model={self.model!r}, year={self.year!r}, price={self._price!r}, "
            f"mileage={self._mileage!r})"
        )

    def __str__(self) -> str:
        return f"{self.full_name} ({self.year}) - {self._price:.2f}$ [{self._mileage:.1f} km]"


class Car(Vehicle):
    def __init__(
        self,
        id: int,
        brand: str,
        model: str,
        year: int,
        price: float,
        mileage: float,
        specification: VehicleSpecification | None = None,
    ) -> None:
        super().__init__(
            id=id,
            brand=brand,
            model=model,
            year=year,
            price=price,
            mileage=mileage,
            specification=specification,
        )

    def replace(self, **changes: Any) -> "Car":
        return Car(
            id=int(changes.get("id", self.id)),
            brand=str(changes.get("brand", self.brand)),
            model=str(changes.get("model", self.model)),
            year=int(changes.get("year", self.year)),
            price=float(changes.get("price", self.price)),
            mileage=float(changes.get("mileage", self.mileage)),
            specification=changes.get("specification", self.specification),
        )


class ElectricCar(Car):
    def __init__(
        self,
        id: int,
        brand: str,
        model: str,
        year: int,
        price: float,
        mileage: float,
        battery_capacity: float,
        range_km: float,
        specification: VehicleSpecification | None = None,
    ) -> None:
        super().__init__(
            id=id,
            brand=brand,
            model=model,
            year=year,
            price=price,
            mileage=mileage,
            specification=specification,
        )
        if battery_capacity <= 0:
            raise ValueError("Battery capacity must be strictly positive")
        if range_km <= 0:
            raise ValueError("Range must be strictly positive")
        self.battery_capacity = float(battery_capacity)
        self.range_km = float(range_km)

    @property
    def energy_consumption(self) -> float:
        if self.range_km == 0:
            return 0.0
        return round((self.battery_capacity / self.range_km) * 100, 2)

    def replace(self, **changes: Any) -> "ElectricCar":
        return ElectricCar(
            id=int(changes.get("id", self.id)),
            brand=str(changes.get("brand", self.brand)),
            model=str(changes.get("model", self.model)),
            year=int(changes.get("year", self.year)),
            price=float(changes.get("price", self.price)),
            mileage=float(changes.get("mileage", self.mileage)),
            battery_capacity=float(changes.get("battery_capacity", self.battery_capacity)),
            range_km=float(changes.get("range_km", self.range_km)),
            specification=changes.get("specification", self.specification),
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["battery_capacity"] = self.battery_capacity
        data["range_km"] = self.range_km
        data["energy_consumption"] = self.energy_consumption
        return data

    def __str__(self) -> str:
        return (
            f"⚡ {self.full_name} ({self.year}) [EV {self.battery_capacity}kWh, {self.range_km}km] - "
            f"{self.price:.2f}$ [{self.mileage:.1f} km]"
        )


class VehicleCatalog(Sequence[Vehicle]):
    def __init__(self, vehicles: list[Vehicle] | None = None) -> None:
        self._items: list[Vehicle] = list(vehicles or [])

    def add(self, vehicle: Vehicle) -> None:
        self._items.append(vehicle)

    def get(self, vehicle_id: int) -> Vehicle | None:
        for v in self._items:
            if v.id == vehicle_id:
                return v
        return None

    def remove(self, vehicle_id: int) -> bool:
        for idx, v in enumerate(self._items):
            if v.id == vehicle_id:
                del self._items[idx]
                return True
        return False

    def most_expensive(self) -> Vehicle | None:
        if not self._items:
            return None
        return max(self._items, key=lambda v: v.price)

    def lowest_mileage(self) -> Vehicle | None:
        if not self._items:
            return None
        return min(self._items, key=lambda v: v.mileage)

    def average_price(self) -> float:
        if not self._items:
            return 0.0
        return round(sum(v.price for v in self._items) / len(self._items), 2)

    def filter_by_year(self, year: int) -> list[Vehicle]:
        return [v for v in self._items if v.year == year]

    def search(self, criteria: SearchCriteria) -> list[Vehicle]:
        return [v for v in self._items if criteria.matches(v)]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Vehicle]:
        return iter(self._items)

    def __getitem__(self, index: Any) -> Any:
        return self._items[index]

    def __contains__(self, item: object) -> bool:
        if isinstance(item, int):
            return any(v.id == item for v in self._items)
        return item in self._items

    def __add__(self, other: "VehicleCatalog") -> "VehicleCatalog":
        if not isinstance(other, VehicleCatalog):
            return NotImplemented
        return VehicleCatalog(self._items + other._items)

    def __repr__(self) -> str:
        return f"VehicleCatalog(items={self._items!r})"

    def __str__(self) -> str:
        return f"VehicleCatalog({len(self._items)} vehicles)"
