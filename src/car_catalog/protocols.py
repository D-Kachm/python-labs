from typing import Any, Protocol, TypeVar, runtime_checkable

@runtime_checkable
class HasId(Protocol):
    id: int

@runtime_checkable
class Priceable(Protocol):
    @property
    def price(self) -> float: ...

@runtime_checkable
class SearchCriteria(Protocol):
    def matches(self, vehicle: Any) -> bool: ...

@runtime_checkable
class VehicleNotifier(Protocol):
    def send(self, recipient: str, message: str) -> None: ...

@runtime_checkable
class Exportable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...

T = TypeVar("T")

class ReaderProtocol(Protocol[T]):
    def read_all(self) -> list[T]: ...
