from collections import Counter, defaultdict
from typing import Callable
from car_catalog.models import Car

def get_unique_brands(cars: list[Car]) -> set[str]:
    return {car.brand for car in cars}

def create_car_index(cars: list[Car]) -> dict[int, Car]:
    return {car.id: car for car in cars}

def find_car_by_id(index: dict[int, Car], car_id: int) -> Car | None:
    return index.get(car_id)

def find_car_linear(cars: list[Car], car_id: int) -> Car | None:
    for car in cars:
        if car.id == car_id:
            return car
    return None

def filter_by_brand(cars: list[Car], brand: str) -> list[Car]:
    target = brand.strip().lower()
    return [c for c in cars if c.brand.lower() == target]

def filter_by_year(cars: list[Car], year: int) -> list[Car]:
    return [c for c in cars if c.year == year]

def filter_cars(cars: list[Car], predicate: Callable[[Car], bool]) -> list[Car]:
    return [c for c in cars if predicate(c)]

def group_by_brand(cars: list[Car]) -> dict[str, list[Car]]:
    result: defaultdict[str, list[Car]] = defaultdict(list)
    for car in cars:
        result[car.brand].append(car)
    return dict(result)

def group_by_brand_and_year(cars: list[Car]) -> dict[str, dict[int, list[Car]]]:
    grouped: defaultdict[str, defaultdict[int, list[Car]]] = defaultdict(lambda: defaultdict(list))
    for car in cars:
        grouped[car.brand][car.year].append(car)
    return {brand: dict(years) for brand, years in grouped.items()}

def count_by_brand(cars: list[Car]) -> Counter[str]:
    return Counter(car.brand for car in cars)
