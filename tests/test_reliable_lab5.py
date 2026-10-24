import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from car_catalog.config import (
    AppConfig,
    FilterConfig,
    InputConfig,
    LoggingConfig,
    OutputConfig,
    ProcessingConfig,
    load_config,
    validate_config,
)
from car_catalog.exceptions import (
    ApplicationError,
    ConfigurationError,
    DataError,
    DataExportError,
    DataImportError,
    RecordValidationError,
    StorageError,
)
from car_catalog.exporters import (
    CsvExporter,
    JsonExporter,
    JsonlExporter,
    YamlExporter,
    JsonImporter,
    export_cars_csv,
    export_cars_json,
    export_cars_jsonl,
    export_cars_yaml,
    export_invalid_records_csv,
    get_exporter,
    get_importer,
)
from car_catalog.models import Car
from car_catalog.readers import (
    read_csv_rows,
    read_file_rows,
    read_json_rows,
    read_jsonl_rows,
    read_yaml_rows,
)
from car_catalog.services import (
    ImportStatistics,
    filter_imported_cars,
    import_cars,
    run_import_export_pipeline,
)
from car_catalog.utils import atomic_file_writer, logged_operation, timer
from car_catalog.validators import parse_car_record

class TestExceptionHierarchy(unittest.TestCase):
    def test_inheritance(self) -> None:
        self.assertTrue(issubclass(ConfigurationError, ApplicationError))
        self.assertTrue(issubclass(DataError, ApplicationError))
        self.assertTrue(issubclass(DataImportError, DataError))
        self.assertTrue(issubclass(RecordValidationError, DataError))
        self.assertTrue(issubclass(DataExportError, DataError))
        self.assertTrue(issubclass(StorageError, ApplicationError))

    def test_record_validation_error_attributes(self) -> None:
        err = RecordValidationError("Bad price", line_number=12, field="price", raw_record={"id": "1"})
        self.assertEqual(err.line_number, 12)
        self.assertEqual(err.field, "price")
        self.assertEqual(err.raw_record, {"id": "1"})
        self.assertEqual(str(err), "Bad price")

class TestRecordValidation(unittest.TestCase):
    def test_valid_record_with_vehicle_id(self) -> None:
        row = {"vehicle_id": "10", "brand": "Audi", "model": "A6", "year": "2021", "price": "35000.0", "mileage": "45000.0"}
        car = parse_car_record(row, line_number=2)
        self.assertEqual(car.id, 10)
        self.assertEqual(car.brand, "Audi")
        self.assertEqual(car.model, "A6")
        self.assertEqual(car.year, 2021)
        self.assertEqual(car.price, 35000.0)
        self.assertEqual(car.mileage, 45000.0)

    def test_valid_record_with_id_fallback(self) -> None:
        row = {"id": "5", "brand": "BMW", "model": "X5", "year": "2019", "price": "42000.0", "mileage": "60000.0"}
        car = parse_car_record(row, line_number=3)
        self.assertEqual(car.id, 5)

    def test_invalid_vehicle_id(self) -> None:
        row = {"vehicle_id": "xyz", "brand": "BMW", "model": "X5", "year": "2019", "price": "42000.0", "mileage": "60000.0"}
        with self.assertRaises(RecordValidationError) as ctx:
            parse_car_record(row, line_number=4)
        self.assertEqual(ctx.exception.field, "vehicle_id")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)

    def test_negative_vehicle_id(self) -> None:
        row = {"vehicle_id": "-5", "brand": "BMW", "model": "X5", "year": "2019", "price": "42000.0", "mileage": "60000.0"}
        with self.assertRaises(RecordValidationError) as ctx:
            parse_car_record(row, line_number=5)
        self.assertEqual(ctx.exception.field, "vehicle_id")

    def test_empty_brand_and_model(self) -> None:
        row1 = {"vehicle_id": "1", "brand": "   ", "model": "Focus", "year": "2018", "price": "10000.0", "mileage": "90000.0"}
        with self.assertRaises(RecordValidationError) as ctx1:
            parse_car_record(row1, line_number=6)
        self.assertEqual(ctx1.exception.field, "brand")

        row2 = {"vehicle_id": "1", "brand": "Ford", "model": "", "year": "2018", "price": "10000.0", "mileage": "90000.0"}
        with self.assertRaises(RecordValidationError) as ctx2:
            parse_car_record(row2, line_number=7)
        self.assertEqual(ctx2.exception.field, "model")

    def test_year_validation_and_chaining(self) -> None:
        row = {"vehicle_id": "1", "brand": "Ford", "model": "Focus", "year": "bad_year", "price": "10000.0", "mileage": "90000.0"}
        with self.assertRaises(RecordValidationError) as ctx:
            parse_car_record(row, line_number=8)
        self.assertEqual(ctx.exception.field, "year")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)

        row_range = {"vehicle_id": "1", "brand": "Ford", "model": "Focus", "year": "1800", "price": "10000.0", "mileage": "90000.0"}
        with self.assertRaises(RecordValidationError) as ctx_range:
            parse_car_record(row_range, line_number=9)
        self.assertEqual(ctx_range.exception.field, "year")

    def test_negative_price_and_mileage(self) -> None:
        row_price = {"vehicle_id": "1", "brand": "Ford", "model": "Focus", "year": "2018", "price": "-500.0", "mileage": "90000.0"}
        with self.assertRaises(RecordValidationError) as ctx:
            parse_car_record(row_price, line_number=10)
        self.assertEqual(ctx.exception.field, "price")

        row_mil = {"vehicle_id": "1", "brand": "Ford", "model": "Focus", "year": "2018", "price": "5000.0", "mileage": "-10.0"}
        with self.assertRaises(RecordValidationError) as ctx_mil:
            parse_car_record(row_mil, line_number=11)
        self.assertEqual(ctx_mil.exception.field, "mileage")

