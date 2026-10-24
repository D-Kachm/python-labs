from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any
import pytest
from car_catalog.abstractions import NoDiscount, PercentageDiscount
from car_catalog.models import Car, ElectricCar, Vehicle
from car_catalog.repositories import VehicleRepository

@pytest.fixture
def sample_car() -> Car:
    return Car(
        id=1,
        brand="Toyota",
        model="Camry",
        year=2021,
        price=26000.0,
        mileage=45000,
    )

@pytest.fixture
def sample_electric_car() -> ElectricCar:
    return ElectricCar(
        id=2,
        brand="Tesla",
        model="Model 3",
        year=2023,
        price=42000.0,
        mileage=15000,
        battery_capacity=75.0,
        range_km=500,
    )

@pytest.fixture
def sample_cars_list(sample_car: Car, sample_electric_car: ElectricCar) -> list[Vehicle]:
    car_bmw = Car(
        id=3,
        brand="BMW",
        model="M3",
        year=2022,
        price=75000.0,
        mileage=12000,
    )
    car_honda = Car(
        id=4,
        brand="Honda",
        model="Civic",
        year=2019,
        price=18500.0,
        mileage=65000,
    )
    car_audi = Car(
        id=5,
        brand="Audi",
        model="A6",
        year=2020,
        price=38000.0,
        mileage=50000,
    )
    return [sample_car, sample_electric_car, car_bmw, car_honda, car_audi]

@pytest.fixture
def car_factory() -> Callable[..., Car]:
    def _create_car(
        *,
        car_id: int = 10,
        brand: str = "Toyota",
        model: str = "Corolla",
        year: int = 2020,
        price: float = 20000.0,
        mileage: float = 30000.0,
    ) -> Car:
        return Car(
            id=car_id,
            brand=brand,
            model=model,
            year=year,
            price=price,
            mileage=mileage,
        )
    return _create_car

@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "cars_test_dataset.csv"
    content = (
        "vehicle_id,brand,model,year,price,mileage\n"
        "101,Toyota,Camry,2021,26000.0,45000\n"
        "102,BMW,M3,2022,75000.0,12000\n"
        "103,Tesla,Model 3,2023,42000.0,15000\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path

@pytest.fixture
def sample_csv_with_errors(tmp_path: Path) -> Path:
    file_path = tmp_path / "cars_with_errors.csv"
    content = (
        "vehicle_id,brand,model,year,price,mileage\n"
        "201,Ford,Focus,2018,14000.0,70000\n"
        "202,,Civic,2020,19000.0,30000\n"
        "203,Audi,A4,invalid_year,22000.0,40000\n"
        "204,Porsche,911,2022,-5000.0,10000\n"
        "205,Volvo,XC90,2021,55000.0,25000\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path

@pytest.fixture
def sample_yaml_config(tmp_path: Path, sample_csv_file: Path) -> Path:
    config_file = tmp_path / "config_test.yaml"
    out_file = tmp_path / "output_test.json"
    err_file = tmp_path / "errors_test.csv"
    content = f"""
input:
  path: "{sample_csv_file.as_posix()}"
  format: "csv"

output:
  path: "{out_file.as_posix()}"
  format: "json"

processing:
  skip_invalid: true
  backup_existing: false
  error_csv_path: "{err_file.as_posix()}"
  filters:
    min_year: 2020
    max_year: 2025
    min_price: 20000.0
    max_price: 80000.0

logging:
  level: "INFO"
  path: "{tmp_path.as_posix()}/test_app.log"
  console: false
"""
    config_file.write_text(content, encoding="utf-8")
    return config_file

@pytest.fixture
def teardown_tracker() -> Generator[dict[str, Any], None, None]:
    tracker: dict[str, Any] = {"initialized": True, "cleaned_up": False}
    yield tracker
    tracker["cleaned_up"] = True

@pytest.fixture(autouse=True)
def clean_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_SKIP_INVALID", raising=False)
    monkeypatch.delenv("APP_LOG_LEVEL", raising=False)

@pytest.fixture
def db_engine() -> Generator[Any, None, None]:
    from car_catalog.database import Base, create_database_engine
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def db_session(db_engine: Any) -> Generator[Any, None, None]:
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session

@pytest.fixture
def populated_db_session(db_session: Any) -> Any:
    from car_catalog.db_models import CarEntity, Manufacturer
    toyota = Manufacturer(name="Toyota", country="Japan")
    bmw = Manufacturer(name="BMW", country="Germany")
    tesla = Manufacturer(name="Tesla", country="USA")
    db_session.add_all([toyota, bmw, tesla])
    db_session.commit()

    car1 = CarEntity(
        manufacturer_id=toyota.id,
        model="Camry",
        year=2021,
        price=26000.0,
        mileage=45000.0,
        vin="1HGCR2F83HA000001",
    )
    car2 = CarEntity(
        manufacturer_id=bmw.id,
        model="M3",
        year=2022,
        price=75000.0,
        mileage=12000.0,
        vin="1HGCR2F83HA000002",
    )
    car3 = CarEntity(
        manufacturer_id=tesla.id,
        model="Model 3",
        year=2023,
        price=42000.0,
        mileage=15000.0,
        vin="1HGCR2F83HA000003",
    )
    car4 = CarEntity(
        manufacturer_id=toyota.id,
        model="Corolla",
        year=2020,
        price=20000.0,
        mileage=35000.0,
        vin="1HGCR2F83HA000004",
    )
    db_session.add_all([car1, car2, car3, car4])
    db_session.commit()
    return db_session
