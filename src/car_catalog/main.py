import sys
from collections import deque
from itertools import islice
from pathlib import Path
from time import perf_counter
from car_catalog.abstractions import (
    PercentageDiscount,
)
from car_catalog.analytics import (
    calculate_average_price,
    calculate_average_prices,
    create_car_record,
    create_price_filter,
    find_lowest_mileage_car,
    find_most_expensive_car,
    get_catalog_summary,
    get_price_range,
    sort_by_price,
    cached_brand_statistics,
    calculate_scores_sequential,
    generate_sample_prices,
    invalidate_brand_statistics_cache,
    statistics_numpy,
    statistics_python,
)
from car_catalog.parallel import (
    ThreadSafeCounter,
    calculate_scores_processes,
    calculate_scores_threads,
)
from car_catalog.profiling import (
    calculate_speedup,
    get_system_cpu_count,
)
from car_catalog.batches import batched_cars
from car_catalog.benchmark import (
    benchmark_early_termination,
    generate_cars_csv,
    run_streaming_benchmark,
)
from car_catalog.comparisons import (
    ComposedVehicleProcessor,
    CsvVehicleProcessor,
    VehicleFormatter,
    VehicleParser,
    VehicleValidator,
)
from car_catalog.criteria import (
    AndCriteria,
    BrandCriteria,
    PriceRangeCriteria,
    YearRangeCriteria,
)
from car_catalog.data import DEMO_CARS, generate_cars
from car_catalog.dto import (
    VehiclePayload,
    vehicle_from_payload,
)
from car_catalog.iterators import CarCatalogIterable, recursive_flatten
from car_catalog.models import Car, ElectricCar, VehicleCatalog
from car_catalog.notifiers import ConsoleNotifier
from car_catalog.pipeline import (
    build_streaming_pipeline,
    export_stream_to_csv,
    find_first_car,
)
from car_catalog.processors import (
    count_by_brand,
    create_car_index,
    filter_by_brand,
    filter_by_year,
    filter_cars,
    find_car_by_id,
    find_car_linear,
    get_unique_brands,
    group_by_brand,
    group_by_brand_and_year,
)
from car_catalog.protocols import SearchCriteria
from car_catalog.readers import infinite_car_stream
from car_catalog.repositories import VehicleRepository
from car_catalog.services import CatalogService
from car_catalog.specifications import VehicleSpecification
from car_catalog.streaming_analytics import (
    streaming_accumulate_prices,
    streaming_groupby_brand,
    streaming_pairwise_price_diff,
    streaming_statistics,
)
from car_catalog.value_objects import Mileage, Money, VIN
from car_catalog.config import load_config
from car_catalog.exceptions import ApplicationError, RecordValidationError
from car_catalog.logging_config import configure_logging
from car_catalog.services import run_import_export_pipeline
from car_catalog.utils import logged_operation
from car_catalog.validators import parse_car_record


def print_cars(title: str, items: list[Car]) -> None:
    print(f"\n{title}")
    print("-" * 75)
    print(f"{'ID':>3} | {'Марка та модель':22} | {'Рік':4} | {'Ціна ($)':>10} | {'Пробіг (км)':>12}")
    print("-" * 75)
    for c in items:
        print(f"{c.id:3} | {c.full_name:22} | {c.year:4} | {c.price:10.2f} | {c.mileage:12.1f}")


def run_benchmark() -> list[tuple[int, float, float]]:
    sizes = [1000, 10000, 100000]
    results: list[tuple[int, float, float]] = []
    print("\n" + "=" * 65)
    print("  ЕКСПЕРИМЕНТАЛЬНИЙ БЕНЧМАРК: List Search проти Dict Index Search")
    print("=" * 65)
    for size in sizes:
        dataset = generate_cars(size)
        index = create_car_index(dataset)
        target_id = size - 1

        start_linear = perf_counter()
        _ = find_car_linear(dataset, target_id)
        time_linear = perf_counter() - start_linear

        start_dict = perf_counter()
        _ = find_car_by_id(index, target_id)
        time_dict = perf_counter() - start_dict

        results.append((size, time_linear, time_dict))
        print(f"Розмір: {size:6} | Пошук у List: {time_linear:.8f} с | Пошук у Dict: {time_dict:.8f} с")
    print("=" * 65)
    return results


