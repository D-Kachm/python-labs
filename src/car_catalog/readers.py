from collections.abc import Iterator
from itertools import chain, count
from pathlib import Path
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
