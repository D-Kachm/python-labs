from collections.abc import Callable
from typing import Any
import pytest
from car_catalog.abstractions import NoDiscount, PercentageDiscount, ThresholdDiscount
from car_catalog.criteria import BrandCriteria
from car_catalog.models import Car, ElectricCar, Vehicle, VehicleCatalog
from car_catalog.value_objects import Mileage, Money, VIN


@pytest.mark.unit
def test_car_creation_and_attributes(sample_car: Car) -> None:
    assert sample_car.id == 1
    assert sample_car.brand == "Toyota"
    assert sample_car.model == "Camry"
    assert sample_car.year == 2021
    assert sample_car.price == pytest.approx(26000.0)
    assert sample_car.mileage == pytest.approx(45000.0)
    assert sample_car.full_name == "Toyota Camry"
    assert sample_car.age == 2026 - 2021
    assert sample_car.to_tuple() == (1, "Toyota", "Camry", 2021, 26000.0, 45000.0)
    assert sample_car.to_csv_row() == ["1", "Toyota", "Camry", "2021", "26000.00", "45000.0"]


@pytest.mark.unit
def test_car_setters_and_validation(sample_car: Car) -> None:
    sample_car.price = 27000.0
    assert sample_car.price == pytest.approx(27000.0)
    with pytest.raises(ValueError, match="Price cannot be negative"):
        sample_car.price = -10.0

    sample_car.mileage = 46000.0
    assert sample_car.mileage == pytest.approx(46000.0)
    with pytest.raises(ValueError, match="Mileage cannot be negative"):
        sample_car.mileage = -5.0

    sample_car.price = 26000.0
    sample_car.mileage = 45000.0


@pytest.mark.unit
def test_electric_car_creation_and_specifics(sample_electric_car: ElectricCar) -> None:
    assert sample_electric_car.id == 2
    assert sample_electric_car.battery_capacity == pytest.approx(75.0)
    assert sample_electric_car.range_km == pytest.approx(500.0)
    assert sample_electric_car.energy_consumption == pytest.approx(15.0)
    assert "⚡" in str(sample_electric_car)
    d = sample_electric_car.to_dict()
    assert d["battery_capacity"] == pytest.approx(75.0)
    assert d["range_km"] == pytest.approx(500.0)


@pytest.mark.unit
def test_electric_car_boundary_exceptions() -> None:
    with pytest.raises(ValueError, match="Battery capacity must be strictly positive"):
        ElectricCar(10, "Tesla", "Model S", 2022, 90000.0, 5000.0, 0.0, 400.0)
    with pytest.raises(ValueError, match="Range must be strictly positive"):
        ElectricCar(11, "Tesla", "Model S", 2022, 90000.0, 5000.0, 100.0, 0.0)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("year", "expected"),
    [
        pytest.param(1886, 1886, id="lower_boundary_first_car"),
        pytest.param(2000, 2000, id="normal_year_2000"),
        pytest.param(2026, 2026, id="upper_boundary_current_year"),
    ],
)
def test_car_valid_boundary_years(car_factory: Callable[..., Car], year: int, expected: int) -> None:
    car = car_factory(year=year)
    assert car.year == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_year",
    [
        pytest.param(1885, id="below_minimum_1886"),
        pytest.param(0, id="zero_year"),
        pytest.param(-2020, id="negative_year"),
    ],
)
def test_car_invalid_boundary_years(car_factory: Callable[..., Car], invalid_year: int) -> None:
    with pytest.raises(ValueError, match="Invalid manufacturing year"):
        car_factory(year=invalid_year)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("price", "expected"),
    [
        pytest.param(0.0, 0.0, id="zero_price_boundary"),
        pytest.param(0.01, 0.01, id="minimal_positive_price"),
        pytest.param(999999.99, 999999.99, id="high_price"),
    ],
)
def test_car_price_valid_boundary(car_factory: Callable[..., Car], price: float, expected: float) -> None:
    car = car_factory(price=price)
    assert car.price == pytest.approx(expected)


@pytest.mark.unit
def test_car_negative_price_raises_error(car_factory: Callable[..., Car]) -> None:
    with pytest.raises(ValueError, match="Price cannot be negative"):
        car_factory(price=-0.01)


@pytest.mark.unit
def test_car_negative_mileage_raises_error(car_factory: Callable[..., Car]) -> None:
    with pytest.raises(ValueError, match="Mileage cannot be negative"):
        car_factory(mileage=-1.0)


@pytest.mark.unit
def test_car_empty_brand_or_model_raises_error(car_factory: Callable[..., Car]) -> None:
    with pytest.raises(ValueError, match="Brand and model cannot be empty"):
        car_factory(brand="")
    with pytest.raises(ValueError, match="Brand and model cannot be empty"):
        car_factory(model="")


@pytest.mark.unit
def test_car_negative_or_zero_id_raises_error(car_factory: Callable[..., Car]) -> None:
    with pytest.raises(ValueError, match="ID must be positive"):
        car_factory(car_id=0)
    with pytest.raises(ValueError, match="ID must be positive"):
        car_factory(car_id=-5)


@pytest.mark.unit
def test_car_replace_immutability(sample_car: Car) -> None:
    updated = sample_car.replace(price=30000.0, mileage=50000.0)
    assert updated.id == sample_car.id
    assert updated.price == pytest.approx(30000.0)
    assert updated.mileage == pytest.approx(50000.0)
    assert sample_car.price == pytest.approx(26000.0)
    assert sample_car.mileage == pytest.approx(45000.0)


