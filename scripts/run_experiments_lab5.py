import csv
import tempfile
import traceback
import tracemalloc
from pathlib import Path
from time import perf_counter
from typing import Any

from car_catalog.config import load_config
from car_catalog.exceptions import ConfigurationError, DataExportError, RecordValidationError
from car_catalog.exporters import export_cars_json
from car_catalog.models import Car
from car_catalog.services import ImportStatistics, import_cars
from car_catalog.validators import parse_car_record


def run_experiment_1() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 1: STRICT VS TOLERANT PROCESSING")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_file = Path(tmp_dir) / "exp1_cars.csv"
        with csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["vehicle_id", "brand", "model", "year", "price", "mileage"])
            for i in range(1, 1011):
                if i in {100, 200, 300, 400, 500, 600, 700, 800, 900, 1000}:
                    writer.writerow([f"err_{i}", "", "Corrupted", "bad_year", "-999", "-500"])
                else:
                    writer.writerow([i, "Toyota", f"Model-{i}", 2015 + (i % 8), 15000.0 + (i % 1000), 50000.0])

        strict_stats = ImportStatistics()
        strict_status = "Success"
        try:
            for _ in import_cars(csv_file, skip_invalid=False, statistics=strict_stats):
                pass
        except RecordValidationError as e:
            strict_status = f"Aborted ({type(e).__name__} at line {e.line_number})"

        tolerant_stats = ImportStatistics()
        tolerant_status = "Success"
        try:
            for _ in import_cars(csv_file, skip_invalid=True, statistics=tolerant_stats):
                pass
        except RecordValidationError as e:
            tolerant_status = f"Aborted ({type(e).__name__})"

        print(f"{'Параметр':<30} | {'Strict Mode':<22} | {'Tolerant Mode':<22}")
        print("-" * 80)
        print(f"{'Оброблено записів':<30} | {strict_stats.total:<22} | {tolerant_stats.total:<22}")
        print(f"{'Valid':<30} | {strict_stats.valid:<22} | {tolerant_stats.valid:<22}")
        print(f"{'Invalid':<30} | {strict_stats.invalid:<22} | {tolerant_stats.invalid:<22}")
        print(f"{'Exported / Passed':<30} | {strict_stats.valid:<22} | {tolerant_stats.valid:<22}")
        print(f"{'Завершення application':<30} | {strict_status:<22} | {tolerant_status:<22}")
        print("-" * 80)


def run_experiment_2() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 2: STREAMING VS EAGER FILE LOADING (RAM & EXECUTION TIME)")
    print("=" * 80)
    datasets = [
        (10_000, Path("data/cars_10000.csv")),
        (100_000, Path("data/cars_100000.csv")),
        (500_000, Path("data/cars_500000.csv")),
    ]

    print(
        f"{'Records':<10} | {'Eager time (s)':<15} | {'Streaming time (s)':<18} | {'Eager peak RAM (MB)':<20} | {'Streaming peak RAM (MB)':<22}"
    )
    print("-" * 95)

    for rec_count, path in datasets:
        if not path.exists():
            continue

        tracemalloc.start()
        t0 = perf_counter()
        with path.open("r", encoding="utf-8", newline="") as file:
            eager_rows = list(csv.DictReader(file))
        eager_time = perf_counter() - t0
        _, eager_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        eager_peak_mb = eager_peak / (1024 * 1024)
        del eager_rows

        tracemalloc.start()
        t0 = perf_counter()
        count = 0
        with path.open("r", encoding="utf-8", newline="") as file:
            for _ in csv.DictReader(file):
                count += 1
        streaming_time = perf_counter() - t0
        _, streaming_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        streaming_peak_mb = streaming_peak / (1024 * 1024)

        print(
            f"{rec_count:<10} | {eager_time:<15.4f} | {streaming_time:<18.4f} | {eager_peak_mb:<20.2f} | {streaming_peak_mb:<22.4f}"
        )
    print("-" * 95)


