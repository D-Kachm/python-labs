from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class VehicleSpecification:
    engine_type: str
    transmission: str
    horsepower: int
    fuel_type: str
    body_type: str = "Sedan"

    def __post_init__(self) -> None:
        if self.horsepower <= 0:
            raise ValueError("Horsepower must be strictly positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_type": self.engine_type,
            "transmission": self.transmission,
            "horsepower": self.horsepower,
            "fuel_type": self.fuel_type,
            "body_type": self.body_type,
        }

    def __str__(self) -> str:
        return f"{self.body_type} ({self.engine_type}, {self.horsepower} hp, {self.transmission}, {self.fuel_type})"
