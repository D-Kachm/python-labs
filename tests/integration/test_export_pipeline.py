import json
from pathlib import Path
import pytest
from car_catalog.config import FilterConfig
from car_catalog.exporters import JsonExporter
from car_catalog.services import ImportStatistics, filter_imported_cars, import_cars

@pytest.mark.integration
def test_filter_and_export_pipeline_end_to_end(sample_csv_file: Path, tmp_path: Path) -> None:
    output_file = tmp_path / "filtered_cars.json"
    stats = ImportStatistics()
    cars_stream = import_cars(sample_csv_file, skip_invalid=False, statistics=stats)

    filter_criteria = FilterConfig(
        min_year=2022,
        max_year=2024,
        min_price=30000.0,
        max_price=80000.0,
    )

    filtered_cars = list(filter_imported_cars(cars_stream, filter_criteria))
    assert len(filtered_cars) == 2

    exporter = JsonExporter()
    exported_count = exporter.export(filtered_cars, output_file)

    assert exported_count == 2
    assert output_file.exists()

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    models = {car_dict["model"] for car_dict in data}
    assert models == {"M3", "Model 3"}
