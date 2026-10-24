import pytest
from car_catalog.exceptions import RecordValidationError
from car_catalog.validators import parse_car_record

@pytest.mark.unit
def test_parse_valid_car_record() -> None:
    record = {
        "vehicle_id": "1",
        "brand": "Toyota",
        "model": "Camry",
        "year": "2021",
        "price": "26000.0",
        "mileage": "45000",
    }
    car = parse_car_record(record, line_number=5)
    assert car.id == 1
    assert car.brand == "Toyota"
    assert car.model == "Camry"
    assert car.year == 2021
    assert car.price == pytest.approx(26000.0)
    assert car.mileage == pytest.approx(45000.0)

@pytest.mark.unit
def test_parse_valid_record_with_id_key() -> None:
    record = {
        "id": "99",
        "brand": "Honda",
        "model": "Civic",
        "year": "2020",
        "price": "18000",
        "mileage": "30000",
    }
    car = parse_car_record(record, line_number=2)
    assert car.id == 99
    assert car.brand == "Honda"

@pytest.mark.unit
@pytest.mark.parametrize(
    ("record_updates", "expected_field", "match_pattern"),
    [
        pytest.param({"brand": ""}, "brand", "Brand cannot be empty", id="empty_brand"),
        pytest.param({"brand": "   "}, "brand", "Brand cannot be empty", id="whitespace_brand"),
        pytest.param({"model": ""}, "model", "Model cannot be empty", id="empty_model"),
        pytest.param({"year": "not_a_number"}, "year", "Invalid year format", id="non_numeric_year"),
        pytest.param({"year": "1800"}, "year", "Year must be between", id="year_too_early"),
        pytest.param({"year": "2050"}, "year", "Year must be between", id="year_too_late"),
        pytest.param({"price": "-100.0"}, "price", "Price cannot be negative", id="negative_price"),
        pytest.param({"price": "abc"}, "price", "Invalid price format", id="non_numeric_price"),
        pytest.param({"mileage": "-5"}, "mileage", "Mileage cannot be negative", id="negative_mileage"),
        pytest.param({"mileage": "ten_k"}, "mileage", "Invalid mileage format", id="non_numeric_mileage"),
        pytest.param({"vehicle_id": "invalid_id"}, "vehicle_id", "Invalid vehicle ID format", id="non_numeric_id"),
        pytest.param({"vehicle_id": "-1"}, "vehicle_id", "Vehicle ID must be positive", id="negative_id"),
    ],
)
def test_parse_invalid_car_records(
    record_updates: dict[str, str],
    expected_field: str,
    match_pattern: str,
) -> None:
    base_record = {
        "vehicle_id": "1",
        "brand": "Toyota",
        "model": "Camry",
        "year": "2021",
        "price": "26000.0",
        "mileage": "45000",
    }
    base_record.update(record_updates)

    with pytest.raises(RecordValidationError, match=match_pattern) as exc_info:
        parse_car_record(base_record, line_number=42)

    assert exc_info.value.field == expected_field
    assert exc_info.value.line_number == 42

@pytest.mark.unit
def test_exception_chaining_on_invalid_numeric_conversion() -> None:
    record = {
        "vehicle_id": "1",
        "brand": "Toyota",
        "model": "Camry",
        "year": "invalid_numeric_year",
        "price": "26000.0",
        "mileage": "45000",
    }
    with pytest.raises(RecordValidationError) as exc_info:
        parse_car_record(record, line_number=10)

    assert exc_info.value.field == "year"
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)
