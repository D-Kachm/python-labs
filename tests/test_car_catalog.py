import tempfile
import unittest
from pathlib import Path
from itertools import islice
from car_catalog.models import Car
from car_catalog.readers import infinite_car_stream, read_lines, read_multiple_files
from car_catalog.parsers import clean_lines, parse_csv_rows
from car_catalog.filters import (
    filter_by_brand_and_year_stream,
    filter_by_brand_stream,
    filter_by_year_stream,
    filter_cars_stream,
    validate_cars,
)
from car_catalog.transformations import apply_price_discount, normalize_car_names
from car_catalog.batches import batched_cars
from car_catalog.iterators import CarCatalogIterable, CarCatalogIterator, recursive_flatten
from car_catalog.streaming_analytics import (
    streaming_accumulate_prices,
    streaming_average_price,
    streaming_find_lowest_mileage,
    streaming_find_most_expensive,
    streaming_groupby_brand,
    streaming_pairwise_price_diff,
    streaming_statistics,
)
from car_catalog.pipeline import (
    build_streaming_pipeline,
    export_stream_to_csv,
    find_first_car,
)
from car_catalog.analytics import calculate_average_price, find_most_expensive_car
from car_catalog.data import DEMO_CARS, generate_cars
from car_catalog.processors import create_car_index, filter_by_brand

class TestStreamingReadersAndParsers(unittest.TestCase):
    def test_read_lines_and_clean(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("line 1\n\n  \n# comment\nline 2   \n")
            f_path = Path(f.name)

        try:
            raw = list(read_lines(f_path))
            self.assertEqual(len(raw), 5)

            cleaned = list(clean_lines(raw))
            self.assertEqual(cleaned, ["line 1", "line 2"])
        finally:
            f_path.unlink()

    def test_read_multiple_files(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f1, \
             tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f2:
            f1.write("a\nb\n")
            f2.write("c\nd\n")
            p1 = Path(f1.name)
            p2 = Path(f2.name)

        try:
            combined = list(read_multiple_files(p1, p2))
            self.assertEqual(combined, ["a\n", "b\n", "c\n", "d\n"])
        finally:
            p1.unlink()
            p2.unlink()

    def test_infinite_car_stream(self) -> None:
        stream = infinite_car_stream(start_id=10)
        first_3 = list(islice(stream, 3))
        self.assertEqual(len(first_3), 3)
        self.assertEqual(first_3[0].id, 10)
        self.assertEqual(first_3[1].id, 11)
        self.assertEqual(first_3[2].id, 12)

class TestStreamingFiltersAndValidation(unittest.TestCase):
    def test_validate_cars(self) -> None:
        rows = [
            {"id": "1", "brand": "Audi", "model": "A6", "year": "2020", "price": "40000", "mileage": "50000"},
            {"id": "-5", "brand": "Bad", "model": "Car", "year": "2020", "price": "100", "mileage": "0"},
            {"id": "2", "brand": "BMW", "model": "X5", "year": "invalid_year", "price": "50000", "mileage": "20000"},
            {"id": "3", "brand": "Toyota", "model": "Camry", "year": "2022", "price": "25000", "mileage": "15000"},
        ]
        errors: dict[str, int] = {}
        valid = list(validate_cars(rows, error_tracker=errors))
        self.assertEqual(len(valid), 2)
        self.assertEqual(errors["invalid_records"], 2)
        self.assertEqual(valid[0].brand, "Audi")
        self.assertEqual(valid[1].brand, "Toyota")

    def test_filter_by_brand_and_year_stream(self) -> None:
        cars = [
            Car(1, "Audi", "A6", 2020, 30000.0, 50000.0),
            Car(2, "BMW", "X5", 2018, 40000.0, 60000.0),
            Car(3, "Audi", "Q7", 2015, 35000.0, 90000.0),
        ]
        filtered = list(filter_by_brand_and_year_stream(cars, brand="Audi", min_year=2018))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].model, "A6")

