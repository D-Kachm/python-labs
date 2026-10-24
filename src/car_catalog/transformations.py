from collections.abc import Iterable, Iterator
from car_catalog.models import Car


def normalize_car_names(cars: Iterable[Car]) -> Iterator[Car]:
    for car in cars:
        normalized_brand = car.brand.strip().title()
        normalized_model = car.model.strip()
        yield car.replace(brand=normalized_brand, model=normalized_model)


def apply_price_discount(cars: Iterable[Car], discount_percent: float) -> Iterator[Car]:
    multiplier = 1.0 - (discount_percent / 100.0)
    for car in cars:
        new_price = round(max(0.0, car.price * multiplier), 2)
        yield car.replace(price=new_price)


def convert_currency(cars: Iterable[Car], rate: float) -> Iterator[Car]:
    for car in cars:
        new_price = round(car.price * rate, 2)
        yield car.replace(price=new_price)
