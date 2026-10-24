import csv
import random
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any
from car_catalog.models import Car
from car_catalog.pipeline import build_streaming_pipeline, find_first_car
from car_catalog.streaming_analytics import streaming_statistics


def generate_cars_csv(path: Path, count: int, invalid_ratio: float = 0.005) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    brands_models = [
        ("Audi", "A6"),
        ("Toyota", "Camry"),
        ("BMW", "X5"),
        ("Ford", "Focus"),
        ("Mercedes-Benz", "E-Class"),
        ("Volkswagen", "Passat"),
        ("Honda", "Civic"),
        ("Skoda", "Octavia"),
        ("Volvo", "XC90"),
        ("Porsche", "911"),
    ]
    num_models = len(brands_models)
    rnd = random.Random(42)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "brand", "model", "year", "price", "mileage"])

        for idx in range(1, count + 1):
            if invalid_ratio > 0 and rnd.random() < invalid_ratio:
                corrupt_type = rnd.randint(1, 3)
                if corrupt_type == 1:
                    writer.writerow([idx, "Unknown", "Ghost", "invalid_year", "5000", "10000"])
                elif corrupt_type == 2:
                    writer.writerow([idx, "", "", "2020", "-100", "50000"])
                else:
                    writer.writerow([idx, "Faulty", "Car", "2018", "15000", "invalid_mileage"])
                continue

            brand, model = brands_models[idx % num_models]
            year = 2000 + (idx % 25)
            price = round(3000.0 + float((idx * 37) % 85000) + rnd.uniform(0, 1000), 2)
            mileage = round(5000.0 + float((idx * 123) % 350000) + rnd.uniform(0, 500), 1)
            writer.writerow([idx, brand, f"{model}-{idx}", year, f"{price:.2f}", f"{mileage:.1f}"])


def measure_peak_memory_and_time(func: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float, float]:
    tracemalloc.start()
    start_time = perf_counter()
    result = func(*args, **kwargs)
    elapsed = perf_counter() - start_time
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed, float(peak)


def run_eager_pipeline(path: Path, min_year: int = 2015) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    lines = [line.strip() for line in raw_lines if line.strip() and not line.strip().startswith("#")]
    reader = csv.DictReader(lines)
    all_rows = list(reader)

    valid_cars: list[Car] = []
    for row in all_rows:
        try:
            cid = int(row["id"])
            b = row["brand"].strip()
            m = row["model"].strip()
            y = int(row["year"])
            p = float(row["price"])
            mil = float(row["mileage"])
            if cid > 0 and b and m and (1900 <= y <= 2026) and p >= 0.0 and mil >= 0.0:
                valid_cars.append(Car(id=cid, brand=b.title(), model=m, year=y, price=p, mileage=mil))
        except (ValueError, KeyError, TypeError):
            continue

    filtered_cars = [c for c in valid_cars if c.year >= min_year]

    if not filtered_cars:
        return {"count": 0, "average_price": 0.0}

    total_price = sum(c.price for c in filtered_cars)
    avg_price = total_price / len(filtered_cars)
    most_expensive = max(filtered_cars, key=lambda c: c.price)
    lowest_mileage = min(filtered_cars, key=lambda c: c.mileage)

    return {
        "count": len(filtered_cars),
        "total_value": total_price,
        "average_price": avg_price,
        "most_expensive": most_expensive,
        "lowest_mileage": lowest_mileage,
    }


def run_lazy_pipeline(path: Path, min_year: int = 2015) -> dict[str, Any]:
    error_tracker: dict[str, int] = {}
    pipeline = build_streaming_pipeline(path, min_year=min_year, error_tracker=error_tracker)
    stats = streaming_statistics(pipeline)
    stats["invalid_records"] = error_tracker.get("invalid_records", 0)
    return stats


def measure_ttfr(path: Path, min_year: int = 2015) -> tuple[float, float]:
    start_eager = perf_counter()
    _eager_res = run_eager_pipeline(path, min_year=min_year)
    eager_ttfr = perf_counter() - start_eager

    start_lazy = perf_counter()
    pipeline = build_streaming_pipeline(path, min_year=min_year)
    _first_car = next(pipeline, None)
    lazy_ttfr = perf_counter() - start_lazy

    return eager_ttfr, lazy_ttfr


def run_streaming_benchmark(sizes: list[int] | None = None, base_dir: Path | None = None) -> list[dict[str, Any]]:
    if sizes is None:
        sizes = [10_000, 100_000, 500_000]
    if base_dir is None:
        base_dir = Path("data")
    base_dir.mkdir(parents=True, exist_ok=True)

    benchmark_results: list[dict[str, Any]] = []

    for size in sizes:
        file_path = base_dir / f"cars_{size}.csv"
        generate_cars_csv(file_path, size, invalid_ratio=0.005)

        _, eager_time, eager_peak = measure_peak_memory_and_time(run_eager_pipeline, file_path, 2015)
        _, lazy_time, lazy_peak = measure_peak_memory_and_time(run_lazy_pipeline, file_path, 2015)
        eager_ttfr, lazy_ttfr = measure_ttfr(file_path, 2015)

        row = {
            "size": size,
            "eager_time": eager_time,
            "lazy_time": lazy_time,
            "eager_peak_bytes": eager_peak,
            "lazy_peak_bytes": lazy_peak,
            "eager_peak_kib": eager_peak / 1024.0,
            "lazy_peak_kib": lazy_peak / 1024.0,
            "eager_peak_mib": eager_peak / (1024.0 * 1024.0),
            "lazy_peak_mib": lazy_peak / (1024.0 * 1024.0),
            "eager_ttfr": eager_ttfr,
            "lazy_ttfr": lazy_ttfr,
            "memory_ratio": eager_peak / lazy_peak if lazy_peak > 0 else 0.0,
            "speedup_ttfr": eager_ttfr / lazy_ttfr if lazy_ttfr > 0 else 0.0,
        }
        benchmark_results.append(row)

    return benchmark_results


def benchmark_early_termination(path: Path) -> dict[str, Any]:
    target_price = 87000.0

    def predicate(c: Car) -> bool:
        return c.price >= target_price

    def eager_find_first(p: Path) -> Car | None:
        with p.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        rows = list(csv.DictReader(lines))
        matched: list[Car] = []
        for r in rows:
            try:
                car = Car(
                    id=int(r["id"]),
                    brand=r["brand"].strip().title(),
                    model=r["model"].strip(),
                    year=int(r["year"]),
                    price=float(r["price"]),
                    mileage=float(r["mileage"]),
                )
                if predicate(car):
                    matched.append(car)
            except (ValueError, KeyError, TypeError):
                continue
        return matched[0] if matched else None

    def lazy_find_first(p: Path) -> Car | None:
        pipe = build_streaming_pipeline(p)
        return find_first_car(pipe, predicate)

    eager_car, eager_time, eager_peak = measure_peak_memory_and_time(eager_find_first, path)
    lazy_car, lazy_time, lazy_peak = measure_peak_memory_and_time(lazy_find_first, path)

    return {
        "eager_car": eager_car,
        "lazy_car": lazy_car,
        "eager_time": eager_time,
        "lazy_time": lazy_time,
        "eager_peak_kib": eager_peak / 1024.0,
        "lazy_peak_kib": lazy_peak / 1024.0,
        "speedup": eager_time / lazy_time if lazy_time > 0 else 0.0,
        "memory_saving_ratio": eager_peak / lazy_peak if lazy_peak > 0 else 0.0,
    }