def run_demo(cars: list[Car]) -> None:
    print("\n" + "=" * 75)
    print("  ДЕМОНСТРАЦІЯ МОДУЛЯ ОБРОБКИ ДАНИХ (ЛАБОРАТОРНА РОБОТА №2, ВАРІАНТ 5)")
    print("=" * 75)

    print_cars("1. Всі автомобілі в каталозі (list[Car])", cars)

    unique_brands = get_unique_brands(cars)
    print("\n2. Унікальні марки (set):", unique_brands)

    brand_counts = count_by_brand(cars)
    print("\n3. Кількість авто кожної марки (Counter):")
    for brand, count in brand_counts.items():
        print(f"   {brand}: {count}")

    avg_price = calculate_average_price(cars)
    print(f"\n4. Середня ціна всіх автомобілів: {avg_price:.2f}$")

    best_car = find_most_expensive_car(cars)
    if best_car:
        print(f"\n5. Найдорожчий автомобіль: {best_car.full_name} ({best_car.price:.2f}$)")

    lowest_mileage = find_lowest_mileage_car(cars)
    if lowest_mileage:
        print(f"\n6. Найменший пробіг: {lowest_mileage.full_name} ({lowest_mileage.mileage:.1f} км)")

    price_range = get_price_range(cars)
    print(f"\n7. Діапазон цін (tuple[float, float]): від {price_range[0]:.2f}$ до {price_range[1]:.2f}$")

    sorted_cars = sort_by_price(cars, reverse=True)
    print_cars("8. Сортування за ціною (спадання, lambda)", sorted_cars)

    grouped_cars = group_by_brand(cars)
    print("\n9. Групування автомобілів за марками (defaultdict):")
    for brand, group_items in grouped_cars.items():
        print(f"   {brand} ({len(group_items)} авто): {', '.join(c.model for c in group_items)}")

    nested_group = group_by_brand_and_year(cars)
    print("\n10. Вкладене групування за маркою та роком:")
    for b, years in nested_group.items():
        for y, items in years.items():
            print(f"   {b} [{y}]: {len(items)} шт.")

    car_index = create_car_index(cars)
    search_id = 3
    found_car = find_car_by_id(car_index, search_id)
    print(f"\n11. Пошук за ID={search_id} через dict index O(1):")
    print(
        f"   {found_car.full_name} | Рік: {found_car.year} | Ціна: {found_car.price}$"
        if found_car
        else "   Не знайдено"
    )

    price_filter = create_price_filter(15000.0, 50000.0)
    affordable_cars = filter_cars(cars, price_filter)
    print_cars("12. Фільтрація за ціною [15000$ - 50000$] (використання closure)", affordable_cars)

    demo_avg = calculate_average_prices(12000.0, 24000.0, 36000.0, 48000.0)
    print(f"\n13. Обчислення середнього значення довільних цін через *args: {demo_avg:.2f}$")

    new_car = create_car_record(
        id=9,
        brand="Porsche",
        model="911 Carrera",
        year=2023,
        price=115000.0,
        mileage=12000.0,
    )
    print(f"\n14. Створення об'єкта через **kwargs: {new_car.full_name} (ID: {new_car.id}, {new_car.price}$)")
    print(f"    Кортеж сутності (Car.to_tuple): {new_car.to_tuple()}")

    summary = get_catalog_summary(cars)
    print("\n15. Зведений звіт каталогу (Aggregation Summary):")
    for k, v in summary.items():
        print(f"   {k}: {v}")


