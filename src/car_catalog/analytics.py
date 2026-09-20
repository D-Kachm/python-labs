from typing import Any, Callable
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
