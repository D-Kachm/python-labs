from abc import ABC, abstractmethod
from typing import Any
from car_catalog.abstractions import DiscountPolicy, NoDiscount, PercentageDiscount, Repository
from car_catalog.models import Car, Vehicle
from car_catalog.notifiers import ConsoleNotifier
from car_catalog.protocols import VehicleNotifier
from car_catalog.repositories import InMemoryRepository
from car_catalog.value_objects import Money

class TightlyCoupledService:
    def __init__(self) -> None:
        self.repository: InMemoryRepository[Vehicle] = InMemoryRepository[Vehicle]()
        self.notifier: ConsoleNotifier = ConsoleNotifier()
        self.discount_policy: PercentageDiscount = PercentageDiscount(5.0)

    def register_car(self, car: Vehicle) -> None:
        self.repository.add(car)
        self.notifier.send("admin@company.com", f"Car added: {car.full_name}")

class DecoupledService:
    def __init__(
        self,
        repository: Repository[Vehicle],
        notifier: VehicleNotifier,
        discount_policy: DiscountPolicy,
    ) -> None:
        self.repository = repository
        self.notifier = notifier
        self.discount_policy = discount_policy

    def register_car(self, car: Vehicle) -> None:
        self.repository.add(car)
        self.notifier.send("admin@company.com", f"Car added: {car.full_name}")

class BaseVehicleProcessor(ABC):
    @abstractmethod
    def read_source(self, raw_input: str) -> list[str]:
        pass

    @abstractmethod
    def parse_item(self, line: str) -> Vehicle:
        pass

    def process(self, raw_input: str) -> list[Vehicle]:
        lines = self.read_source(raw_input)
        return [self.parse_item(line) for line in lines if line.strip()]

class CsvVehicleProcessor(BaseVehicleProcessor):
    def read_source(self, raw_input: str) -> list[str]:
        return raw_input.strip().splitlines()

    def parse_item(self, line: str) -> Vehicle:
        parts = [p.strip() for p in line.split(",")]
        return Car(
            id=int(parts[0]),
            brand=parts[1],
            model=parts[2],
            year=int(parts[3]),
            price=float(parts[4]),
            mileage=float(parts[5]),
        )

class VehicleParser:
    def parse(self, line: str) -> dict[str, Any]:
        parts = [p.strip() for p in line.split(",")]
        return {
            "id": int(parts[0]),
            "brand": parts[1],
            "model": parts[2],
            "year": int(parts[3]),
            "price": float(parts[4]),
            "mileage": float(parts[5]),
        }

class VehicleValidator:
    def validate(self, data: dict[str, Any]) -> bool:
        return (
            data.get("id", 0) > 0
            and bool(data.get("brand"))
            and bool(data.get("model"))
            and data.get("year", 0) >= 1886
            and data.get("price", 0.0) >= 0.0
            and data.get("mileage", 0.0) >= 0.0
        )

class VehicleFormatter:
    def format(self, vehicle: Vehicle) -> str:
        return f"{vehicle.full_name} ({vehicle.year}) - {vehicle.price:.2f}$"

class ComposedVehicleProcessor:
    def __init__(
        self,
        parser: VehicleParser,
        validator: VehicleValidator,
        formatter: VehicleFormatter,
    ) -> None:
        self.parser = parser
        self.validator = validator
        self.formatter = formatter

    def process_lines(self, lines: list[str]) -> list[Vehicle]:
        results: list[Vehicle] = []
        for line in lines:
            if not line.strip():
                continue
            data = self.parser.parse(line)
            if self.validator.validate(data):
                car = Car(
                    id=data["id"],
                    brand=data["brand"],
                    model=data["model"],
                    year=data["year"],
                    price=data["price"],
                    mileage=data["mileage"],
                )
                results.append(car)
        return results