def run_stream_demo(demo_path: Path | None = None) -> None:
    if demo_path is None:
        demo_path = Path("data/demo_stream_cars.csv")
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    generate_cars_csv(demo_path, 100, invalid_ratio=0.04)

    print("\n" + "=" * 78)
    print("  ДЕМОНСТРАЦІЯ ПОТОКОВОЇ ОБРОБКИ ДАНИХ (ЛАБОРАТОРНА РОБОТА №3, ВАРІАНТ 5)")
    print("=" * 78)

    errors: dict[str, int] = {}
    stream = build_streaming_pipeline(demo_path, error_tracker=errors)
    first_5 = list(islice(stream, 5))
    print_cars("1. Перші 5 валідних записів із потоку (islice)", first_5)
    print(f"   [Потокова валідація]: виявлено та відсіяно некоректних записів: {errors.get('invalid_records', 0)}")

    bmw_pipeline = build_streaming_pipeline(demo_path, brand="BMW", min_year=2015)
    first_bmw = list(islice(bmw_pipeline, 4))
    print_cars("2. Фільтрація потоку за маркою ('BMW') та роком (>= 2015)", first_bmw)

    stats_pipeline = build_streaming_pipeline(demo_path)
    stats = streaming_statistics(stats_pipeline)
    print("\n3. Потокова однопрохідна агрегація (Streaming Statistics):")
    print(f"   Кількість валідних авто: {stats['count']}")
    print(f"   Загальна ринкова вартість: {stats['total_value']:.2f}$")
    print(f"   Streaming Average Price: {stats['average_price']:.2f}$")
    print(f"   Діапазон цін: від {stats['min_price']:.2f}$ до {stats['max_price']:.2f}$")
    if stats["most_expensive"]:
        print(f"   Найдорожчий автомобіль: {stats['most_expensive'].full_name} ({stats['most_expensive'].price:.2f}$)")
    if stats["lowest_mileage"]:
        print(
            f"   Автомобіль з найменшим пробігом: {stats['lowest_mileage'].full_name} ({stats['lowest_mileage'].mileage:.1f} км)"
        )

    batch_pipeline = build_streaming_pipeline(demo_path)
    print("\n4. Пакетна обробка потоку (Batching по 10 авто):")
    for batch_idx, batch in enumerate(islice(batched_cars(batch_pipeline, batch_size=10), 3), 1):
        prices_sum = sum(c.price for c in batch)
        print(
            f"   Батч #{batch_idx}: {len(batch)} авто | Сума вартості: {prices_sum:.2f}$ | Моделі: {', '.join(c.model for c in batch[:3])}..."
        )

    early_pipeline = build_streaming_pipeline(demo_path)
    target = find_first_car(early_pipeline, lambda c: c.price > 6000.0)
    print("\n5. Lazy Search із Early Termination (перший автомобіль з ціною > 6 000$):")
    if target:
        print(f"   Знайдено: {target.full_name} (ID: {target.id}, Рік: {target.year}, Ціна: {target.price:.2f}$)")

    infinite_stream = infinite_car_stream(start_id=1000)
    infinite_sample = list(islice(infinite_stream, 3))
    print_cars("6. Генерація нескінченного потоку (infinite generator + islice)", infinite_sample)

    group_pipeline = build_streaming_pipeline(demo_path)
    grouped = streaming_groupby_brand(islice(group_pipeline, 20))
    print("\n7. Групування через itertools.groupby (перші 20 авто після сортування за маркою):")
    for b_name, b_items in grouped[:4]:
        print(f"   Марка '{b_name}' ({len(b_items)} шт.): {', '.join(c.model for c in b_items)}")

    pair_pipeline = build_streaming_pipeline(demo_path)
    pair_sample = list(islice(streaming_pairwise_price_diff(pair_pipeline), 3))
    print("\n8. Аналіз дельти цін між сусідніми авто (itertools.pairwise):")
    for prev_c, curr_c, diff in pair_sample:
        sign = "+" if diff >= 0 else ""
        print(
            f"   {prev_c.full_name} ({prev_c.price:.0f}$) -> {curr_c.full_name} ({curr_c.price:.0f}$) | Різниця: {sign}{diff:.2f}$"
        )

    acc_pipeline = build_streaming_pipeline(demo_path)
    cum_prices = list(islice(streaming_accumulate_prices(acc_pipeline), 4))
    print("\n9. Кумулятивна вартість (itertools.accumulate):", [f"{p:.2f}$" for p in cum_prices])

    export_path = Path("data/demo_export.csv")
    export_pipeline = build_streaming_pipeline(demo_path, min_year=2020)
    exported_count = export_stream_to_csv(export_pipeline, export_path)
    print(f"\n10. Потоковий експорт у новий CSV файл: експортовано {exported_count} авто у {export_path}")

    custom_iter = CarCatalogIterable(DEMO_CARS)
    print(f"\n11. Власний ітераторний клас CarCatalogIterator: довжина {len(custom_iter)}")
    first_two = [c.full_name for c in islice(iter(custom_iter), 2)]
    print(f"    Перші два авто через custom iterator: {', '.join(first_two)}")

    nested_data = [DEMO_CARS[0], [DEMO_CARS[1], [DEMO_CARS[2], DEMO_CARS[3]]]]
    flattened = list(recursive_flatten(nested_data))
    print(f"\n12. Рекурсивний генератор з yield from (flattening): розгорнуто {len(flattened)} об'єктів")


def run_stream_benchmark_cli() -> None:
    print("\n" + "=" * 80)
    print("  ЕКСПЕРИМЕНТАЛЬНЕ ПОРІВНЯННЯ: Eager Evaluation проти Lazy Streaming Pipeline")
    print("  (Дослідження часу, оперативної пам'яті, TTFR та раннього завершення)")
    print("=" * 80)

    sizes = [10_000, 100_000, 500_000]
    results = run_streaming_benchmark(sizes)

    print("\nТаблиця 1: Порівняння тривалості обробки та пікового споживання пам'яті:")
    print("-" * 88)
    print(
        f"{'К-сть рядків':>12} | {'Eager Час (с)':>14} | {'Lazy Час (с)':>13} | {'Eager RAM (KiB)':>16} | {'Lazy RAM (KiB)':>15} | {'Економія RAM':>14}"
    )
    print("-" * 88)
    for r in results:
        print(
            f"{r['size']:12,d} | {r['eager_time']:14.4f} | {r['lazy_time']:13.4f} | {r['eager_peak_kib']:16.1f} | {r['lazy_peak_kib']:15.1f} | {r['memory_ratio']:13.1f}x"
        )
    print("-" * 88)

    print("\nТаблиця 2: Порівняння Time to First Result (TTFR):")
    print("-" * 65)
    print(f"{'К-сть рядків':>12} | {'Eager TTFR (с)':>16} | {'Lazy TTFR (с)':>15} | {'Прискорення':>12}")
    print("-" * 65)
    for r in results:
        print(f"{r['size']:12,d} | {r['eager_ttfr']:16.6f} | {r['lazy_ttfr']:15.6f} | {r['speedup_ttfr']:11.1f}x")
    print("-" * 65)

    print("\nДослідження Early Termination (пошук першого запису у файлі на 100 000 записів):")
    early_file = Path("data/cars_100000.csv")
    if not early_file.exists():
        generate_cars_csv(early_file, 100_000)
    early_res = benchmark_early_termination(early_file)
    print(f"  Eager час: {early_res['eager_time']:.6f} с | Пікова пам'ять: {early_res['eager_peak_kib']:.1f} KiB")
    print(f"  Lazy час:  {early_res['lazy_time']:.6f} с | Пікова пам'ять: {early_res['lazy_peak_kib']:.1f} KiB")
    print(f"  Прискорення: {early_res['speedup']:.1f}x | Економія пам'яті: {early_res['memory_saving_ratio']:.1f}x")
    print("=" * 80)


