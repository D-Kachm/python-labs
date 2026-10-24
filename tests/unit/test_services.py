from collections.abc import Callable
from unittest.mock import AsyncMock, Mock, create_autospec
import pytest
from car_catalog.abstractions import NoDiscount, PercentageDiscount, Repository
from car_catalog.analytics import (
    calculate_average_price,
    calculate_average_prices,
    create_car_record,
    create_mileage_filter,
    create_price_filter,
    find_lowest_mileage_car,
    find_most_expensive_car,
    get_catalog_summary,
    get_price_range,
    sort_by_price,
)
from car_catalog.models import Car, Vehicle
from car_catalog.processors import (
    count_by_brand,
    create_car_index,
    find_car_by_id,
    find_car_linear,
    get_unique_brands,
    group_by_brand,
    group_by_brand_and_year,
)
from car_catalog.protocols import (
    AsyncExternalMarketClient,
    ExternalVehicleInfoService,
    VehicleNotifier,
)
from car_catalog.repositories import VehicleRepository
from car_catalog.services import (
    AsyncVehicleMarketService,
    CatalogService,
    VehicleEnrichmentService,
)


class FakeVehicleRepository(Repository[Vehicle]):
    def __init__(self) -> None:
        self._items: dict[int, Vehicle] = {}

    def add(self, item: Vehicle) -> None:
        self._items[item.id] = item

    def get(self, item_id: int) -> Vehicle | None:
        return self._items.get(item_id)

    def all(self) -> list[Vehicle]:
        return list(self._items.values())

    def remove(self, item_id: int) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def filter(self, predicate: Callable[[Vehicle], bool]) -> list[Vehicle]:
        return [item for item in self._items.values() if predicate(item)]

    def count(self) -> int:
        return len(self._items)


@pytest.mark.unit
def test_catalog_service_search_by_brand(sample_cars_list: list[Vehicle]) -> None:
    repo = VehicleRepository()
    for car in sample_cars_list:
        repo.add(car)
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    results = service.search_by_brand("Toyota")
    assert len(results) == 1
    assert results[0].brand == "Toyota"


@pytest.mark.unit
def test_catalog_service_search_by_model(sample_cars_list: list[Vehicle]) -> None:
    repo = VehicleRepository()
    for car in sample_cars_list:
        repo.add(car)
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    results = service.search_by_brand_and_model("BMW", "M3")
    assert len(results) == 1
    assert results[0].model == "M3"


@pytest.mark.unit
def test_catalog_service_filter_by_year(sample_cars_list: list[Vehicle]) -> None:
    repo = VehicleRepository()
    for car in sample_cars_list:
        repo.add(car)
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    results = service.filter_by_year(2021)
    assert len(results) == 1
    assert results[0].year == 2021


@pytest.mark.unit
def test_catalog_service_analytics_calculations(sample_cars_list: list[Vehicle]) -> None:
    repo = VehicleRepository()
    for car in sample_cars_list:
        repo.add(car)
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    most_expensive = service.find_most_expensive()
    assert most_expensive is not None
    assert most_expensive.brand == "BMW"
    assert most_expensive.price == pytest.approx(75000.0)

    avg_price = service.calculate_average_price()
    expected_avg = (26000.0 + 42000.0 + 75000.0 + 18500.0 + 38000.0) / 5
    assert avg_price == pytest.approx(round(expected_avg, 2))

    lowest_mileage = service.find_lowest_mileage()
    assert lowest_mileage is not None
    assert lowest_mileage.brand == "BMW"
    assert lowest_mileage.mileage == pytest.approx(12000.0)


@pytest.mark.unit
def test_catalog_service_empty_analytics() -> None:
    repo = VehicleRepository()
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    assert service.find_most_expensive() is None
    assert service.find_lowest_mileage() is None
    assert service.calculate_average_price() == pytest.approx(0.0)


@pytest.mark.unit
def test_fake_repository_crud(sample_car: Car) -> None:
    fake_repo = FakeVehicleRepository()
    fake_repo.add(sample_car)
    assert fake_repo.get(sample_car.id) == sample_car
    assert len(fake_repo.all()) == 1
    assert fake_repo.count() == 1

    removed = fake_repo.remove(sample_car.id)
    assert removed is True
    assert fake_repo.get(sample_car.id) is None
    assert fake_repo.remove(999) is False


@pytest.mark.unit
def test_catalog_service_with_notifier_mock(sample_car: Car) -> None:
    repo = VehicleRepository()
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, PercentageDiscount(10.0))

    result = service.add_vehicle(sample_car)
    assert result.success is True
    notifier_mock.send.assert_called_once_with(
        "admin@car-catalog.ua",
        f"New vehicle registered: {sample_car.full_name} (ID: {sample_car.id})",
    )


@pytest.mark.unit
def test_catalog_service_duplicate_add_fails(sample_car: Car) -> None:
    repo = VehicleRepository()
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, NoDiscount())

    service.add_vehicle(sample_car)
    duplicate_result = service.add_vehicle(sample_car)
    assert duplicate_result.success is False
    assert "already exists" in str(duplicate_result.error)
    notifier_mock.send.assert_called_once()


@pytest.mark.unit
def test_catalog_service_checkout(sample_car: Car) -> None:
    repo = VehicleRepository()
    repo.add(sample_car)
    notifier_mock = Mock(spec=VehicleNotifier)
    service = CatalogService(repo, notifier_mock, PercentageDiscount(10.0))

    checkout_res = service.checkout_vehicle(sample_car.id, "buyer@example.com")
    assert checkout_res.success is True
    assert checkout_res.value is not None
    assert checkout_res.value.amount == pytest.approx(23400.0)
    notifier_mock.send.assert_called_once()

    missing_res = service.checkout_vehicle(999, "buyer@example.com")
    assert missing_res.success is False
    assert "not found" in str(missing_res.error)


