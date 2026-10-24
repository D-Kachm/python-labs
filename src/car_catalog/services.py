from typing import Callable, Sequence
from car_catalog.abstractions import DiscountPolicy, Repository
from car_catalog.analytics import (
    calculate_average_price as legacy_avg_price,
    find_lowest_mileage_car as legacy_lowest_mileage,
    find_most_expensive_car as legacy_most_expensive,
    sort_by_price as legacy_sort_by_price,
)
from car_catalog.batches import batched_cars, dynamic_batched
from car_catalog.criteria import BrandAndModelCriteria, BrandCriteria, YearRangeCriteria
from car_catalog.dto import Result
from car_catalog.filters import (
    filter_by_brand_and_year_stream,
    filter_by_brand_stream,
    filter_by_year_stream,
    filter_cars_stream,
    validate_cars,
)
from car_catalog.models import Car, Vehicle
from car_catalog.parsers import clean_lines, parse_csv_rows
from car_catalog.pipeline import (
    build_streaming_pipeline,
    export_stream_to_csv,
    find_first_car,
)
from car_catalog.processors import (
    create_car_index,
    filter_by_brand,
    filter_by_year,
    find_car_by_id,
    get_unique_brands,
)
from car_catalog.protocols import SearchCriteria, VehicleNotifier
from car_catalog.readers import infinite_car_stream, read_lines, read_multiple_files
from car_catalog.streaming_analytics import (
    streaming_accumulate_prices,
    streaming_average_price,
    streaming_find_lowest_mileage,
    streaming_find_most_expensive,
    streaming_groupby_brand,
    streaming_min_max_price,
    streaming_pairwise_price_diff,
    streaming_statistics,
)
from car_catalog.transformations import (
    apply_price_discount,
    convert_currency,
    normalize_car_names,
)
from car_catalog.value_objects import Money

class CatalogService:
    def __init__(
        self,
        repository: Repository[Vehicle],
        notifier: VehicleNotifier,
        discount_policy: DiscountPolicy,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._discount_policy = discount_policy

    @property
    def repository(self) -> Repository[Vehicle]:
        return self._repository

    @property
    def notifier(self) -> VehicleNotifier:
        return self._notifier

    @property
    def discount_policy(self) -> DiscountPolicy:
        return self._discount_policy

    def add_vehicle(self, vehicle: Vehicle) -> Result[Vehicle]:
        if self._repository.get(vehicle.id) is not None:
            return Result(value=None, error=f"Vehicle with ID {vehicle.id} already exists")
        self._repository.add(vehicle)
        self._notifier.send("admin@car-catalog.ua", f"New vehicle registered: {vehicle.full_name} (ID: {vehicle.id})")
        return Result(value=vehicle, error=None)

    def get_vehicle(self, vehicle_id: int) -> Vehicle | None:
        return self._repository.get(vehicle_id)

    def remove_vehicle(self, vehicle_id: int) -> bool:
        removed = self._repository.remove(vehicle_id)
        if removed:
            self._notifier.send("admin@car-catalog.ua", f"Vehicle ID {vehicle_id} removed")
        return removed

    def list_all(self) -> list[Vehicle]:
        return self._repository.all()

    def search_by_brand(self, brand: str) -> list[Vehicle]:
        crit = BrandCriteria(brand)
        return self._repository.filter(crit.matches)

    def search_by_brand_and_model(self, brand: str, model: str) -> list[Vehicle]:
        crit = BrandAndModelCriteria(brand, model)
        return self._repository.filter(crit.matches)

    def filter_by_year(self, year: int) -> list[Vehicle]:
        crit = YearRangeCriteria(min_year=year, max_year=year)
        return self._repository.filter(crit.matches)

    def search_by_criteria(self, criteria: SearchCriteria) -> list[Vehicle]:
        return self._repository.filter(criteria.matches)

    def find_most_expensive(self) -> Vehicle | None:
        all_vehicles = self._repository.all()
        if not all_vehicles:
            return None
        return max(all_vehicles, key=lambda v: v.price)

    def find_lowest_mileage(self) -> Vehicle | None:
        all_vehicles = self._repository.all()
        if not all_vehicles:
            return None
        return min(all_vehicles, key=lambda v: v.mileage)

    def calculate_average_price(self) -> float:
        all_vehicles = self._repository.all()
        if not all_vehicles:
            return 0.0
        return round(sum(v.price for v in all_vehicles) / len(all_vehicles), 2)

    def checkout_vehicle(self, vehicle_id: int, recipient: str) -> Result[Money]:
        vehicle = self._repository.get(vehicle_id)
        if vehicle is None:
            return Result(value=None, error=f"Vehicle with ID {vehicle_id} not found")
        final_price = self._discount_policy.apply(vehicle.price_money)
        self._notifier.send(
            recipient,
            f"Checkout approved for {vehicle.full_name}. Price: {final_price} (Original: {vehicle.price:.2f}$)",
        )
        return Result(value=final_price, error=None)

def search_by_brand(cars: list[Car], brand: str) -> list[Car]:
    return filter_by_brand(cars, brand)

def process_pipeline(cars: list[Car], *operations: Callable[[list[Car]], list[Car]]) -> list[Car]:
    result = cars
    for op in operations:
        result = op(result)
    return result