def run_oop_demo() -> None:
    print("\n" + "=" * 80)
    print("  ДЕМОНСТРАЦІЯ ПРОФЕСІЙНОГО ООП ТА СИСТЕМИ ТИПІВ (ЛАБОРАТОРНА РОБОТА №4)")
    print("  (Варіант 5: Каталог автомобілів | SOLID, Protocols, Generic Repository, Value Objects)")
    print("=" * 80)

    print("\n1. Імутабельні Value Objects (dataclass frozen=True, slots=True):")
    price1 = Money(25000.0, "USD")
    price2 = Money(3500.0, "USD")
    total_price = price1 + price2
    print(f"   Money: {price1} + {price2} = {total_price}")

    mileage = Mileage(45000.0, "km")
    vin = VIN("1HGCR2F83HA123456")
    print(f"   Mileage: {mileage} | VIN: {vin}")

    try:
        _ = Money(-500.0, "USD")
    except ValueError as e:
        print(f"   Валідація Money (від'ємна сума): перехоплено ValueError -> {e}")

    print("\n2. Domain Entities, Наслідування та Композиція (VehicleSpecification):")
    spec_ice = VehicleSpecification(
        engine_type="2.5L I4 DOHC",
        transmission="Automatic 8-speed",
        horsepower=203,
        fuel_type="Gasoline",
        body_type="Sedan",
    )
    car = Car(
        id=1,
        brand="Toyota",
        model="Camry",
        year=2021,
        price=24500.0,
        mileage=42000.0,
        specification=spec_ice,
    )
    print(f"   Car (Vehicle subclass): {car}")
    print(f"   Композиція зі специфікацією: {car.specification}")

    spec_ev = VehicleSpecification(
        engine_type="Dual Electric Motors",
        transmission="Single-speed fixed gear",
        horsepower=450,
        fuel_type="Electricity",
        body_type="Sedan",
    )
    ev = ElectricCar(
        id=2,
        brand="Tesla",
        model="Model 3 Long Range",
        year=2023,
        price=41000.0,
        mileage=18000.0,
        battery_capacity=82.0,
        range_km=560.0,
        specification=spec_ev,
    )
    print(f"   ElectricCar (спеціалізація Car): {ev}")
    print(f"   Споживання енергії: {ev.energy_consumption} kWh/100km")

    print("\n3. Кастомна колекція VehicleCatalog (Dunder methods):")
    catalog = VehicleCatalog([car, ev])
    extra_car = Car(3, "BMW", "320i", 2020, 27500.0, 53000.0)
    catalog.add(extra_car)
    print(f"   __len__: {len(catalog)} автомобілів у каталозі")
    print(f"   __contains__ (ID=2 in catalog): {2 in catalog}")
    print(f"   __getitem__ (перше авто): {catalog[0].full_name}")
    print(f"   Середня ціна в каталозі: {catalog.average_price():.2f}$")
    most_exp = catalog.most_expensive()
    print(f"   Найдорожче авто: {most_exp.full_name if most_exp else 'None'} ({most_exp.price if most_exp else 0}$)")

    print("\n4. Generic Repository (InMemoryRepository[Vehicle] із TypeVar):")
    repo = VehicleRepository()
    repo.add(car)
    repo.add(ev)
    repo.add(extra_car)
    print(f"   Збережено об'єктів у Generic Repository: {repo.count()}")
    retrieved = repo.get(2)
    print(f"   Отримано за ID 2: {retrieved.full_name if retrieved else 'None'}")

    print("\n5. Пошукові критерії (Strategy Pattern & runtime_checkable Protocol):")
    crit_brand = BrandCriteria("Tesla")
    crit_price = PriceRangeCriteria(20000.0, 30000.0)
    crit_composite = AndCriteria([YearRangeCriteria(2021, 2024), PriceRangeCriteria(20000.0, 50000.0)])

    res_tesla = repo.filter(crit_brand.matches)
    res_price = repo.filter(crit_price.matches)
    res_comp = repo.filter(crit_composite.matches)
    print(f"   Пошук за маркою Tesla: {[v.full_name for v in res_tesla]}")
    print(f"   Пошук у ціновому діапазоні 20k-30k$: {[v.full_name for v in res_price]}")
    print(f"   Композитний пошук (2021-2024 рр. та 20k-50k$): {[v.full_name for v in res_comp]}")
    print(f"   Перевірка протоколу isinstance(crit_brand, SearchCriteria): {isinstance(crit_brand, SearchCriteria)}")

    print("\n6. Application Service та Dependency Injection (CatalogService):")
    notifier = ConsoleNotifier()
    discount = PercentageDiscount(10.0)
    service = CatalogService(repository=repo, notifier=notifier, discount_policy=discount)

    checkout_res = service.checkout_vehicle(2, recipient="client@example.com")
    if checkout_res.success and checkout_res.value:
        print(f"   Результат оформлення авто (зі знижкою 10%): {checkout_res.value}")

    print("\n7. DTO, TypedDict та Generic Result[T]:")
    payload: VehiclePayload = {
        "id": 4,
        "brand": "Audi",
        "model": "A4",
        "year": 2022,
        "price": 31500.0,
        "mileage": 32000.0,
        "horsepower": 190,
        "body_type": "Sedan",
    }
    car_from_dto = vehicle_from_payload(payload)
    add_res = service.add_vehicle(car_from_dto)
    print(f"   Конвертація з TypedDict у Domain Entity: {car_from_dto}")
    print(f"   Generic Result success: {add_res.success} | Value: {add_res.value.full_name if add_res.value else None}")

    print("\n8. Порівняння архітектурних підходів (Sections 72 & 73):")
    print("   [Section 72 - Dependency Injection]:")
    print("     - TightlyCoupledService: створює конкретні залежності жорстко у __init__ (високий coupling).")
    print("     - DecoupledService: отримує абстракції через DI (низький coupling, ізольоване тестування).")

    csv_raw = "10,Ford,Focus,2019,14500.0,85000.0"
    inh_proc = CsvVehicleProcessor()
    inh_res = inh_proc.process(csv_raw)
    comp_proc = ComposedVehicleProcessor(VehicleParser(), VehicleValidator(), VehicleFormatter())
    comp_res = comp_proc.process_lines([csv_raw])
    print("   [Section 73 - Inheritance vs Composition]:")
    print(f"     - Inheritance Processor результат: {inh_res[0].full_name}")
    print(f"     - Composed Processor результат:    {comp_res[0].full_name}")
    print("     - Висновок: композиція усуває монолітність базового класу та ізолює відповідальності.")


