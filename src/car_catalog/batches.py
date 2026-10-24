from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar
from car_catalog.models import Car

T = TypeVar("T")


def batched_cars(cars: Iterable[Car], batch_size: int) -> Iterator[list[Car]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    iterator = iter(cars)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def dynamic_batched(iterable: Iterable[T], batch_size: int) -> Iterator[list[T]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch
