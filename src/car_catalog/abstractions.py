from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar
from car_catalog.protocols import HasId
from car_catalog.value_objects import Money

T = TypeVar("T", bound=HasId)


class DiscountPolicy(ABC):
    @abstractmethod
    def apply(self, price: Money) -> Money:
        pass


class NoDiscount(DiscountPolicy):
    def apply(self, price: Money) -> Money:
        return price


class PercentageDiscount(DiscountPolicy):
    def __init__(self, percent: float) -> None:
        if not (0 <= percent <= 100):
            raise ValueError("Discount percentage must be between 0 and 100")
        self._percent = percent

    @property
    def percent(self) -> float:
        return self._percent

    def apply(self, price: Money) -> Money:
        multiplier = 1.0 - (self._percent / 100.0)
        return price * multiplier


class ThresholdDiscount(DiscountPolicy):
    def __init__(self, threshold: Money, discount_amount: Money) -> None:
        if threshold.currency != discount_amount.currency:
            raise ValueError("Currencies of threshold and discount must match")
        self._threshold = threshold
        self._discount_amount = discount_amount

    def apply(self, price: Money) -> Money:
        if price.currency != self._threshold.currency:
            raise ValueError("Currency mismatch in discount application")
        if price.amount >= self._threshold.amount:
            return price - self._discount_amount
        return price


class AbstractSearchCriteria(ABC):
    @abstractmethod
    def matches(self, vehicle: Any) -> bool:
        pass


class Repository(ABC, Generic[T]):
    @abstractmethod
    def add(self, item: T) -> None:
        pass

    @abstractmethod
    def get(self, item_id: int) -> T | None:
        pass

    @abstractmethod
    def all(self) -> list[T]:
        pass

    @abstractmethod
    def remove(self, item_id: int) -> bool:
        pass

    @abstractmethod
    def filter(self, predicate: Callable[[T], bool]) -> list[T]:
        pass