class TestConfigManagement(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.sample_csv = self.base_path / "test_cars.csv"
        self.sample_csv.write_text("vehicle_id,brand,model,year,price,mileage\n1,Audi,A4,2018,20000.0,50000.0\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_and_validate_valid_config(self) -> None:
        cfg_file = self.base_path / "config.yaml"
        cfg_content = f"""
input:
  path: {self.sample_csv}
  format: csv
output:
  path: {self.base_path / "out.json"}
  format: json
processing:
  skip_invalid: true
  filters:
    min_year: 2010
    max_year: 2024
    min_price: 1000.0
    max_price: 50000.0
logging:
  level: DEBUG
  path: {self.base_path / "test.log"}
"""
        cfg_file.write_text(cfg_content, encoding="utf-8")
        config = load_config(cfg_file)
        self.assertEqual(config.input.path, self.sample_csv)
        self.assertEqual(config.processing.filters.min_year, 2010)
        self.assertTrue(config.processing.skip_invalid)
        self.assertEqual(config.logging.level, "DEBUG")

    def test_missing_config_file(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_config(self.base_path / "non_existing.yaml")

    def test_invalid_yaml(self) -> None:
        bad_yaml = self.base_path / "bad.yaml"
        bad_yaml.write_text("input:\n  path: [unclosed", encoding="utf-8")
        with self.assertRaises(ConfigurationError):
            load_config(bad_yaml)

    def test_missing_input_file_validation(self) -> None:
        cfg = AppConfig(
            input=InputConfig(path=self.base_path / "missing.csv", format="csv"),
            output=OutputConfig(path=self.base_path / "out.json", format="json"),
            processing=ProcessingConfig(),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ConfigurationError):
            validate_config(cfg)

    def test_env_override(self) -> None:
        cfg_file = self.base_path / "cfg.yaml"
        cfg_file.write_text(f"input:\n  path: {self.sample_csv}\n", encoding="utf-8")
        os.environ["APP_LOG_LEVEL"] = "WARNING"
        os.environ["APP_SKIP_INVALID"] = "false"
        try:
            cfg = load_config(cfg_file)
            self.assertEqual(cfg.logging.level, "WARNING")
            self.assertFalse(cfg.processing.skip_invalid)
        finally:
            del os.environ["APP_LOG_LEVEL"]
            del os.environ["APP_SKIP_INVALID"]

class TestContextManagers(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_logged_operation_normal_and_exception(self) -> None:
        with logged_operation("Normal Op"):
            val = 42
        self.assertEqual(val, 42)

        with self.assertRaises(ZeroDivisionError):
            with logged_operation("Failing Op"):
                _ = 1 / 0

    def test_timer(self) -> None:
        with timer("benchmark") as t:
            total = sum(i for i in range(1000))
        self.assertGreater(t["elapsed"], 0.0)
        self.assertEqual(total, 499500)

    def test_atomic_file_writer_success(self) -> None:
        target = self.base_path / "atomic_test.txt"
        with atomic_file_writer(target) as f:
            f.write("test content")
        self.assertTrue(target.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "test content")
        self.assertFalse(target.with_suffix(".txt.tmp").exists())

    def test_atomic_file_writer_failure_preserves_target(self) -> None:
        target = self.base_path / "preserved.txt"
        target.write_text("initial valid data", encoding="utf-8")

        with self.assertRaises(DataExportError):
            with atomic_file_writer(target) as f:
                f.write("corrupted data")
                raise ValueError("Crash during write")

        self.assertEqual(target.read_text(encoding="utf-8"), "initial valid data")
        self.assertFalse(target.with_suffix(".txt.tmp").exists())

class TestStreamingReadersAndExporters(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.cars = [
            Car(1, "Audi", "A4", 2018, 22000.0, 60000.0),
            Car(2, "BMW", "320i", 2020, 31000.0, 40000.0),
        ]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_json_export_and_read(self) -> None:
        json_path = self.base_path / "cars.json"
        exported = export_cars_json(self.cars, json_path)
        self.assertEqual(exported, 2)
        rows = list(read_json_rows(json_path))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1]["brand"], "Audi")

    def test_jsonl_export_and_read(self) -> None:
        jsonl_path = self.base_path / "cars.jsonl"
        exported = export_cars_jsonl(self.cars, jsonl_path)
        self.assertEqual(exported, 2)
        rows = list(read_jsonl_rows(jsonl_path))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1]["brand"], "BMW")

    def test_csv_export_and_read(self) -> None:
        csv_path = self.base_path / "cars.csv"
        exported = export_cars_csv(self.cars, csv_path)
        self.assertEqual(exported, 2)
        rows = list(read_csv_rows(csv_path))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1]["brand"], "Audi")

    def test_yaml_export_and_read(self) -> None:
        yaml_path = self.base_path / "cars.yaml"
        exported = export_cars_yaml(self.cars, yaml_path)
        self.assertEqual(exported, 2)
        rows = list(read_yaml_rows(yaml_path))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1]["brand"], "Audi")

    def test_protocols_and_factories(self) -> None:
        importer = get_importer("json")
        exporter = get_exporter("json")
        self.assertIsInstance(importer, JsonImporter)
        self.assertIsInstance(exporter, JsonExporter)

