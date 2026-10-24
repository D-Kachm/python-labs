from typing import Any, Sequence
from car_catalog.abstractions import AbstractSearchCriteria
from car_catalog.models import ElectricCar
from car_catalog.protocols import SearchCriteria


class BrandCriteria(AbstractSearchCriteria):
    def __init__(self, brand: str) -> None:
        self.brand = brand.strip().lower()

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "brand"):
            return False
        return str(vehicle.brand).strip().lower() == self.brand


class ModelCriteria(AbstractSearchCriteria):
    def __init__(self, model: str) -> None:
        self.model = model.strip().lower()

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "model"):
            return False
        return str(vehicle.model).strip().lower() == self.model


class BrandAndModelCriteria(AbstractSearchCriteria):
    def __init__(self, brand: str, model: str) -> None:
        self.brand = brand.strip().lower()
        self.model = model.strip().lower()

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "brand") or not hasattr(vehicle, "model"):
            return False
        return str(vehicle.brand).strip().lower() == self.brand and str(vehicle.model).strip().lower() == self.model


class YearRangeCriteria(AbstractSearchCriteria):
    def __init__(self, min_year: int, max_year: int | None = None) -> None:
        self.min_year = min_year
        self.max_year = max_year

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "year"):
            return False
        val = int(vehicle.year)
        if val < self.min_year:
            return False
        if self.max_year is not None and val > self.max_year:
            return False
        return True


class PriceRangeCriteria(AbstractSearchCriteria):
    def __init__(self, min_price: float, max_price: float) -> None:
        self.min_price = min_price
        self.max_price = max_price

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "price"):
            return False
        val = float(vehicle.price)
        return self.min_price <= val <= self.max_price


class MaxMileageCriteria(AbstractSearchCriteria):
    def __init__(self, max_mileage: float) -> None:
        self.max_mileage = max_mileage

    def matches(self, vehicle: Any) -> bool:
        if not hasattr(vehicle, "mileage"):
            return False
        return float(vehicle.mileage) <= self.max_mileage


class ElectricOnlyCriteria(AbstractSearchCriteria):
    def matches(self, vehicle: Any) -> bool:
        return isinstance(vehicle, ElectricCar)


class AndCriteria(AbstractSearchCriteria):
    def __init__(self, criteria: Sequence[SearchCriteria]) -> None:
        self.criteria = list(criteria)

    def matches(self, vehicle: Any) -> bool:
        return all(c.matches(vehicle) for c in self.criteria)


class OrCriteria(AbstractSearchCriteria):
    def __init__(self, criteria: Sequence[SearchCriteria]) -> None:
        self.criteria = list(criteria)

    def matches(self, vehicle: Any) -> bool:
        return any(c.matches(vehicle) for c in self.criteria)
