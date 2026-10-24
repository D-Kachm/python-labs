import csv
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Protocol
import yaml
from car_catalog.exceptions import DataExportError
from car_catalog.models import Car
from car_catalog.readers import read_csv_rows, read_json_rows, read_jsonl_rows, read_yaml_rows


class Importer(Protocol):
    def read(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]: ...


class Exporter(Protocol):
    def export(self, cars: Iterable[Car], path: Path) -> int: ...


class CsvImporter:
    def read(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        return read_csv_rows(path)


class JsonImporter:
    def read(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        return read_json_rows(path)


class JsonlImporter:
    def read(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        return read_jsonl_rows(path)


class YamlImporter:
    def read(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        return read_yaml_rows(path)


def export_cars_json(cars: Iterable[Car], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8") as file:
            file.write("[\n")
            first = True
            for car in cars:
                if not first:
                    file.write(",\n")
                payload = {
                    "vehicle_id": car.id,
                    "brand": car.brand,
                    "model": car.model,
                    "year": car.year,
                    "price": car.price,
                    "mileage": car.mileage,
                }
                file.write("  " + json.dumps(payload, ensure_ascii=False))
                first = False
                count += 1
            file.write("\n]\n")
        temporary.replace(path)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export data to {path}") from error
    return count


def export_cars_jsonl(cars: Iterable[Car], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8") as file:
            for car in cars:
                payload = {
                    "vehicle_id": car.id,
                    "brand": car.brand,
                    "model": car.model,
                    "year": car.year,
                    "price": car.price,
                    "mileage": car.mileage,
                }
                file.write(json.dumps(payload, ensure_ascii=False) + "\n")
                count += 1
        temporary.replace(path)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export data to {path}") from error
    return count


def export_cars_csv(cars: Iterable[Car], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["vehicle_id", "brand", "model", "year", "price", "mileage"])
            for car in cars:
                writer.writerow(
                    [
                        car.id,
                        car.brand,
                        car.model,
                        car.year,
                        f"{car.price:.2f}",
                        f"{car.mileage:.1f}",
                    ]
                )
                count += 1
        temporary.replace(path)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export data to {path}") from error
    return count


def export_cars_yaml(cars: Iterable[Car], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    records: list[dict[str, Any]] = []
    try:
        for car in cars:
            records.append(
                {
                    "vehicle_id": car.id,
                    "brand": car.brand,
                    "model": car.model,
                    "year": car.year,
                    "price": car.price,
                    "mileage": car.mileage,
                }
            )
            count += 1
        with temporary.open("w", encoding="utf-8") as file:
            yaml.safe_dump(records, file, allow_unicode=True, sort_keys=False)
        temporary.replace(path)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export data to {path}") from error
    return count


def export_invalid_records_csv(records: Iterable[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["line_number", "field", "message", "raw_data"])
            for rec in records:
                writer.writerow(
                    [
                        rec.get("line_number", ""),
                        rec.get("field", ""),
                        rec.get("message", ""),
                        str(rec.get("raw_data", "")),
                    ]
                )
                count += 1
        temporary.replace(path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot export invalid records to {path}") from error
    return count


class JsonExporter:
    def export(self, cars: Iterable[Car], path: Path) -> int:
        return export_cars_json(cars, path)


class JsonlExporter:
    def export(self, cars: Iterable[Car], path: Path) -> int:
        return export_cars_jsonl(cars, path)


class CsvExporter:
    def export(self, cars: Iterable[Car], path: Path) -> int:
        return export_cars_csv(cars, path)


class YamlExporter:
    def export(self, cars: Iterable[Car], path: Path) -> int:
        return export_cars_yaml(cars, path)


def get_importer(format_name: str) -> Importer:
    fmt = format_name.lower().lstrip(".")
    if fmt == "csv":
        return CsvImporter()
    if fmt == "json":
        return JsonImporter()
    if fmt == "jsonl":
        return JsonlImporter()
    if fmt in {"yaml", "yml"}:
        return YamlImporter()
    raise DataExportError(f"Unsupported importer format: {format_name}")


def get_exporter(format_name: str) -> Exporter:
    fmt = format_name.lower().lstrip(".")
    if fmt == "json":
        return JsonExporter()
    if fmt == "jsonl":
        return JsonlExporter()
    if fmt == "csv":
        return CsvExporter()
    if fmt in {"yaml", "yml"}:
        return YamlExporter()
    raise DataExportError(f"Unsupported exporter format: {format_name}")