@pytest.mark.unit
def test_vehicle_repository_dunders(sample_car: Car) -> None:
    repo = VehicleRepository()
    repo.add(sample_car)
    assert len(repo) == 1
    assert sample_car.id in repo
    assert repo[sample_car.id] == sample_car
    assert list(iter(repo)) == [sample_car]
    assert repo.get(sample_car.id) == sample_car


@pytest.mark.unit
def test_vehicle_enrichment_service_mock_success() -> None:
    external_mock = Mock(spec=ExternalVehicleInfoService)
    external_mock.fetch_vehicle_specs.return_value = {
        "engine": "2.5L 4-Cylinder",
        "horsepower": 203,
        "transmission": "8-Speed Automatic",
    }
    enrichment_service = VehicleEnrichmentService(external_mock)
    vin = "1HGCR2F83HA123456"

    specs = enrichment_service.enrich_specs(vin)
    assert specs["horsepower"] == 203
    assert specs["engine"] == "2.5L 4-Cylinder"
    external_mock.fetch_vehicle_specs.assert_called_once_with(vin)


@pytest.mark.unit
def test_vehicle_enrichment_service_mock_side_effect_failure() -> None:
    external_mock = Mock(spec=ExternalVehicleInfoService)
    external_mock.fetch_vehicle_specs.side_effect = ConnectionError("External service timeout")
    enrichment_service = VehicleEnrichmentService(external_mock)
    vin = "1HGCR2F83HA123456"

    with pytest.raises(ConnectionError, match="External service timeout"):
        enrichment_service.enrich_specs(vin)

    external_mock.fetch_vehicle_specs.assert_called_once_with(vin)


@pytest.mark.unit
def test_vehicle_enrichment_service_invalid_vin() -> None:
    external_mock = Mock(spec=ExternalVehicleInfoService)
    enrichment_service = VehicleEnrichmentService(external_mock)

    with pytest.raises(ValueError, match="VIN must contain exactly 17 characters"):
        enrichment_service.enrich_specs("SHORT_VIN")

    external_mock.fetch_vehicle_specs.assert_not_called()


@pytest.mark.unit
def test_create_autospec_verification() -> None:
    autospec_service = create_autospec(ExternalVehicleInfoService, instance=True)
    autospec_service.fetch_vehicle_specs.return_value = {"status": "ok"}

    enrichment = VehicleEnrichmentService(autospec_service)
    result = enrichment.enrich_specs("12345678901234567")
    assert result == {"status": "ok"}
    autospec_service.fetch_vehicle_specs.assert_called_once_with("12345678901234567")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_vehicle_market_service_success() -> None:
    client_mock = AsyncMock(spec=AsyncExternalMarketClient)
    client_mock.fetch_market_evaluation.return_value = {
        "brand": "Toyota",
        "model": "Camry",
        "year": 2021,
        "estimated_price": 25500.0,
    }
    service = AsyncVehicleMarketService(client_mock)

    price = await service.get_market_price("Toyota", "Camry", 2021)
    assert price == pytest.approx(25500.0)
    client_mock.fetch_market_evaluation.assert_awaited_once_with("Toyota", "Camry", 2021)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_vehicle_market_service_failure() -> None:
    client_mock = AsyncMock(spec=AsyncExternalMarketClient)
    client_mock.fetch_market_evaluation.side_effect = TimeoutError("Market API unreachable")
    service = AsyncVehicleMarketService(client_mock)

    with pytest.raises(TimeoutError, match="Market API unreachable"):
        await service.get_market_price("BMW", "M3", 2022)

    client_mock.fetch_market_evaluation.assert_awaited_once_with("BMW", "M3", 2022)


@pytest.mark.unit
def test_legacy_analytics_and_processors_functions(sample_cars_list: list[Vehicle]) -> None:
    cars = [c for c in sample_cars_list if isinstance(c, Car)]
    assert calculate_average_price(cars) > 0.0
    assert calculate_average_price([]) == pytest.approx(0.0)
    assert calculate_average_prices(100.0, 200.0, 300.0) == pytest.approx(200.0)
    assert calculate_average_prices() == pytest.approx(0.0)

    new_car = create_car_record(id=99, brand="Ford", model="Mondeo", year=2020, price=15000.0, mileage=80000.0)
    assert new_car.id == 99

    assert find_most_expensive_car(cars) is not None
    assert find_most_expensive_car([]) is None
    assert find_lowest_mileage_car(cars) is not None
    assert find_lowest_mileage_car([]) is None

    sorted_cars = sort_by_price(cars)
    assert sorted_cars[0].price <= sorted_cars[-1].price

    p_filter = create_price_filter(20000.0, 50000.0)
    m_filter = create_mileage_filter(30000.0)
    filtered = [c for c in cars if p_filter(c) and m_filter(c)]
    assert isinstance(filtered, list)

    min_p, max_p = get_price_range(cars)
    assert min_p <= max_p
    assert get_price_range([]) == (0.0, 0.0)

    summary = get_catalog_summary(cars)
    assert summary["total_count"] == len(cars)
    assert get_catalog_summary([]) == {}

    brands = get_unique_brands(cars)
    assert "Toyota" in brands

    idx = create_car_index(cars)
    assert find_car_by_id(idx, 1) is not None
    assert find_car_linear(cars, 1) is not None
    assert find_car_linear(cars, 9999) is None

    grouped = group_by_brand(cars)
    assert "Toyota" in grouped
    grouped_by_year = group_by_brand_and_year(cars)
    assert "Toyota" in grouped_by_year

    counter = count_by_brand(cars)
    assert counter["Toyota"] >= 1
