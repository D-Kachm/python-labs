from dataclasses import dataclass
from typing import TypeVar

Number = TypeVar("Number", int, float)


@dataclass(frozen=True, slots=True)
class Money:
    amount: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} != {other.currency}")
        return Money(round(self.amount + other.amount, 2), self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} != {other.currency}")
        if self.amount < other.amount:
            raise ValueError("Resulting money amount cannot be negative")
        return Money(round(self.amount - other.amount, 2), self.currency)

    def __mul__(self, factor: float) -> "Money":
        if factor < 0:
            raise ValueError("Multiplier cannot be negative")
        return Money(round(self.amount * factor, 2), self.currency)

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} != {other.currency}")
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount!r}, currency={self.currency!r})"


@dataclass(frozen=True, slots=True)
class Mileage:
    value: float
    unit: str = "km"

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Mileage cannot be negative")

    def __add__(self, other: "Mileage") -> "Mileage":
        if not isinstance(other, Mileage):
            return NotImplemented
        if self.unit != other.unit:
            raise ValueError(f"Mileage unit mismatch: {self.unit} != {other.unit}")
        return Mileage(round(self.value + other.value, 1), self.unit)

    def __lt__(self, other: "Mileage") -> bool:
        if not isinstance(other, Mileage):
            return NotImplemented
        if self.unit != other.unit:
            raise ValueError(f"Mileage unit mismatch: {self.unit} != {other.unit}")
        return self.value < other.value

    def __str__(self) -> str:
        return f"{self.value:.1f} {self.unit}"

    def __repr__(self) -> str:
        return f"Mileage(value={self.value!r}, unit={self.unit!r})"


@dataclass(frozen=True, slots=True)
class VIN:
    code: str

    def __post_init__(self) -> None:
        cleaned = self.code.strip().upper()
        if len(cleaned) < 5 or not cleaned.isalnum():
            raise ValueError(f"Invalid VIN format: {self.code}")
        object.__setattr__(self, "code", cleaned)

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"VIN(code={self.code!r})"
