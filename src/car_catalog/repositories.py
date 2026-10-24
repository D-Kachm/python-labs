import sqlite3
from typing import Any, Callable, Generic, Iterator, TypeVar
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from car_catalog.abstractions import Repository
from car_catalog.db_models import CarEntity, Manufacturer
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

class SqlAlchemyManufacturerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, manufacturer: Manufacturer) -> Manufacturer:
        self.session.add(manufacturer)
        self.session.commit()
        self.session.refresh(manufacturer)
        return manufacturer

    def get_by_id(self, manufacturer_id: int) -> Manufacturer | None:
        return self.session.get(Manufacturer, manufacturer_id)

    def get_by_name(self, name: str) -> Manufacturer | None:
        statement = select(Manufacturer).where(Manufacturer.name == name)
        return self.session.scalar(statement)

    def get_all(self) -> list[Manufacturer]:
        statement = select(Manufacturer)
        return list(self.session.scalars(statement))

    def delete(self, manufacturer_id: int) -> bool:
        manufacturer = self.get_by_id(manufacturer_id)
        if manufacturer is None:
            return False
        self.session.delete(manufacturer)
        self.session.commit()
        return True

class SqlAlchemyCarRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, car: CarEntity) -> CarEntity:
        self.session.add(car)
        self.session.commit()
        self.session.refresh(car)
        return car

    def get_by_id(self, car_id: int) -> CarEntity | None:
        return self.session.get(CarEntity, car_id)

    def get_by_vin(self, vin: str) -> CarEntity | None:
        statement = select(CarEntity).where(CarEntity.vin == vin)
        return self.session.scalar(statement)

    def get_all(self) -> list[CarEntity]:
        statement = select(CarEntity)
        return list(self.session.scalars(statement))

    def find_by_model(self, model: str) -> list[CarEntity]:
        statement = select(CarEntity).where(CarEntity.model == model)
        return list(self.session.scalars(statement))

    def find_by_manufacturer_id(self, manufacturer_id: int) -> list[CarEntity]:
        statement = select(CarEntity).where(CarEntity.manufacturer_id == manufacturer_id)
        return list(self.session.scalars(statement))

    def find_by_manufacturer_name(self, name: str) -> list[CarEntity]:
        statement = (
            select(CarEntity)
            .join(Manufacturer, CarEntity.manufacturer_id == Manufacturer.id)
            .where(Manufacturer.name == name)
        )
        return list(self.session.scalars(statement))

    def filter_by_year(self, year: int) -> list[CarEntity]:
        statement = select(CarEntity).where(CarEntity.year == year)
        return list(self.session.scalars(statement))

    def filter_by_year_range(self, min_year: int, max_year: int) -> list[CarEntity]:
        statement = select(CarEntity).where(CarEntity.year >= min_year, CarEntity.year <= max_year)
        return list(self.session.scalars(statement))

    def get_most_expensive(self) -> CarEntity | None:
        statement = select(CarEntity).order_by(CarEntity.price.desc()).limit(1)
        return self.session.scalar(statement)

    def get_most_expensive_car(self) -> CarEntity | None:
        return self.get_most_expensive()

    def get_lowest_mileage(self) -> CarEntity | None:
        statement = select(CarEntity).order_by(CarEntity.mileage.asc()).limit(1)
        return self.session.scalar(statement)

    def get_lowest_mileage_car(self) -> CarEntity | None:
        return self.get_lowest_mileage()

    def get_average_price(self) -> float:
        statement = select(func.avg(CarEntity.price))
        result = self.session.scalar(statement)
        return float(result) if result is not None else 0.0

    def update_price(self, car_id: int, new_price: float) -> CarEntity | None:
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        car = self.get_by_id(car_id)
        if car is None:
            return None
        car.price = new_price
        self.session.commit()
        self.session.refresh(car)
        return car

    def update_mileage(self, car_id: int, new_mileage: float) -> CarEntity | None:
        if new_mileage < 0:
            raise ValueError("Mileage cannot be negative")
        car = self.get_by_id(car_id)
        if car is None:
            return None
        car.mileage = new_mileage
        self.session.commit()
        self.session.refresh(car)
        return car

    def delete(self, car_id: int) -> bool:
        car = self.get_by_id(car_id)
        if car is None:
            return False
        self.session.delete(car)
        self.session.commit()
        return True

    def get_manufacturer_statistics(self) -> list[dict[str, Any]]:
        statement = (
            select(
                Manufacturer.name.label("manufacturer"),
                func.count(CarEntity.id).label("total_cars"),
                func.avg(CarEntity.price).label("average_price"),
                func.min(CarEntity.price).label("min_price"),
                func.max(CarEntity.price).label("max_price"),
            )
            .join(CarEntity, Manufacturer.id == CarEntity.manufacturer_id)
            .group_by(Manufacturer.name)
        )
        rows = self.session.execute(statement).all()
        return [
            {
                "manufacturer": row.manufacturer,
                "total_cars": row.total_cars,
                "average_price": round(float(row.average_price), 2) if row.average_price else 0.0,
                "min_price": float(row.min_price) if row.min_price else 0.0,
                "max_price": float(row.max_price) if row.max_price else 0.0,
            }
            for row in rows
        ]

ManufacturerRepository = SqlAlchemyManufacturerRepository
CarRepository = SqlAlchemyCarRepository

def find_cars_by_manufacturer_dbapi(
    database_path: str,
    manufacturer_name: str,
) -> list[tuple[Any, ...]]:
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT c.id, m.name, c.model, c.year, c.price, c.mileage, c.vin
            FROM cars c
            JOIN manufacturers m ON c.manufacturer_id = m.id
            WHERE m.name = ?
            ORDER BY c.id ASC
            """,
            (manufacturer_name,),
        )
        return cursor.fetchall()

def bulk_update_prices_by_manufacturer(
    session: Session,
    manufacturer_id: int,
    multiplier: float,
    max_price_limit: float = 200_000.0,
) -> None:
    if multiplier <= 0:
        raise ValueError("Multiplier must be positive")
    try:
        statement = select(CarEntity).where(CarEntity.manufacturer_id == manufacturer_id)
        cars = list(session.scalars(statement))
        if not cars:
            raise ValueError(f"No cars found for manufacturer ID {manufacturer_id}")

        for car in cars:
            new_price = round(car.price * multiplier, 2)
            if new_price > max_price_limit:
                raise ValueError(
                    f"New price {new_price} for car ID {car.id} exceeds maximum limit {max_price_limit}"
                )
            car.price = new_price

        session.commit()
    except Exception:
        session.rollback()
        raise
