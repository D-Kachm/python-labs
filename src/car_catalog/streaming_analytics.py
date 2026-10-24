from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import accumulate, groupby, pairwise
from typing import Any
from car_catalog.models import Car

def streaming_average_price(cars: Iterable[Car]) -> float:
    total = 0.0
    count = 0
    for car in cars:
        total += car.price
        count += 1
    return total / count if count else 0.0

def streaming_min_max_price(cars: Iterable[Car]) -> tuple[float, float]:
    min_p: float | None = None
    max_p: float | None = None
    for car in cars:
        if min_p is None or car.price < min_p:
            min_p = car.price
        if max_p is None or car.price > max_p:
            max_p = car.price
    return (min_p if min_p is not None else 0.0, max_p if max_p is not None else 0.0)

def streaming_find_most_expensive(cars: Iterable[Car]) -> Car | None:
    best_car: Car | None = None
    for car in cars:
        if best_car is None or car.price > best_car.price:
            best_car = car
    return best_car

def streaming_find_lowest_mileage(cars: Iterable[Car]) -> Car | None:
    best_car: Car | None = None
    for car in cars:
        if best_car is None or car.mileage < best_car.mileage:
            best_car = car
    return best_car

def streaming_statistics(cars: Iterable[Car]) -> dict[str, Any]:
    count = 0
    total = 0.0
    min_p: float | None = None
    max_p: float | None = None
    most_expensive: Car | None = None
    lowest_mileage: Car | None = None
    brands: Counter[str] = Counter()

    for car in cars:
        count += 1
        total += car.price
        brands[car.brand] += 1

        if min_p is None or car.price < min_p:
            min_p = car.price
        if max_p is None or car.price > max_p:
            max_p = car.price

        if most_expensive is None or car.price > most_expensive.price:
            most_expensive = car
        if lowest_mileage is None or car.mileage < lowest_mileage.mileage:
            lowest_mileage = car

    average = total / count if count else 0.0

    return {
        "count": count,
        "total_value": total,
        "average_price": average,
        "min_price": min_p if min_p is not None else 0.0,
        "max_price": max_p if max_p is not None else 0.0,
        "most_expensive": most_expensive,
        "lowest_mileage": lowest_mileage,
        "brands": dict(brands),
    }

def streaming_groupby_brand(cars: Iterable[Car]) -> list[tuple[str, list[Car]]]:
    sorted_cars = sorted(cars, key=lambda c: c.brand)
    result: list[tuple[str, list[Car]]] = []
    for brand, group_iter in groupby(sorted_cars, key=lambda c: c.brand):
        result.append((brand, list(group_iter)))
    return result

def streaming_pairwise_price_diff(cars: Iterable[Car]) -> Iterator[tuple[Car, Car, float]]:
    for prev_car, curr_car in pairwise(cars):
        diff = round(curr_car.price - prev_car.price, 2)
        yield (prev_car, curr_car, diff)

def streaming_accumulate_prices(cars: Iterable[Car]) -> Iterator[float]:
    yield from accumulate(car.price for car in cars)
