from pathlib import Path
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from car_catalog.database import create_database_engine, init_database
from car_catalog.db_models import CarEntity, Manufacturer
from car_catalog.models import Car
from car_catalog.repositories import (
    CarRepository,
    ManufacturerRepository,
    bulk_update_prices_by_manufacturer,
    find_cars_by_manufacturer_dbapi,
)


@pytest.mark.integration
def test_manufacturer_repository_crud(db_session: Session) -> None:
    repo = ManufacturerRepository(db_session)

    manufacturer = Manufacturer(name="Audi", country="Germany")
    saved = repo.add(manufacturer)
    assert saved.id is not None
    assert saved.name == "Audi"
    assert saved.country == "Germany"

    found_by_id = repo.get_by_id(saved.id)
    assert found_by_id is not None
    assert found_by_id.name == "Audi"

    found_by_name = repo.get_by_name("Audi")
    assert found_by_name is not None
    assert found_by_name.id == saved.id

    all_manufacturers = repo.get_all()
    assert len(all_manufacturers) == 1

    deleted = repo.delete(saved.id)
    assert deleted is True
    assert repo.get_by_id(saved.id) is None
    assert repo.delete(9999) is False


@pytest.mark.integration
def test_car_repository_crud(db_session: Session) -> None:
    m_repo = ManufacturerRepository(db_session)
    c_repo = CarRepository(db_session)

    m = m_repo.add(Manufacturer(name="Toyota", country="Japan"))
    car = CarEntity(
        manufacturer_id=m.id,
        model="RAV4",
        year=2022,
        price=32000.0,
        mileage=20000.0,
        vin="1HGCR2F83HA111111",
    )
    saved_car = c_repo.add(car)
    assert saved_car.id is not None
    assert saved_car.model == "RAV4"
    assert saved_car.price == pytest.approx(32000.0)

    loaded = c_repo.get_by_id(saved_car.id)
    assert loaded is not None
    assert loaded.model == "RAV4"
    assert loaded.vin == "1HGCR2F83HA111111"

    updated_price = c_repo.update_price(saved_car.id, 30000.0)
    assert updated_price is not None
    assert updated_price.price == pytest.approx(30000.0)

    updated_mileage = c_repo.update_mileage(saved_car.id, 25000.0)
    assert updated_mileage is not None
    assert updated_mileage.mileage == pytest.approx(25000.0)

    with pytest.raises(ValueError, match="Price cannot be negative"):
        c_repo.update_price(saved_car.id, -100.0)

    with pytest.raises(ValueError, match="Mileage cannot be negative"):
        c_repo.update_mileage(saved_car.id, -5.0)

    assert c_repo.update_price(9999, 1000.0) is None
    assert c_repo.update_mileage(9999, 1000.0) is None

    deleted = c_repo.delete(saved_car.id)
    assert deleted is True
    assert c_repo.get_by_id(saved_car.id) is None
    assert c_repo.delete(9999) is False


@pytest.mark.integration
def test_manufacturer_car_relationship_and_cascade(db_session: Session) -> None:
    m_repo = ManufacturerRepository(db_session)
    c_repo = CarRepository(db_session)

    bmw = m_repo.add(Manufacturer(name="BMW", country="Germany"))
    car1 = CarEntity(
        manufacturer_id=bmw.id,
        model="330i",
        year=2021,
        price=45000.0,
        mileage=30000.0,
    )
    car2 = CarEntity(
        manufacturer_id=bmw.id,
        model="M5",
        year=2023,
        price=105000.0,
        mileage=8000.0,
    )
    c_repo.add(car1)
    c_repo.add(car2)

    db_session.refresh(bmw)
    assert len(bmw.cars) == 2
    assert car1.manufacturer.name == "BMW"

    m_repo.delete(bmw.id)
    assert c_repo.get_by_id(car1.id) is None
    assert c_repo.get_by_id(car2.id) is None


@pytest.mark.integration
def test_car_repository_search_and_filters(populated_db_session: Session) -> None:
    repo = CarRepository(populated_db_session)

    camry = repo.find_by_model("Camry")
    assert len(camry) == 1
    assert camry[0].model == "Camry"

    by_year = repo.filter_by_year(2022)
    assert len(by_year) == 1
    assert by_year[0].model == "M3"

    by_year_range = repo.filter_by_year_range(2021, 2023)
    assert len(by_year_range) == 3


@pytest.mark.integration
def test_car_repository_aggregates(populated_db_session: Session) -> None:
    repo = CarRepository(populated_db_session)

    most_exp = repo.get_most_expensive()
    assert most_exp is not None
    assert most_exp.model == "M3"
    assert most_exp.price == pytest.approx(75000.0)

    lowest_mil = repo.get_lowest_mileage()
    assert lowest_mil is not None
    assert lowest_mil.model == "M3"
    assert lowest_mil.mileage == pytest.approx(12000.0)

    avg_p = repo.get_average_price()
    expected_avg = (26000.0 + 75000.0 + 42000.0 + 20000.0) / 4
    assert avg_p == pytest.approx(expected_avg)


