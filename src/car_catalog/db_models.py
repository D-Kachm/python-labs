from __future__ import annotations
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from car_catalog.database import Base
from car_catalog.models import Car


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Unknown")

    cars: Mapped[list[CarEntity]] = relationship(
        back_populates="manufacturer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Manufacturer(id={self.id!r}, name={self.name!r}, country={self.country!r})"


class CarEntity(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mileage: Mapped[float] = mapped_column(Float, nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True)

    manufacturer: Mapped[Manufacturer] = relationship(
        back_populates="cars",
    )

    @property
    def brand(self) -> str:
        return self.manufacturer.name if self.manufacturer is not None else ""

    @property
    def full_name(self) -> str:
        brand_name = self.brand
        return f"{brand_name} {self.model}".strip()

    def to_domain(self) -> Car:
        return Car(
            id=self.id,
            brand=self.brand,
            model=self.model,
            year=self.year,
            price=self.price,
            mileage=self.mileage,
        )

    @classmethod
    def from_domain(cls, car: Car, manufacturer_id: int, vin: str | None = None) -> CarEntity:
        return cls(
            id=car.id,
            manufacturer_id=manufacturer_id,
            model=car.model,
            year=car.year,
            price=car.price,
            mileage=car.mileage,
            vin=vin,
        )

    def __repr__(self) -> str:
        return (
            f"CarEntity(id={self.id!r}, manufacturer_id={self.manufacturer_id!r}, "
            f"model={self.model!r}, year={self.year!r}, price={self.price!r}, "
            f"mileage={self.mileage!r}, vin={self.vin!r})"
        )
