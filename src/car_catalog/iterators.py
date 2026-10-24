from collections.abc import Iterable, Iterator, Sequence
from typing import Any
from car_catalog.models import Car


class CarCatalogIterator:
    def __init__(self, cars: Sequence[Car]) -> None:
        self._cars = cars
        self._index = 0
        self._length = len(cars)

    def __iter__(self) -> "CarCatalogIterator":
        return self

    def __next__(self) -> Car:
        if self._index >= self._length:
            raise StopIteration
        car = self._cars[self._index]
        self._index += 1
        return car


class CarCatalogIterable:
    def __init__(self, cars: Sequence[Car]) -> None:
        self._cars = tuple(cars)

    def __iter__(self) -> CarCatalogIterator:
        return CarCatalogIterator(self._cars)

    def __len__(self) -> int:
        return len(self._cars)


def recursive_flatten(nested: Iterable[Any]) -> Iterator[Any]:
    for item in nested:
        if isinstance(item, (list, tuple, set)):
            yield from recursive_flatten(item)
        else:
            yield item