def run_reliable_demo() -> None:
    print("\n" + "=" * 70)
    print("ДЕМОНСТРАЦІЯ ЛАБОРАТОРНОЇ РОБОТИ №5: НАДІЙНИЙ ІМПОРТ/ЕКСПОРТ І СЕРІАЛІЗАЦІЯ")
    print("=" * 70)

    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"Файл конфігурації {config_path} не знайдено.")
        return

    print("\n1. Завантаження та валідація YAML конфігурації (Fail-fast):")
    config = load_config(config_path)
    print(f"   - Вхідний файл:   {config.input.path} ({config.input.format})")
    print(f"   - Вихідний файл:  {config.output.path} ({config.output.format})")
    print(f"   - Режим обробки:  skip_invalid={config.processing.skip_invalid}")
    print(f"   - Фільтр років:   [{config.processing.filters.min_year} - {config.processing.filters.max_year}]")
    print(f"   - Фільтр цін:     [{config.processing.filters.min_price}$ - {config.processing.filters.max_price}$]")
    print(f"   - Рівень логу:    {config.logging.level} -> {config.logging.path}")

    print("\n2. Ініціалізація системи логування (logging.basicConfig):")
    app_logger = configure_logging(config.logging.level, config.logging.path, console=True)
    app_logger.info("Reliable pipeline demonstration started")

    print("\n3. Виконання надійного потокового конвеєра (Tolerant mode):")
    stats = run_import_export_pipeline(config)
    print(f"   - Усього записів у файлі:  {stats.total}")
    print(f"   - Валідних записів:        {stats.valid}")
    print(f"   - Некоректних (пропущено): {stats.invalid}")
    print(f"   - Експортовано у JSON:     {stats.exported}")

    print("\n4. Демонстрація перевірки атомарного виходу (Atomic replacement):")
    if config.output.path.exists():
        size_bytes = config.output.path.stat().st_size
        print(f"   - Файл {config.output.path} створено успішно (розмір: {size_bytes} байт).")
        tmp_path = config.output.path.with_suffix(config.output.path.suffix + ".tmp")
        print(f"   - Тимчасовий файл {tmp_path} відсутній (чисте atomic replacement): {not tmp_path.exists()}")

    print("\n5. Демонстрація експорту невалідних записів (Error CSV):")
    if config.processing.error_csv_path and config.processing.error_csv_path.exists():
        err_lines = config.processing.error_csv_path.read_text(encoding="utf-8").strip().splitlines()
        print(f"   - Файл помилок {config.processing.error_csv_path} містить {len(err_lines) - 1} відхилених записів.")

    print("\n6. Демонстрація Exception Chaining (ValueError -> RecordValidationError):")
    invalid_sample = {
        "vehicle_id": "1",
        "brand": "Audi",
        "model": "A4",
        "year": "invalid_year",
        "price": "1000",
        "mileage": "5000",
    }
    try:
        parse_car_record(invalid_sample, line_number=42)
    except RecordValidationError as exc:
        print(f"   - Перехоплено: {type(exc).__name__}: {exc}")
        print(f"   - Причина (chained __cause__): {type(exc.__cause__).__name__}: {exc.__cause__}")
        print(f"   - Поле помилки: {exc.field}, рядок: {exc.line_number}")

    print("\n7. Демонстрація власного Context Manager (logged_operation):")
    with logged_operation("Test Context Operation"):
        print("   - Тіло блоку with виконується під контролем context manager.")

    print("\nДемонстрацію Лабораторної роботи №5 успішно завершено.")


