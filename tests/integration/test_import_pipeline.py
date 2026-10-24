from pathlib import Path
from typing import Any
import pytest
from car_catalog.exceptions import RecordValidationError
from car_catalog.services import ImportStatistics, import_cars

@pytest.mark.integration
def test_streaming_import_tolerant_mode(sample_csv_with_errors: Path) -> None:
    stats = ImportStatistics()
    error_sink: list[dict[str, Any]] = []

    cars = list(
        import_cars(
            sample_csv_with_errors,
            skip_invalid=True,
            statistics=stats,
            error_sink=error_sink,
        )
    )

    assert len(cars) == 2
    assert stats.total == 5
    assert stats.valid == 2
    assert stats.invalid == 3
    assert len(error_sink) == 3

    brands = [car.brand for car in cars]
    assert brands == ["Ford", "Volvo"]

@pytest.mark.integration
def test_streaming_import_strict_mode_aborts(sample_csv_with_errors: Path) -> None:
    stats = ImportStatistics()

    with pytest.raises(RecordValidationError) as exc_info:
        for _ in import_cars(sample_csv_with_errors, skip_invalid=False, statistics=stats):
            pass

    assert exc_info.value.field == "brand"
    assert stats.total == 2
    assert stats.valid == 1
    assert stats.invalid == 1
