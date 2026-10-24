from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
from typing import Any
from car_catalog.abstractions import DiscountPolicy, Repository
from car_catalog.config import AppConfig, FilterConfig
from car_catalog.criteria import BrandAndModelCriteria, BrandCriteria, YearRangeCriteria
from car_catalog.dto import Result
from car_catalog.exceptions import RecordValidationError
from car_catalog.exporters import export_invalid_records_csv, get_exporter
from car_catalog.models import Car, Vehicle
from car_catalog.processors import filter_by_brand
from car_catalog.protocols import (
    AsyncExternalMarketClient,
    ExternalVehicleInfoService,
    SearchCriteria,
    VehicleNotifier,
)
from car_catalog.readers import read_file_rows
from car_catalog.utils import logged_operation
from car_catalog.validators import parse_car_record
from car_catalog.value_objects import Money

service_logger = logging.getLogger(__name__)


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


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    exported: int = 0


def import_cars(
    path: Path,
    *,
    skip_invalid: bool,
    statistics: ImportStatistics,
    error_sink: list[dict[str, Any]] | None = None,
    file_format: str | None = None,
) -> Iterator[Car]:
    for line_number, row in read_file_rows(path, file_format):
        statistics.total += 1
        try:
            car = parse_car_record(row, line_number=line_number)
        except RecordValidationError as error:
            statistics.invalid += 1
            service_logger.warning("Invalid record at line %s: %s", error.line_number, error)
            if error_sink is not None:
                error_sink.append(
                    {
                        "line_number": error.line_number,
                        "field": error.field,
                        "message": str(error),
                        "raw_data": row,
                    }
                )
            if skip_invalid:
                continue
            raise
        else:
            statistics.valid += 1
            yield car


def filter_imported_cars(
    cars: Iterable[Car],
    filters: FilterConfig,
) -> Iterator[Car]:
    for car in cars:
        if filters.min_year <= car.year <= filters.max_year and filters.min_price <= car.price <= filters.max_price:
            yield car


def run_import_export_pipeline(config: AppConfig) -> ImportStatistics:
    with logged_operation("Car import/export pipeline"):
        if config.processing.backup_existing and config.output.path.exists():
            backup_path = config.output.path.with_suffix(config.output.path.suffix + ".bak")
            shutil.copy2(config.output.path, backup_path)
            service_logger.info("Backup created at %s", backup_path)

        statistics = ImportStatistics()
        error_records: list[dict[str, Any]] = []
        error_sink = error_records if config.processing.error_csv_path is not None else None

        cars_stream = import_cars(
            config.input.path,
            skip_invalid=config.processing.skip_invalid,
            statistics=statistics,
            error_sink=error_sink,
            file_format=config.input.format,
        )

        filtered_stream = filter_imported_cars(cars_stream, config.processing.filters)
        exporter = get_exporter(config.output.format)
        exported_count = exporter.export(filtered_stream, config.output.path)
        statistics.exported = exported_count

        if error_sink and config.processing.error_csv_path is not None:
            export_invalid_records_csv(error_records, config.processing.error_csv_path)
            service_logger.info(
                "Exported %s invalid records to %s", len(error_records), config.processing.error_csv_path
            )

        service_logger.info(
            "Total=%s, valid=%s, invalid=%s, exported=%s",
            statistics.total,
            statistics.valid,
            statistics.invalid,
            statistics.exported,
        )
        return statistics


class VehicleEnrichmentService:
    def __init__(self, external_service: ExternalVehicleInfoService) -> None:
        self._external_service = external_service

    def enrich_specs(self, vin: str) -> dict[str, Any]:
        if not vin or len(vin) != 17:
            raise ValueError("VIN must contain exactly 17 characters")
        data = self._external_service.fetch_vehicle_specs(vin)
        return data


class AsyncVehicleMarketService:
    def __init__(self, client: AsyncExternalMarketClient) -> None:
        self._client = client

    async def get_market_price(self, brand: str, model: str, year: int) -> float:
        data = await self._client.fetch_market_evaluation(brand, model, year)
        price_val = data.get("estimated_price")
        if price_val is None:
            raise ValueError("Price not found in market evaluation")
        return float(price_val)


async def async_run_import_export_pipeline(
    config: AppConfig,
    market_service: AsyncVehicleMarketService | None = None,
) -> ImportStatistics:
    with logged_operation("Async car import/export pipeline"):
        if config.processing.backup_existing and config.output.path.exists():
            backup_path = config.output.path.with_suffix(config.output.path.suffix + ".bak")
            shutil.copy2(config.output.path, backup_path)

        statistics = ImportStatistics()
        error_records: list[dict[str, Any]] = []
        error_sink = error_records if config.processing.error_csv_path is not None else None

        cars_stream = import_cars(
            config.input.path,
            skip_invalid=config.processing.skip_invalid,
            statistics=statistics,
            error_sink=error_sink,
            file_format=config.input.format,
        )

        filtered_stream = list(filter_imported_cars(cars_stream, config.processing.filters))
        if market_service is not None:
            for car in filtered_stream:
                _ = await market_service.get_market_price(car.brand, car.model, car.year)

        exporter = get_exporter(config.output.format)
        exported_count = exporter.export(filtered_stream, config.output.path)
        statistics.exported = exported_count

        if error_sink and config.processing.error_csv_path is not None:
            export_invalid_records_csv(error_records, config.processing.error_csv_path)

        return statistics
