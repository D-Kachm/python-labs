from dataclasses import dataclass

@dataclass
class Car:
    brand: str
    model: str
    year: int
    price: float
    mileage: float

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"