def run_experiment_3() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 3: EXCEPTION CHAINING (DIAGNOSTICS & TRACEBACK)")
    print("=" * 80)
    corrupted_row = {
        "vehicle_id": "1",
        "brand": "Audi",
        "model": "A4",
        "year": "2018",
        "price": "not_a_number",
        "mileage": "45000.0",
    }
    print(f"Вхідний запис: {corrupted_row}")
    try:
        parse_car_record(corrupted_row, line_number=15)
    except RecordValidationError as error:
        print("\nОтримано виняток RecordValidationError!")
        print(f"Повідомлення: {error}")
        print(f"Номер рядка:  {error.line_number}")
        print(f"Поле помилки: {error.field}")
        print(f"Chained cause (__cause__): {type(error.__cause__).__name__}: {error.__cause__}")
        print("\nФорматований ланцюжок викликів (Traceback):")
        traceback.print_exception(error)


def run_experiment_4() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 4: ATOMIC OUTPUT REPLACEMENT")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_path = Path(tmp_dir) / "cars_production.json"
        target_path.write_text('[{"initial_valid_car": true}]', encoding="utf-8")
        tmp_file = target_path.with_suffix(target_path.suffix + ".tmp")

        print(f"1. Початковий цільовий файл існує: {target_path.exists()}, розмір: {target_path.stat().st_size} байт")
        print(f"   Вміст: {target_path.read_text(encoding='utf-8')}")

        def faulty_generator() -> Any:
            yield Car(1, "Audi", "A4", 2020, 25000.0, 30000.0)
            raise RuntimeError("Fatal process crash during serialization!")

        print("\n2. Запуск експорту з імітацією аварійного збою посеред запису...")
        try:
            export_cars_json(faulty_generator(), target_path)
        except DataExportError as e:
            print(f"   Перехоплено контрольований виняток: {type(e).__name__}: {e}")
            print(f"   Оригінальна причина: {type(e.__cause__).__name__}: {e.__cause__}")

        print("\n3. Перевірка цілісності після збою:")
        print(
            f"   - Цільовий файл не пошкоджено: {target_path.exists()} (вміст: '{target_path.read_text(encoding='utf-8')}')"
        )
        print(f"   - Тимчасовий файл {tmp_file.name} очищено (видалено): {not tmp_file.exists()}")


def run_experiment_5() -> None:
    print("\n" + "=" * 80)
    print("ЕКСПЕРИМЕНТ 5: CONFIGURATION ERRORS & FAIL-FAST VALIDATION")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        cases = [
            ("1. Відсутній файл конфігурації", base / "non_existing.yaml"),
            ("2. Синтаксична помилка YAML", base / "invalid_syntax.yaml"),
            ("3. Відсутній ключ 'input'", base / "missing_input.yaml"),
            ("4. Некоректні межі фільтра (min_price > max_price)", base / "invalid_bounds.yaml"),
            ("5. Вхідний файл даних не існує", base / "missing_data_file.yaml"),
        ]

        (base / "invalid_syntax.yaml").write_text("input:\n  path: [unclosed\n", encoding="utf-8")
        (base / "missing_input.yaml").write_text("output:\n  path: out.json\n", encoding="utf-8")

        valid_csv = base / "valid.csv"
        valid_csv.write_text(
            "vehicle_id,brand,model,year,price,mileage\n1,Audi,A4,2020,20000,50000\n", encoding="utf-8"
        )

        (base / "invalid_bounds.yaml").write_text(
            f"""
input:
  path: {valid_csv}
processing:
  filters:
    min_price: 50000.0
    max_price: 10000.0
""",
            encoding="utf-8",
        )

        (base / "missing_data_file.yaml").write_text(
            f"""
input:
  path: {base / "non_existing_data.csv"}
""",
            encoding="utf-8",
        )

        for title, path in cases:
            print(f"\nТест: {title}")
            try:
                load_config(path)
                print("   Помилка: конфігурація пройшла перевірку несподівано!")
            except ConfigurationError as exc:
                print(f"   Успішно перехоплено ConfigurationError: {exc}")


if __name__ == "__main__":
    run_experiment_1()
    run_experiment_2()
    run_experiment_3()
    run_experiment_4()
    run_experiment_5()