class TestTransformationsAndBatches(unittest.TestCase):
    def test_normalize_car_names(self) -> None:
        cars = [Car(1, " audi ", "  a6 avant  ", 2020, 20000.0, 10000.0)]
        normalized = list(normalize_car_names(cars))[0]
        self.assertEqual(normalized.brand, "Audi")
        self.assertEqual(normalized.model, "a6 avant")

    def test_apply_price_discount(self) -> None:
        cars = [Car(1, "BMW", "M3", 2022, 10000.0, 5000.0)]
        discounted = list(apply_price_discount(cars, 10.0))[0]
        self.assertEqual(discounted.price, 9000.0)

    def test_batched_cars(self) -> None:
        cars = [Car(i, "Brand", f"M{i}", 2020, 1000.0 * i, 1000.0) for i in range(1, 8)]
        batches = list(batched_cars(cars, batch_size=3))
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 3)
        self.assertEqual(len(batches[1]), 3)
        self.assertEqual(len(batches[2]), 1)

class TestIteratorsAndAnalytics(unittest.TestCase):
    def test_custom_iterator_and_iterable(self) -> None:
        cars = [DEMO_CARS[0], DEMO_CARS[1]]
        catalog_iter = CarCatalogIterable(cars)
        self.assertEqual(len(catalog_iter), 2)
        iter1 = list(catalog_iter)
        iter2 = list(catalog_iter)
        self.assertEqual(len(iter1), 2)
        self.assertEqual(len(iter2), 2)

    def test_recursive_flatten(self) -> None:
        nested = [1, [2, [3, 4], 5], (6, 7)]
        flat = list(recursive_flatten(nested))
        self.assertEqual(flat, [1, 2, 3, 4, 5, 6, 7])

    def test_streaming_analytics(self) -> None:
        cars = [
            Car(1, "Audi", "A6", 2020, 10000.0, 50000.0),
            Car(2, "BMW", "X5", 2021, 20000.0, 30000.0),
            Car(3, "Audi", "Q7", 2022, 30000.0, 10000.0),
        ]
        avg = streaming_average_price(cars)
        self.assertAlmostEqual(avg, 20000.0)

        stats = streaming_statistics(cars)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["min_price"], 10000.0)
        self.assertEqual(stats["max_price"], 30000.0)
        self.assertEqual(stats["most_expensive"].id, 3)
        self.assertEqual(stats["lowest_mileage"].id, 3)
        self.assertEqual(stats["brands"]["Audi"], 2)

    def test_pairwise_and_accumulate(self) -> None:
        cars = [
            Car(1, "A", "1", 2020, 100.0, 0.0),
            Car(2, "B", "2", 2020, 150.0, 0.0),
            Car(3, "C", "3", 2020, 130.0, 0.0),
        ]
        diffs = [diff for _, _, diff in streaming_pairwise_price_diff(cars)]
        self.assertEqual(diffs, [50.0, -20.0])

        accum = list(streaming_accumulate_prices(cars))
        self.assertEqual(accum, [100.0, 250.0, 380.0])

class TestPipelineAndCompatibility(unittest.TestCase):
    def test_end_to_end_pipeline(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            f.write("id,brand,model,year,price,mileage\n")
            f.write("1,audi,a6,2020,40000.0,50000.0\n")
            f.write("2,bmw,x5,2010,25000.0,150000.0\n")
            f.write("3,audi,q7,2022,60000.0,20000.0\n")
            p = Path(f.name)

        try:
            pipe = build_streaming_pipeline(p, brand="Audi", min_year=2021)
            results = list(pipe)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].brand, "Audi")
            self.assertEqual(results[0].model, "q7")

            first = find_first_car(build_streaming_pipeline(p), lambda c: c.price > 50000.0)
            self.assertIsNotNone(first)
            assert first is not None
            self.assertEqual(first.id, 3)
        finally:
            p.unlink()

    def test_backwards_compatibility(self) -> None:
        self.assertTrue(len(DEMO_CARS) > 0)
        dataset = generate_cars(10)
        self.assertEqual(len(dataset), 10)
        idx = create_car_index(dataset)
        self.assertEqual(len(idx), 10)
        avg = calculate_average_price(dataset)
        self.assertTrue(avg > 0)
        filtered = filter_by_brand(dataset, "Audi")
        self.assertTrue(isinstance(filtered, list))

if __name__ == "__main__":
    unittest.main()
