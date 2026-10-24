from typing import Callable, Generic, Iterator, TypeVar
from car_catalog.abstractions import Repository
from car_catalog.models import Vehicle
from car_catalog.protocols import HasId

T = TypeVar("T", bound=HasId)

class InMemoryRepository(Repository[T], Generic[T]):
    def __init__(self) -> None:
        self._items: dict[int, T] = {}

    def add(self, item: T) -> None:
        self._items[item.id] = item

    def get(self, item_id: int) -> T | None:
        return self._items.get(item_id)

    def all(self) -> list[T]:
        return list(self._items.values())

    def remove(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None

    def filter(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self._items.values() if predicate(item)]

    def count(self) -> int:
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __contains__(self, item_id: int) -> bool:
        return item_id in self._items

    def __getitem__(self, item_id: int) -> T:
        return self._items[item_id]

class VehicleRepository(InMemoryRepository[Vehicle]):
    pass