def print_menu() -> None:
    print("\n--- Меню каталогу автомобілів (Лабораторні роботи №1 - №5) ---")
    print("  [Лабораторна робота №2 - Структури даних]")
    print("   1. Показати всі автомобілі")
    print("   2. Пошук за маркою")
    print("   3. Фільтрація за роком")
    print("   4. Пошук за ID (через O(1) dict index)")
    print("   5. Унікальні марки (set) та підрахунок кількості (Counter)")
    print("   6. Групування автомобілів за марками (defaultdict)")
    print("   7. Загальна аналітика (середня ціна, екстремуми, кортеж діапазону)")
    print("   8. Сортування за ціною (lambda)")
    print("   9. Фільтрація за діапазоном цін (closure)")
    print("  10. Демонстрація функцій *args та **kwargs")
    print("  11. Історія останніх операцій (deque)")
    print("  12. Запуск бенчмарку O(n) list проти O(1) dict (Лаб 2)")
    print("  13. Повна демонстрація функціоналу Лаб 2")
    print("  [Лабораторна робота №3 - Ітератори, генератори та потоки]")
    print("  14. Повна потокова демонстрація конвеєра обробки даних (Лаб 3)")
    print("  15. Експериментальний бенчмарк: Eager vs Lazy (10k, 100k, 500k записів)")
    print("  16. Демонстрація пакетної обробки (Batching через islice)")
    print("  17. Генерація великого тестового набору даних CSV")
    print("  [Лабораторна робота №4 - Професійне ООП та система типів]")
    print("  18. Демонстрація ООП, протоколів, DI та Generic Repository (Лаб 4)")
    print("  [Лабораторна робота №5 - Обробка помилок, файли та серіалізація]")
    print("  19. Надійний конвеєр імпорту/експорту та серіалізація (Лаб 5)")
    print("  [Лабораторна робота №9 - Паралельність, багатопроцесність та оптимізація]")
    print("  20. Демонстрація паралельності, багатопроцесності та оптимізації (Лаб 9)")
    print("  21. Вихід")


