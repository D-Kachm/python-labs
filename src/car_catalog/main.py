import sys
from collections import deque
from itertools import islice
from pathlib import Path
from time import perf_counter
from typing import Any
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
)
from car_catalog.batches import batched_cars
from car_catalog.benchmark import (
    benchmark_early_termination,
    generate_cars_csv,
    run_streaming_benchmark,
)
from car_catalog.data import DEMO_CARS, generate_cars
from car_catalog.decorators import measure_time, repeat
from car_catalog.iterators import CarCatalogIterable, recursive_flatten
from car_catalog.models import Car
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
from car_catalog.readers import infinite_car_stream, read_multiple_files
from car_catalog.streaming_analytics import (
    streaming_accumulate_prices,
    streaming_average_price,
    streaming_find_lowest_mileage,
    streaming_find_most_expensive,
    streaming_groupby_brand,
    streaming_pairwise_price_diff,
    streaming_statistics,
)

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
    print(f"   {found_car.full_name} | Рік: {found_car.year} | Ціна: {found_car.price}$" if found_car else "   Не знайдено")

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
        print(f"   Автомобіль з найменшим пробігом: {stats['lowest_mileage'].full_name} ({stats['lowest_mileage'].mileage:.1f} км)")

    batch_pipeline = build_streaming_pipeline(demo_path)
    print("\n4. Пакетна обробка потоку (Batching по 10 авто):")
    for batch_idx, batch in enumerate(islice(batched_cars(batch_pipeline, batch_size=10), 3), 1):
        prices_sum = sum(c.price for c in batch)
        print(f"   Батч #{batch_idx}: {len(batch)} авто | Сума вартості: {prices_sum:.2f}$ | Моделі: {', '.join(c.model for c in batch[:3])}...")

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
        print(f"   {prev_c.full_name} ({prev_c.price:.0f}$) -> {curr_c.full_name} ({curr_c.price:.0f}$) | Різниця: {sign}{diff:.2f}$")

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
    print(f"{'К-сть рядків':>12} | {'Eager Час (с)':>14} | {'Lazy Час (с)':>13} | {'Eager RAM (KiB)':>16} | {'Lazy RAM (KiB)':>15} | {'Економія RAM':>14}")
    print("-" * 88)
    for r in results:
        print(f"{r['size']:12,d} | {r['eager_time']:14.4f} | {r['lazy_time']:13.4f} | {r['eager_peak_kib']:16.1f} | {r['lazy_peak_kib']:15.1f} | {r['memory_ratio']:13.1f}x")
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

def print_menu() -> None:
    print("\n--- Меню каталогу автомобілів (Лабораторні роботи №1 - №3) ---")
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
    print("  18. Вихід")

def run_menu(cars: list[Car]) -> None:
    history: deque[str] = deque(maxlen=10)
    car_index = create_car_index(cars)

    while True:
        print_menu()
        cmd = input("Оберіть команду (1-18): ").strip()
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
                print(f"Найменший пробіг: {lowest_m.full_name} ({lowest_mileage_car(cars).mileage if lowest_m else 0} км)")
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
            print(f"Створено через create_car_record(**kwargs): {sample_car.full_name}, кортеж: {sample_car.to_tuple()}")
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
            batch_p = build_streaming_pipeline(Path("data/demo_stream_cars.csv") if Path("data/demo_stream_cars.csv").exists() else Path("data/cars_10000.csv"))
            print("\nДемонстрація batching (порціями по 5):")
            for i, b in enumerate(islice(batched_cars(batch_p, 5), 3), 1):
                print(f"  Батч #{i}: {[c.full_name for c in b]}")
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
            print("Роботу завершено. До побачення!")
            break
        else:
            print("Невідома команда. Спробуйте ще раз.")

def main() -> None:
    cars = list(DEMO_CARS)
    if "--stream-demo" in sys.argv:
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
