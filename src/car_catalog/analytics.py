from functools import lru_cache
import math
import random
from typing import Any, Callable
import numpy as np
from car_catalog.decorators import measure_time
from car_catalog.models import Car


@measure_time
def calculate_average_price(cars: list[Car]) -> float:
    if not cars:
        return 0.0
    return sum(c.price for c in cars) / len(cars)


def calculate_average_prices(*prices: float) -> float:
    if not prices:
        return 0.0
    return sum(prices) / len(prices)


def create_car_record(**fields: Any) -> Car:
    return Car(
        id=int(fields["id"]),
        brand=str(fields["brand"]),
        model=str(fields["model"]),
        year=int(fields["year"]),
        price=float(fields["price"]),
        mileage=float(fields["mileage"]),
    )


def find_most_expensive_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None
    return max(cars, key=lambda c: c.price)


def find_lowest_mileage_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None
    return min(cars, key=lambda c: c.mileage)


def sort_by_price(cars: list[Car], reverse: bool = False) -> list[Car]:
    return sorted(cars, key=lambda c: c.price, reverse=reverse)


def sort_cars(cars: list[Car], key: Callable[[Car], Any], reverse: bool = False) -> list[Car]:
    return sorted(cars, key=key, reverse=reverse)


def create_price_filter(min_price: float, max_price: float) -> Callable[[Car], bool]:
    def predicate(car: Car) -> bool:
        return min_price <= car.price <= max_price

    return predicate


def create_mileage_filter(max_mileage: float) -> Callable[[Car], bool]:
    def predicate(car: Car) -> bool:
        return car.mileage <= max_mileage

    return predicate


def get_price_range(cars: list[Car]) -> tuple[float, float]:
    if not cars:
        return (0.0, 0.0)
    prices = [c.price for c in cars]
    return (min(prices), max(prices))


def get_catalog_summary(cars: list[Car]) -> dict[str, Any]:
    if not cars:
        return {}
    min_p, max_p = get_price_range(cars)
    return {
        "total_count": len(cars),
        "average_price": calculate_average_price(cars),
        "min_price": min_p,
        "max_price": max_p,
        "most_expensive": find_most_expensive_car(cars),
        "lowest_mileage": find_lowest_mileage_car(cars),
    }


def generate_sample_prices(count: int, seed: int = 42) -> list[float]:
    rnd = random.Random(seed)
    return [round(rnd.uniform(10000.0, 150000.0), 2) for _ in range(count)]


def generate_sample_mileages(count: int, seed: int = 42) -> list[float]:
    rnd = random.Random(seed)
    return [round(rnd.uniform(500.0, 300000.0), 1) for _ in range(count)]


def calculate_efficiency_score(value: float) -> float:
    result = value
    for _ in range(100):
        result = math.sin(result) ** 2 + math.cos(result) ** 2 + math.sqrt(abs(result) + 1.0)
    return result


def calculate_scores_sequential(values: list[float]) -> list[float]:
    return [calculate_efficiency_score(v) for v in values]


def statistics_python(values: list[float]) -> dict[str, float]:
    if not values:
        return {"average": 0.0, "minimum": 0.0, "maximum": 0.0, "std": 0.0}
    count = len(values)
    avg = sum(values) / count
    min_val = min(values)
    max_val = max(values)
    variance = sum((x - avg) ** 2 for x in values) / count
    return {
        "average": float(avg),
        "minimum": float(min_val),
        "maximum": float(max_val),
        "std": float(math.sqrt(variance)),
    }


def statistics_numpy(values: list[float]) -> dict[str, float]:
    if not values:
        return {"average": 0.0, "minimum": 0.0, "maximum": 0.0, "std": 0.0}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "average": float(arr.mean()),
        "minimum": float(arr.min()),
        "maximum": float(arr.max()),
        "std": float(arr.std()),
    }


@lru_cache(maxsize=128)
def cached_brand_statistics(brand_name: str, version: int = 1) -> dict[str, float]:
    prices = generate_sample_prices(10_000, seed=abs(hash(brand_name)) % 10000 + version)
    return statistics_numpy(prices)


def invalidate_brand_statistics_cache() -> None:
    cached_brand_statistics.cache_clear()