def run_menu(cars: list[Car]) -> None:
    history: deque[str] = deque(maxlen=10)
    car_index = create_car_index(cars)

    while True:
        print_menu()
        cmd = input("Оберіть команду (1-21): ").strip()
        history.append(f"Команда {cmd}")

        if cmd == "1":
            print_cars("Каталог автомобілів", cars)
        elif cmd == "2":
            brand = input("Введіть назву марки: ")
            res = filter_by_brand(cars, brand)
            if res:
                print_cars(f"Результати пошуку для '{brand}'", res)
            else:
                print("Автомобілів цієї марки не знайдено.")
        elif cmd == "3":
            try:
                year = int(input("Введіть рік: "))
                res = filter_by_year(cars, year)
                if res:
                    print_cars(f"Автомобілі {year} року", res)
                else:
                    print("Автомобілів за вказаний рік не знайдено.")
            except ValueError:
                print("Помилка: введіть коректне числове значення року.")
        elif cmd == "4":
            try:
                car_id = int(input("Введіть ID автомобіля: "))
                found = find_car_by_id(car_index, car_id)
                if found:
                    print(f"Знайдено: {found.full_name} | {found.year} р. | {found.price}$ | {found.mileage} км")
                else:
                    print(f"Авто з ID={car_id} не знайдено.")
            except ValueError:
                print("Помилка: введіть ціле число.")
        elif cmd == "5":
            brands = get_unique_brands(cars)
            counts = count_by_brand(cars)
            print("\nУнікальні марки (set):", brands)
            print("Статистика за марками (Counter):")
            for b, cnt in counts.items():
                print(f"  {b}: {cnt} авто")
        elif cmd == "6":
            grouped = group_by_brand(cars)
            print("\nГрупування за марками (defaultdict):")
            for b, group_cars in grouped.items():
                print(f"  {b} ({len(group_cars)}): {', '.join(c.model for c in group_cars)}")
        elif cmd == "7":
            avg_p = calculate_average_price(cars)
            expensive = find_most_expensive_car(cars)
            lowest_m = find_lowest_mileage_car(cars)
            p_range = get_price_range(cars)
            print(f"\nСередня ціна: {avg_p:.2f}$")
            if expensive:
                print(f"Найдорожче авто: {expensive.full_name} ({expensive.price}$)")
            if lowest_m:
                print(f"Найменший пробіг: {lowest_m.full_name} ({lowest_m.mileage} км)")
            print(f"Ціновий діапазон (tuple): min={p_range[0]}$, max={p_range[1]}$")
        elif cmd == "8":
            rev = input("Сортувати за спаданням? (y/n): ").strip().lower() == "y"
            sorted_res = sort_by_price(cars, reverse=rev)
            print_cars("Відсортовані автомобілі за ціною", sorted_res)
        elif cmd == "9":
            try:
                min_p = float(input("Введіть мінімальну ціну: "))
                max_p = float(input("Введіть максимальну ціну: "))
                closure_filter = create_price_filter(min_p, max_p)
                filtered = filter_cars(cars, closure_filter)
                print_cars(f"Автомобілі в діапазоні [{min_p}$ - {max_p}$]", filtered)
            except ValueError:
                print("Помилка: введіть числові значення цін.")
        elif cmd == "10":
            avg_val = calculate_average_prices(10000.0, 20000.0, 30000.0)
            print(f"\nРезультат calculate_average_prices(*args): {avg_val:.2f}$")
            sample_car = create_car_record(
                id=10, brand="Volvo", model="XC90", year=2021, price=48000.0, mileage=55000.0
            )
            print(
                f"Створено через create_car_record(**kwargs): {sample_car.full_name}, кортеж: {sample_car.to_tuple()}"
            )
        elif cmd == "11":
            print("\nІсторія останніх операцій (collections.deque):")
            for idx, op in enumerate(history, 1):
                print(f"  {idx}. {op}")
        elif cmd == "12":
            run_benchmark()
        elif cmd == "13":
            run_demo(cars)
        elif cmd == "14":
            run_stream_demo()
        elif cmd == "15":
            run_stream_benchmark_cli()
        elif cmd == "16":
            batch_p = build_streaming_pipeline(
                Path("data/demo_stream_cars.csv")
                if Path("data/demo_stream_cars.csv").exists()
                else Path("data/cars_10000.csv")
            )
            print("\nДемонстрація batching (порціями по 5):")
            for i, batch in enumerate(islice(batched_cars(batch_p, 5), 3), 1):
                print(f"  Батч #{i}: {[c.full_name for c in batch]}")
        elif cmd == "17":
            try:
                cnt_str = input("Введіть кількість записів (за замовчуванням 100000): ").strip()
                cnt = int(cnt_str) if cnt_str else 100_000
                target_p = Path(f"data/cars_{cnt}.csv")
                print(f"Генерація {cnt} записів у {target_p}...")
                generate_cars_csv(target_p, cnt)
                print("Генерацію завершено успішно.")
            except ValueError:
                print("Помилка: введіть ціле число.")
        elif cmd == "18":
            run_oop_demo()
        elif cmd == "19":
            run_reliable_demo()
        elif cmd == "20":
            run_parallel_demo()
        elif cmd == "21":
            print("Роботу завершено. До побачення!")
            break
        else:
            print("Невідома команда. Спробуйте ще раз.")


def run_parallel_demo() -> None:
    from threading import Thread

    print("\n=== ДЕМОНСТРАЦІЯ ЛАБОРАТОРНОЇ РОБОТИ №9 (Паралельність, багатопроцесність та оптимізація) ===")
    cpu_count = get_system_cpu_count()
    print(f"Доступна кількість ядер процесора: {cpu_count}")
    prices = generate_sample_prices(5000, seed=42)
    print(f"Згенеровано вибірку з {len(prices)} цін автомобілів.")

    start = perf_counter()
    seq_scores = calculate_scores_sequential(prices)
    t_seq = perf_counter() - start
    print(f"1. Sequential baseline (CPU-bound): {t_seq:.4f} s (обчислено {len(seq_scores)} оцінок)")

    workers_to_use = min(4, max(1, cpu_count))
    start = perf_counter()
    calculate_scores_threads(prices, workers=workers_to_use)
    t_th = perf_counter() - start
    print(
        f"2. ThreadPoolExecutor ({workers_to_use} workers): {t_th:.4f} s (Speedup: {calculate_speedup(t_seq, t_th):.2f}x)"
    )

    start = perf_counter()
    calculate_scores_processes(prices, workers=workers_to_use, chunksize=100)
    t_pr = perf_counter() - start
    print(
        f"3. ProcessPoolExecutor ({workers_to_use} workers): {t_pr:.4f} s (Speedup: {calculate_speedup(t_seq, t_pr):.2f}x)"
    )

    start = perf_counter()
    py_stats = statistics_python(prices)
    t_pystat = perf_counter() - start

    start = perf_counter()
    np_stats = statistics_numpy(prices)
    t_npstat = perf_counter() - start
    print(
        f"4. Числова статистика: Pure Python = {t_pystat:.6f} s, NumPy = {t_npstat:.6f} s (Speedup: {calculate_speedup(t_pystat, t_npstat):.2f}x)"
    )
    print(f"   Python: avg={py_stats['average']:.2f}, std={py_stats['std']:.2f}")
    print(f"   NumPy:  avg={np_stats['average']:.2f}, std={np_stats['std']:.2f}")

    print("\n5. Демонстрація Caching (LRU Cache з інвалідацією):")
    start = perf_counter()
    cached_brand_statistics("BMW", version=1)
    t_cold = perf_counter() - start
    print(f"   Cold cache (перший виклик): {t_cold:.6f} s")

    start = perf_counter()
    cached_brand_statistics("BMW", version=1)
    t_warm = perf_counter() - start
    print(f"   Warm cache (повторний виклик): {t_warm:.6f} s (Speedup: {calculate_speedup(t_cold, t_warm):.2f}x)")

    invalidate_brand_statistics_cache()
    print("   Кеш інвалідовано (cache_clear / version change).")

    print("\n6. Демонстрація ThreadSafeCounter (синхронізація Lock):")
    counter = ThreadSafeCounter()

    def increment_task() -> None:
        for _ in range(1000):
            counter.increment()

    threads = [Thread(target=increment_task) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"   Фінальне значення лічильника (10 потоків x 1000 інкрементів): {counter.value} (очікувано 10000)")


