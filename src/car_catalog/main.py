from car_catalog.models import Car
from car_catalog.services import (
    search_by_brand, filter_by_year, find_most_expensive_car,
    calculate_average_price, find_lowest_mileage_car
)

def create_demo_cars() -> list[Car]:
    return [
        Car(brand="Audi", model="A6 C5", year=2003, price=4500.0, mileage=350000.0),
        Car(brand="Toyota", model="Camry", year=2021, price=28000.0, mileage=45000.0),
        Car(brand="BMW", model="X5", year=2019, price=45000.0, mileage=120000.0),
        Car(brand="Ford", model="Focus", year=2015, price=10000.0, mileage=150000.0)
    ]

def print_menu() -> None:
    print("\n--- Каталог автомобілів ---")
    print("1. Показати всі авто")
    print("2. Пошук за маркою")
    print("3. Фільтр за роком")
    print("4. Найдорожче авто")
    print("5. Середня ціна")
    print("6. Найменший пробіг")
    print("7. Вихід")

def run_menu(cars: list[Car]) -> None:
    while True:
        print_menu()
        cmd = input("Оберіть команду: ").strip()
        
        if cmd == "1":
            for c in cars:
                print(f"{c.full_name:15} | {c.year:4} | {c.price:8.2f}$ | {c.mileage:8.1f} км")
        elif cmd == "2":
            brand = input("Введіть марку: ")
            res = search_by_brand(cars, brand)
            if res:
                for c in res:
                    print(f"{c.full_name} - {c.price}$")
            else:
                print("Авто такої марки не знайдено.")
        elif cmd == "3":
            try:
                year = int(input("Введіть рік: "))
                res = filter_by_year(cars, year)
                if res:
                    for c in res:
                        print(f"{c.full_name} - {c.year}")
                else:
                    print("Авто такого року не знайдено.")
            except ValueError:
                print("Помилка: введіть числове значення року.")
        elif cmd == "4":
            best = find_most_expensive_car(cars)
            if best:
                print(f"Найдорожче авто: {best.full_name} ({best.price}$)")
        elif cmd == "5":
            print(f"Середня ціна всіх авто: {calculate_average_price(cars):.2f}$")
        elif cmd == "6":
            best = find_lowest_mileage_car(cars)
            if best:
                print(f"Авто з найменшим пробігом: {best.full_name} ({best.mileage} км)")
        elif cmd == "7":
            print("До побачення!")
            break
        else:
            print("Невідома команда.")

def main() -> None:
    run_menu(create_demo_cars())

if __name__ == "__main__":
    main()