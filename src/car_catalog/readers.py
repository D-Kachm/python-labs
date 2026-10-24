import csv
import json
from collections.abc import Iterator
from itertools import chain, count
from pathlib import Path
from typing import Any
import yaml
from car_catalog.exceptions import DataImportError
from car_catalog.models import Car

def read_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as file:
        yield from file

def read_multiple_files(*paths: Path) -> Iterator[str]:
    file_streams = (read_lines(p) for p in paths)
    yield from chain.from_iterable(file_streams)

def infinite_car_stream(start_id: int = 1) -> Iterator[Car]:
    brands_models = [
        ("Audi", "A6"),
        ("Toyota", "Camry"),
        ("BMW", "X5"),
        ("Ford", "Focus"),
        ("Mercedes-Benz", "E-Class"),
        ("Volkswagen", "Passat"),
        ("Honda", "Civic"),
        ("Skoda", "Octavia"),
    ]
    num_models = len(brands_models)
    for idx in count(start_id):
        brand, model = brands_models[idx % num_models]
        year = 2000 + (idx % 25)
        price = 3000.0 + float((idx * 37) % 80000)
        mileage = 5000.0 + float((idx * 123) % 400000)
        yield Car(
            id=idx,
            brand=brand,
            model=f"{model}-{idx}",
            year=year,
            price=price,
            mileage=mileage,
        )

def read_csv_rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for line_number, row in enumerate(reader, start=2):
                yield line_number, dict(row)
    except OSError as error:
        raise DataImportError(f"Cannot read input file: {path}") from error

def read_json_rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise DataImportError(f"Invalid JSON document in {path}") from error
    except OSError as error:
        raise DataImportError(f"Cannot read input file: {path}") from error

    if not isinstance(data, list):
        raise DataImportError(f"Expected top-level JSON list in {path}, got {type(data).__name__}")

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise DataImportError(f"JSON record at index {idx} is not an object")
        yield idx, item

def read_jsonl_rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    record = json.loads(clean_line)
                except json.JSONDecodeError as error:
                    raise DataImportError(f"Invalid JSON at line {line_number}") from error
                if not isinstance(record, dict):
                    raise DataImportError(f"JSON record at line {line_number} is not an object")
                yield line_number, record
    except OSError as error:
        raise DataImportError(f"Cannot read input file: {path}") from error

def read_yaml_rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise DataImportError(f"Invalid YAML document in {path}") from error
    except OSError as error:
        raise DataImportError(f"Cannot read input file: {path}") from error

    if not isinstance(data, list):
        raise DataImportError(f"Expected top-level YAML list in {path}, got {type(data).__name__}")

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise DataImportError(f"YAML record at index {idx} is not an object")
        yield idx, item

def read_file_rows(path: Path, file_format: str | None = None) -> Iterator[tuple[int, dict[str, Any]]]:
    fmt = (file_format or path.suffix.lstrip(".").lower()).lower()
    if fmt == "csv":
        yield from read_csv_rows(path)
    elif fmt == "json":
        yield from read_json_rows(path)
    elif fmt == "jsonl":
        yield from read_jsonl_rows(path)
    elif fmt in {"yaml", "yml"}:
        yield from read_yaml_rows(path)
    else:
        raise DataImportError(f"Unsupported input format: {fmt}")