@pytest.mark.unit
def test_electric_car_replace(sample_electric_car: ElectricCar) -> None:
    updated = sample_electric_car.replace(battery_capacity=82.0, range_km=550.0)
    assert updated.battery_capacity == pytest.approx(82.0)
    assert updated.range_km == pytest.approx(550.0)
    assert sample_electric_car.battery_capacity == pytest.approx(75.0)


@pytest.mark.unit
def test_car_dunder_methods(sample_car: Car, car_factory: Callable[..., Car]) -> None:
    same_car = car_factory(car_id=1, brand="Toyota", model="Camry", year=2021, price=26000.0, mileage=45000.0)
    cheaper_car = car_factory(car_id=2, price=20000.0)

    assert sample_car == same_car
    assert cheaper_car < sample_car
    assert "Toyota" in repr(sample_car)
    assert "Camry" in str(sample_car)
    assert hash(sample_car) == hash(same_car)
    assert (sample_car == "not_a_car") is False
    not_car: Any = "not_a_car"
    assert sample_car.__lt__(not_car) is NotImplemented


@pytest.mark.unit
def test_vehicle_catalog_collection(sample_cars_list: list[Vehicle], sample_car: Car) -> None:
    catalog = VehicleCatalog(sample_cars_list)
    assert len(catalog) == 5
    assert catalog[0].id == 1
    assert 1 in catalog
    assert 999 not in catalog
    assert sample_car in catalog

    most_exp = catalog.most_expensive()
    assert most_exp is not None
    assert most_exp.brand == "BMW"

    lowest_mil = catalog.lowest_mileage()
    assert lowest_mil is not None
    assert lowest_mil.mileage == pytest.approx(12000.0)

    avg_p = catalog.average_price()
    assert avg_p > 0.0

    filtered = catalog.filter_by_year(2021)
    assert len(filtered) == 1

    searched = catalog.search(BrandCriteria("Toyota"))
    assert len(searched) == 1

    catalog.remove(1)
    assert len(catalog) == 4
    assert 1 not in catalog

    catalog.add(sample_car)
    assert len(catalog) == 5
    assert catalog.get(1) == sample_car

    combined = catalog + VehicleCatalog([sample_car])
    assert len(combined) == 6
    assert "VehicleCatalog" in repr(catalog)
    assert "5 vehicles" in str(catalog)

    empty_cat = VehicleCatalog([])
    assert empty_cat.most_expensive() is None
    assert empty_cat.lowest_mileage() is None
    assert empty_cat.average_price() == pytest.approx(0.0)


@pytest.mark.unit
def test_value_object_money() -> None:
    m1 = Money(100.50, "USD")
    m2 = Money(50.25, "USD")
    assert (m1 + m2).amount == pytest.approx(150.75)
    assert (m1 - m2).amount == pytest.approx(50.25)
    assert (m1 * 2.0).amount == pytest.approx(201.0)
    assert (m2 < m1) is True
    assert str(m1) == "100.50 USD"
    assert "100.5" in repr(m1)

    with pytest.raises(ValueError, match="Money amount cannot be negative"):
        Money(-1.0, "USD")
    with pytest.raises(ValueError, match="Multiplier cannot be negative"):
        _ = m1 * -1.0
    with pytest.raises(ValueError, match="Resulting money amount cannot be negative"):
        _ = m2 - m1
    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m1 + Money(50.0, "EUR")
    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m1 - Money(50.0, "EUR")
    with pytest.raises(ValueError, match="Currency mismatch"):
        _ = m1 < Money(50.0, "EUR")


@pytest.mark.unit
def test_value_object_mileage() -> None:
    m1 = Mileage(10000.0)
    m2 = Mileage(5000.0)
    assert (m1 + m2).value == pytest.approx(15000.0)
    assert (m2 < m1) is True
    assert str(m1) == "10000.0 km"
    assert "10000.0" in repr(m1)

    with pytest.raises(ValueError, match="Mileage cannot be negative"):
        Mileage(-10.0)
    with pytest.raises(ValueError, match="Mileage unit mismatch"):
        _ = m1 + Mileage(500.0, "miles")
    with pytest.raises(ValueError, match="Mileage unit mismatch"):
        _ = m1 < Mileage(500.0, "miles")


@pytest.mark.unit
def test_value_object_vin() -> None:
    valid_vin = "1HGCR2F83HA000000"
    v = VIN(valid_vin)
    assert v.code == valid_vin
    assert str(v) == valid_vin

    with pytest.raises(ValueError, match="Invalid VIN format"):
        VIN("AB")
    with pytest.raises(ValueError, match="Invalid VIN format"):
        VIN("VIN#WITH*SYMBOL")


@pytest.mark.unit
def test_discount_abstractions() -> None:
    no_disc = NoDiscount()
    price = Money(100.0, "USD")
    assert no_disc.apply(price) == price

    perc = PercentageDiscount(20.0)
    assert perc.percent == pytest.approx(20.0)
    assert perc.apply(price).amount == pytest.approx(80.0)

    with pytest.raises(ValueError, match="Discount percentage must be between"):
        PercentageDiscount(-1.0)
    with pytest.raises(ValueError, match="Discount percentage must be between"):
        PercentageDiscount(101.0)

    threshold = ThresholdDiscount(threshold=Money(500.0, "USD"), discount_amount=Money(50.0, "USD"))
    assert threshold.apply(Money(600.0, "USD")).amount == pytest.approx(550.0)
    assert threshold.apply(Money(400.0, "USD")).amount == pytest.approx(400.0)

    with pytest.raises(ValueError, match="Currencies of threshold and discount must match"):
        ThresholdDiscount(threshold=Money(500.0, "USD"), discount_amount=Money(50.0, "EUR"))

    with pytest.raises(ValueError, match="Currency mismatch in discount application"):
        threshold.apply(Money(600.0, "EUR"))
