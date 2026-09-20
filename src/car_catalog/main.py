import sys
from collections import deque
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
from car_catalog.data import DEMO_CARS, generate_cars
from car_catalog.decorators import measure_time, repeat
from car_catalog.models import Car
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

def print_menu() -> None:
    print("\n--- Меню каталогу автомобілів (Лабораторна робота №2) ---")
    print("1. Показати всі автомобілі")
    print("2. Пошук за маркою")
    print("3. Фільтрація за роком")
    print("4. Пошук за ID (через O(1) dict index)")
    print("5. Унікальні марки (set) та підрахунок кількості (Counter)")
    print("6. Групування автомобілів за марками (defaultdict)")
    print("7. Загальна аналітика (середня ціна, екстремуми, кортеж діапазону)")
    print("8. Сортування за ціною (lambda)")
    print("9. Фільтрація за діапазоном цін (closure)")
    print("10. Демонстрація функцій *args та **kwargs")
    print("11. Історія останніх операцій (deque)")
    print("12. Запуск експериментального бенчмарку (1k, 10k, 100k)")
    print("13. Вивести повну демонстрацію всіх функцій")
    print("14. Вихід")

def run_menu(cars: list[Car]) -> None:
    history: deque[str] = deque(maxlen=10)
    car_index = create_car_index(cars)

    while True:
        print_menu()
        cmd = input("Оберіть команду (1-14): ").strip()
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
            print("Роботу завершено. До побачення!")
            break
        else:
            print("Невідома команда. Спробуйте ще раз.")

def main() -> None:
    cars = list(DEMO_CARS)
    if "--demo" in sys.argv:
        run_demo(cars)
    elif "--benchmark" in sys.argv:
        run_benchmark()
    else:
        run_menu(cars)

if __name__ == "__main__":
    main()
