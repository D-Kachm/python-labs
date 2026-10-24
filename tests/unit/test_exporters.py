import json
from pathlib import Path
import pytest
from car_catalog.exceptions import DataExportError
from car_catalog.exporters import (
    CsvExporter,
    JsonExporter,
    JsonlExporter,
    YamlExporter,
    export_invalid_records_csv,
    get_exporter,
)
from car_catalog.models import Car, Vehicle
from car_catalog.utils import atomic_file_writer

@pytest.mark.unit
def test_get_exporter_factory() -> None:
    assert isinstance(get_exporter("json"), JsonExporter)
    assert isinstance(get_exporter("jsonl"), JsonlExporter)
    assert isinstance(get_exporter("csv"), CsvExporter)
    assert isinstance(get_exporter("yaml"), YamlExporter)

    with pytest.raises(DataExportError, match="Unsupported exporter format"):
        get_exporter("unsupported_format")

@pytest.mark.unit
def test_atomic_file_writer_success(tmp_path: Path) -> None:
    target_file = tmp_path / "atomic_success.txt"
    with atomic_file_writer(target_file) as file_handle:
        file_handle.write("Atomic content payload")

    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "Atomic content payload"

@pytest.mark.unit
def test_atomic_file_writer_preserves_original_on_failure(tmp_path: Path) -> None:
    target_file = tmp_path / "important_data.txt"
    target_file.write_text("Initial original data", encoding="utf-8")

    with pytest.raises(DataExportError, match="Cannot export data"):
        with atomic_file_writer(target_file) as file_handle:
            file_handle.write("Corrupted partial data")
            raise RuntimeError("Simulated crash during write")

    assert target_file.read_text(encoding="utf-8") == "Initial original data"
    temp_candidates = list(tmp_path.glob("*.tmp"))
    assert len(temp_candidates) == 0

@pytest.mark.unit
def test_json_exporter_output(tmp_path: Path, sample_cars_list: list[Vehicle]) -> None:
    out_file = tmp_path / "exported_cars.json"
    cars: list[Car] = [c for c in sample_cars_list if isinstance(c, Car)]
    exporter = JsonExporter()
    count = exporter.export(cars, out_file)

    assert count == len(cars)
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 5
    assert data[0]["brand"] == "Toyota"
    assert data[0]["price"] == pytest.approx(26000.0)

@pytest.mark.unit
def test_jsonl_exporter_output(tmp_path: Path, sample_cars_list: list[Vehicle]) -> None:
    out_file = tmp_path / "exported_cars.jsonl"
    cars: list[Car] = [c for c in sample_cars_list if isinstance(c, Car)]
    exporter = JsonlExporter()
    count = exporter.export(cars, out_file)

    assert count == len(cars)
    assert out_file.exists()

    lines = [line.strip() for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 5
    record = json.loads(lines[0])
    assert record["brand"] == "Toyota"

@pytest.mark.unit
def test_csv_exporter_output(tmp_path: Path, sample_cars_list: list[Vehicle]) -> None:
    out_file = tmp_path / "exported_cars.csv"
    cars: list[Car] = [c for c in sample_cars_list if isinstance(c, Car)]
    exporter = CsvExporter()
    count = exporter.export(cars, out_file)

    assert count == len(cars)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "vehicle_id,brand,model,year,price,mileage" in content
    assert "Toyota,Camry" in content

@pytest.mark.unit
def test_export_invalid_records_csv(tmp_path: Path) -> None:
    out_file = tmp_path / "invalid_records.csv"
    invalid_data = [
        {"line_number": 2, "field": "brand", "message": "Brand cannot be empty", "raw_data": {"model": "Civic"}}
    ]
    count = export_invalid_records_csv(invalid_data, out_file)
    assert count == 1
    assert out_file.exists()
    assert "Brand cannot be empty" in out_file.read_text(encoding="utf-8")