@pytest.mark.integration
def test_manufacturer_grouped_statistics(populated_db_session: Session) -> None:
    repo = CarRepository(populated_db_session)
    stats = repo.get_manufacturer_statistics()
    assert len(stats) == 3

    toyota_stat = next(s for s in stats if s["manufacturer"] == "Toyota")
    assert toyota_stat["total_cars"] == 2
    assert toyota_stat["min_price"] == pytest.approx(20000.0)
    assert toyota_stat["max_price"] == pytest.approx(26000.0)
    assert toyota_stat["average_price"] == pytest.approx(23000.0)


@pytest.mark.integration
def test_unique_vin_constraint(db_session: Session) -> None:
    m_repo = ManufacturerRepository(db_session)
    c_repo = CarRepository(db_session)

    m = m_repo.add(Manufacturer(name="Honda", country="Japan"))
    c_repo.add(
        CarEntity(
            manufacturer_id=m.id,
            model="Civic",
            year=2020,
            price=20000.0,
            mileage=30000.0,
            vin="1HGCR2F83HA999999",
        )
    )

    duplicate_vin_car = CarEntity(
        manufacturer_id=m.id,
        model="Accord",
        year=2021,
        price=28000.0,
        mileage=15000.0,
        vin="1HGCR2F83HA999999",
    )
    with pytest.raises(IntegrityError):
        c_repo.add(duplicate_vin_car)

    db_session.rollback()


@pytest.mark.integration
def test_transaction_bulk_update_success(populated_db_session: Session) -> None:
    m_repo = ManufacturerRepository(populated_db_session)
    c_repo = CarRepository(populated_db_session)

    toyota = m_repo.get_by_name("Toyota")
    assert toyota is not None

    bulk_update_prices_by_manufacturer(
        populated_db_session,
        manufacturer_id=toyota.id,
        multiplier=1.10,
        max_price_limit=200000.0,
    )

    cars = c_repo.find_by_manufacturer_id(toyota.id)
    prices = {c.model: c.price for c in cars}
    assert prices["Camry"] == pytest.approx(28600.0)
    assert prices["Corolla"] == pytest.approx(22000.0)


@pytest.mark.integration
def test_transaction_bulk_update_rollback_on_failure(populated_db_session: Session) -> None:
    m_repo = ManufacturerRepository(populated_db_session)
    c_repo = CarRepository(populated_db_session)

    toyota = m_repo.get_by_name("Toyota")
    assert toyota is not None

    initial_cars = c_repo.find_by_manufacturer_id(toyota.id)
    initial_prices = {c.model: c.price for c in initial_cars}

    with pytest.raises(ValueError, match="exceeds maximum limit"):
        bulk_update_prices_by_manufacturer(
            populated_db_session,
            manufacturer_id=toyota.id,
            multiplier=10.0,
            max_price_limit=50000.0,
        )

    refreshed_cars = c_repo.find_by_manufacturer_id(toyota.id)
    for c in refreshed_cars:
        populated_db_session.refresh(c)
        assert c.price == pytest.approx(initial_prices[c.model])


@pytest.mark.integration
def test_dbapi_parameterized_search(tmp_path: Path) -> None:
    db_file = tmp_path / "dbapi_test.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    init_database(engine)

    from sqlalchemy.orm import sessionmaker

    SessionMaker = sessionmaker(bind=engine)
    with SessionMaker() as session:
        m_repo = ManufacturerRepository(session)
        c_repo = CarRepository(session)
        ford = m_repo.add(Manufacturer(name="Ford", country="USA"))
        c_repo.add(
            CarEntity(
                manufacturer_id=ford.id,
                model="Mustang",
                year=2021,
                price=40000.0,
                mileage=15000.0,
                vin="1FA6P8CF5H5111111",
            )
        )
        c_repo.add(
            CarEntity(
                manufacturer_id=ford.id,
                model="F-150",
                year=2022,
                price=55000.0,
                mileage=22000.0,
                vin="1FTFW1E84MF111112",
            )
        )

    results = find_cars_by_manufacturer_dbapi(db_file.as_posix(), "Ford")
    assert len(results) == 2
    assert results[0][1] == "Ford"
    assert results[0][2] == "Mustang"
    assert results[1][2] == "F-150"


@pytest.mark.integration
def test_domain_entity_conversion(populated_db_session: Session) -> None:
    c_repo = CarRepository(populated_db_session)
    cars = c_repo.get_all()
    assert len(cars) > 0

    entity = cars[0]
    domain_car = entity.to_domain()
    assert isinstance(domain_car, Car)
    assert domain_car.id == entity.id
    assert domain_car.model == entity.model
    assert domain_car.price == pytest.approx(entity.price)


@pytest.mark.integration
def test_session_scope_lifecycle(tmp_path: Path) -> None:
    from car_catalog.database import create_session_factory, drop_database, session_scope

    db_file = tmp_path / "scope_test.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    init_database(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        m_repo = ManufacturerRepository(session)
        m_repo.add(Manufacturer(name="Mazda", country="Japan"))

    with session_scope(session_factory) as session:
        m_repo = ManufacturerRepository(session)
        assert m_repo.get_by_name("Mazda") is not None

    with pytest.raises(RuntimeError, match="Simulated scope crash"):
        with session_scope(session_factory) as session:
            m_repo = ManufacturerRepository(session)
            session.add(Manufacturer(name="Nissan", country="Japan"))
            raise RuntimeError("Simulated scope crash")

    with session_scope(session_factory) as session:
        m_repo = ManufacturerRepository(session)
        assert m_repo.get_by_name("Nissan") is None

    drop_database(engine)
    engine.dispose()