def run_parallel_benchmark_cli() -> None:
    from car_catalog.profiling import benchmark_repeated

    print("\n=== ЕКСПЕРИМЕНТАЛЬНИЙ БЕНЧМАРК ОПТИМІЗАЦІЙ ЛАБОРАТОРНОЇ №9 ===")
    cpu_count = get_system_cpu_count()
    print(f"CPU cores: {cpu_count}")
    data_sizes = [5000, 20000]
    for size in data_sizes:
        print(f"\n--- Тестування на вибірці N={size} записів ---")
        prices = generate_sample_prices(size, seed=42)
        t_seq = benchmark_repeated(calculate_scores_sequential, prices, repeats=3)
        t_th = benchmark_repeated(calculate_scores_threads, prices, workers=4, repeats=3)
        t_pr = benchmark_repeated(calculate_scores_processes, prices, workers=4, chunksize=100, repeats=3)
        t_np = benchmark_repeated(statistics_numpy, prices, repeats=5)
        t_py = benchmark_repeated(statistics_python, prices, repeats=5)
        print(f"CPU-bound Sequential: {t_seq:.4f} s (1.00x)")
        print(f"CPU-bound ThreadPool (4w): {t_th:.4f} s ({calculate_speedup(t_seq, t_th):.2f}x)")
        print(f"CPU-bound ProcessPool (4w): {t_pr:.4f} s ({calculate_speedup(t_seq, t_pr):.2f}x)")
        print(
            f"Vectorization NumPy stats: {t_np:.6f} s vs Python stats {t_py:.6f} s ({calculate_speedup(t_py, t_np):.2f}x)"
        )


def main() -> None:
    cars = list(DEMO_CARS)
    if "--reliable-demo" in sys.argv:
        run_reliable_demo()
    elif "--reliable-pipeline" in sys.argv:
        idx = sys.argv.index("--reliable-pipeline")
        cfg_file = (
            Path(sys.argv[idx + 1])
            if len(sys.argv) > idx + 1 and not sys.argv[idx + 1].startswith("--")
            else Path("config.yaml")
        )
        try:
            cfg = load_config(cfg_file)
            configure_logging(cfg.logging.level, cfg.logging.path, console=cfg.logging.console)
            run_import_export_pipeline(cfg)
        except ApplicationError as err:
            print(f"Application error: {err}", file=sys.stderr)
            sys.exit(1)
    elif "--run-api" in sys.argv:
        import uvicorn

        port = 8000
        if "--port" in sys.argv:
            p_idx = sys.argv.index("--port")
            if len(sys.argv) > p_idx + 1:
                try:
                    port = int(sys.argv[p_idx + 1])
                except ValueError:
                    port = 8000
        uvicorn.run("car_catalog.api:app", host="127.0.0.1", port=port, reload=False)
    elif "--parallel-demo" in sys.argv:
        run_parallel_demo()
    elif "--parallel-benchmark" in sys.argv:
        run_parallel_benchmark_cli()
    elif "--oop-demo" in sys.argv:
        run_oop_demo()
    elif "--stream-demo" in sys.argv:
        run_stream_demo()
    elif "--stream-benchmark" in sys.argv:
        run_stream_benchmark_cli()
    elif "--demo" in sys.argv:
        run_demo(cars)
    elif "--benchmark" in sys.argv:
        run_benchmark()
    elif "--generate-dataset" in sys.argv:
        idx = sys.argv.index("--generate-dataset")
        count = 100_000
        if len(sys.argv) > idx + 1:
            try:
                count = int(sys.argv[idx + 1])
            except ValueError:
                count = 100_000
        out = Path(f"data/cars_{count}.csv")
        print(f"Генерація {count} записів у {out}...")
        generate_cars_csv(out, count)
        print("Готово.")
    else:
        run_menu(cars)


if __name__ == "__main__":
    main()
