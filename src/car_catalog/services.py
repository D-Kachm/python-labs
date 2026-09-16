from car_catalog.models import Car

def search_by_brand(cars: list[Car], brand: str) -> list[Car]:
    return [c for c in cars if c.brand.lower() == brand.lower()]

def filter_by_year(cars: list[Car], year: int) -> list[Car]:
    return [c for c in cars if c.year == year]

def find_most_expensive_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None
    return max(cars, key=lambda c: c.price)

def calculate_average_price(cars: list[Car]) -> float:
    if not cars:
        return 0.0
    return sum(c.price for c in cars) / len(cars)

def find_lowest_mileage_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None
    return min(cars, key=lambda c: c.mileage)