class TestPipelinesAndModes(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.csv_path = self.base_path / "mixed.csv"
        content = """vehicle_id,brand,model,year,price,mileage
1,Audi,A4,2018,22000.0,60000.0
2,,ModelX,2020,30000.0,40000.0
3,Toyota,Corolla,2015,12000.0,110000.0
"""
        self.csv_path.write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_tolerant_mode_skips_invalid(self) -> None:
        stats = ImportStatistics()
        errors: list[dict[str, Any]] = []
        cars = list(import_cars(self.csv_path, skip_invalid=True, statistics=stats, error_sink=errors))
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.valid, 2)
        self.assertEqual(stats.invalid, 1)
        self.assertEqual(len(cars), 2)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["line_number"], 3)
        self.assertEqual(errors[0]["field"], "brand")

    def test_strict_mode_aborts_immediately(self) -> None:
        stats = ImportStatistics()
        with self.assertRaises(RecordValidationError) as ctx:
            list(import_cars(self.csv_path, skip_invalid=False, statistics=stats))
        self.assertEqual(ctx.exception.line_number, 3)
        self.assertEqual(stats.total, 2)
        self.assertEqual(stats.valid, 1)
        self.assertEqual(stats.invalid, 1)

    def test_filter_imported_cars(self) -> None:
        cars = [
            Car(1, "Audi", "A4", 2018, 22000.0, 60000.0),
            Car(2, "BMW", "320i", 1995, 3000.0, 250000.0),
            Car(3, "Tesla", "Model 3", 2022, 45000.0, 30000.0),
        ]
        filters = FilterConfig(min_year=2000, max_year=2026, min_price=10000.0, max_price=50000.0)
        filtered = list(filter_imported_cars(cars, filters))
        self.assertEqual(len(filtered), 2)
        self.assertEqual([c.id for c in filtered], [1, 3])

    def test_full_pipeline_with_backup_and_error_csv(self) -> None:
        out_json = self.base_path / "out.json"
        out_json.write_text("[]", encoding="utf-8")
        err_csv = self.base_path / "errors.csv"

        cfg = AppConfig(
            input=InputConfig(path=self.csv_path, format="csv"),
            output=OutputConfig(path=out_json, format="json"),
            processing=ProcessingConfig(
                skip_invalid=True,
                backup_existing=True,
                error_csv_path=err_csv,
                filters=FilterConfig(min_year=2000, max_year=2026, min_price=0.0, max_price=100000.0),
            ),
            logging=LoggingConfig(level="INFO", path=self.base_path / "app.log", console=False),
        )

        stats = run_import_export_pipeline(cfg)
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.valid, 2)
        self.assertEqual(stats.invalid, 1)
        self.assertEqual(stats.exported, 2)

        backup_file = out_json.with_suffix(".json.bak")
        self.assertTrue(backup_file.exists())
        self.assertTrue(err_csv.exists())
        self.assertTrue(out_json.exists())
