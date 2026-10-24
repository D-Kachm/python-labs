from typing import Any
from car_catalog.exceptions import RecordValidationError
from car_catalog.models import Car


def parse_car_record(
    row: dict[str, Any],
    *,
    line_number: int,
) -> Car:
    raw_id = row.get("vehicle_id") if "vehicle_id" in row else row.get("id")
    if raw_id is None:
        raise RecordValidationError(
            "Missing vehicle ID field",
            line_number=line_number,
            field="vehicle_id",
            raw_record=row,
        )
    try:
        vehicle_id = int(raw_id)
    except (TypeError, ValueError) as error:
        raise RecordValidationError(
            f"Invalid vehicle ID format '{raw_id}'",
            line_number=line_number,
            field="vehicle_id",
            raw_record=row,
        ) from error

    if vehicle_id <= 0:
        raise RecordValidationError(
            f"Vehicle ID must be positive, got {vehicle_id}",
            line_number=line_number,
            field="vehicle_id",
            raw_record=row,
        )

    raw_brand = row.get("brand")
    brand = str(raw_brand).strip() if raw_brand is not None else ""
    if not brand:
        raise RecordValidationError(
            "Brand cannot be empty",
            line_number=line_number,
            field="brand",
            raw_record=row,
        )

    raw_model = row.get("model")
    model = str(raw_model).strip() if raw_model is not None else ""
    if not model:
        raise RecordValidationError(
            "Model cannot be empty",
            line_number=line_number,
            field="model",
            raw_record=row,
        )

    raw_year = row.get("year")
    if raw_year is None:
        raise RecordValidationError(
            "Missing manufacturing year",
            line_number=line_number,
            field="year",
            raw_record=row,
        )
    try:
        year = int(raw_year)
    except (TypeError, ValueError) as error:
        raise RecordValidationError(
            f"Invalid year format '{raw_year}'",
            line_number=line_number,
            field="year",
            raw_record=row,
        ) from error

    if not (1886 <= year <= 2026):
        raise RecordValidationError(
            f"Year must be between 1886 and 2026, got {year}",
            line_number=line_number,
            field="year",
            raw_record=row,
        )

    raw_price = row.get("price")
    if raw_price is None:
        raise RecordValidationError(
            "Missing vehicle price",
            line_number=line_number,
            field="price",
            raw_record=row,
        )
    try:
        price = float(raw_price)
    except (TypeError, ValueError) as error:
        raise RecordValidationError(
            f"Invalid price format '{raw_price}'",
            line_number=line_number,
            field="price",
            raw_record=row,
        ) from error

    if price < 0.0:
        raise RecordValidationError(
            f"Price cannot be negative, got {price}",
            line_number=line_number,
            field="price",
            raw_record=row,
        )

    raw_mileage = row.get("mileage")
    if raw_mileage is None:
        raise RecordValidationError(
            "Missing vehicle mileage",
            line_number=line_number,
            field="mileage",
            raw_record=row,
        )
    try:
        mileage = float(raw_mileage)
    except (TypeError, ValueError) as error:
        raise RecordValidationError(
            f"Invalid mileage format '{raw_mileage}'",
            line_number=line_number,
            field="mileage",
            raw_record=row,
        ) from error

    if mileage < 0.0:
        raise RecordValidationError(
            f"Mileage cannot be negative, got {mileage}",
            line_number=line_number,
            field="mileage",
            raw_record=row,
        )

    return Car(
        id=vehicle_id,
        brand=brand,
        model=model,
        year=year,
        price=price,
        mileage=mileage,
    )
