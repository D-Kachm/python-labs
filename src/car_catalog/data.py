from car_catalog.models import Car

DEMO_CARS: list[Car] = [
    Car(id=1, brand="Audi", model="A6 C5", year=2003, price=4500.0, mileage=350000.0),
    Car(id=2, brand="Toyota", model="Camry", year=2021, price=28000.0, mileage=45000.0),
    Car(id=3, brand="BMW", model="X5", year=2019, price=45000.0, mileage=120000.0),
    Car(id=4, brand="Ford", model="Focus", year=2015, price=10000.0, mileage=150000.0),
    Car(id=5, brand="BMW", model="M3", year=2022, price=75000.0, mileage=25000.0),
    Car(id=6, brand="Toyota", model="Corolla", year=2018, price=16500.0, mileage=95000.0),
    Car(id=7, brand="Audi", model="Q7", year=2020, price=52000.0, mileage=80000.0),
    Car(id=8, brand="Mercedes-Benz", model="E-Class", year=2017, price=29000.0, mileage=135000.0),
]


def generate_cars(count: int) -> list[Car]:
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
    cars: list[Car] = []
    num_models = len(brands_models)
    for i in range(1, count + 1):
        brand, model = brands_models[i % num_models]
        year = 2000 + (i % 24)
        price = 3000.0 + float((i * 37) % 80000)
        mileage = 5000.0 + float((i * 123) % 400000)
        cars.append(Car(id=i, brand=brand, model=f"{model}-{i}", year=year, price=price, mileage=mileage))
    return cars
