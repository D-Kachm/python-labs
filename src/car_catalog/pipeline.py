import csv
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Callable
from car_catalog.filters import (
    filter_by_brand_and_year_stream,
    filter_cars_stream,
    validate_cars,
)
from car_catalog.models import Car
from car_catalog.parsers import clean_lines, parse_csv_rows
from car_catalog.readers import read_lines
from car_catalog.transformations import normalize_car_names


def build_streaming_pipeline(
    path: Path,
    brand: str | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    error_tracker: dict[str, int] | None = None,
) -> Iterator[Car]:
    lines = read_lines(path)
    cleaned = clean_lines(lines)
    rows = parse_csv_rows(cleaned)
    valid_cars = validate_cars(rows, error_tracker=error_tracker)
    normalized = normalize_car_names(valid_cars)
    filtered = filter_by_brand_and_year_stream(normalized, brand=brand, min_year=min_year, max_year=max_year)
    if min_price is not None or max_price is not None:
        filtered = filter_cars_stream(
            filtered,
            lambda c: (min_price is None or c.price >= min_price) and (max_price is None or c.price <= max_price),
        )
    return filtered


def find_first_car(cars: Iterable[Car], predicate: Callable[[Car], bool]) -> Car | None:
    for car in cars:
        if predicate(car):
            return car
    return None


def export_stream_to_csv(cars: Iterable[Car], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "brand", "model", "year", "price", "mileage"])
        for car in cars:
            writer.writerow(car.to_csv_row())
            count += 1
    return count
