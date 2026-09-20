from typing import Callable
from car_catalog.analytics import (
    calculate_average_price,
    find_lowest_mileage_car,
    find_most_expensive_car,
    sort_by_price,
)
from car_catalog.models import Car
from car_catalog.processors import (
    create_car_index,
    filter_by_brand,
    filter_by_year,
    find_car_by_id,
    get_unique_brands,
)

def search_by_brand(cars: list[Car], brand: str) -> list[Car]:
    return filter_by_brand(cars, brand)

def process_pipeline(cars: list[Car], *operations: Callable[[list[Car]], list[Car]]) -> list[Car]:
    result = cars
    for op in operations:
        result = op(result)
    return result
