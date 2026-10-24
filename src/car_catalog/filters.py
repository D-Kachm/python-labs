from collections.abc import Iterable, Iterator
from typing import Callable
from car_catalog.models import Car

def validate_cars(
    rows: Iterable[dict[str, str]],
    error_tracker: dict[str, int] | None = None,
) -> Iterator[Car]:
    for row in rows:
        try:
            car_id = int(row["id"])
            brand = row["brand"].strip()
            model = row["model"].strip()
            year = int(row["year"])
            price = float(row["price"])
            mileage = float(row["mileage"])

            if car_id <= 0 or not brand or not model:
                if error_tracker is not None:
                    error_tracker["invalid_records"] = error_tracker.get("invalid_records", 0) + 1
                continue

            if not (1900 <= year <= 2026) or price < 0.0 or mileage < 0.0:
                if error_tracker is not None:
                    error_tracker["invalid_records"] = error_tracker.get("invalid_records", 0) + 1
                continue

            yield Car(
                id=car_id,
                brand=brand,
                model=model,
                year=year,
                price=price,
                mileage=mileage,
            )
        except (ValueError, KeyError, TypeError):
            if error_tracker is not None:
                error_tracker["invalid_records"] = error_tracker.get("invalid_records", 0) + 1
            continue

def filter_by_brand_stream(cars: Iterable[Car], brand: str) -> Iterator[Car]:
    target = brand.strip().lower()
    for car in cars:
        if car.brand.lower() == target:
            yield car

def filter_by_year_stream(cars: Iterable[Car], year: int) -> Iterator[Car]:
    for car in cars:
        if car.year == year:
            yield car

def filter_by_brand_and_year_stream(
    cars: Iterable[Car],
    brand: str | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
) -> Iterator[Car]:
    target_brand = brand.strip().lower() if brand else None
    for car in cars:
        if target_brand and car.brand.lower() != target_brand:
            continue
        if min_year is not None and car.year < min_year:
            continue
        if max_year is not None and car.year > max_year:
            continue
        yield car

def filter_cars_stream(cars: Iterable[Car], predicate: Callable[[Car], bool]) -> Iterator[Car]:
    for car in cars:
        if predicate(car):
            yield car
