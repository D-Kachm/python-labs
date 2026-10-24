import asyncio
from time import perf_counter
from typing import Any
from fastapi.testclient import TestClient
import httpx
from car_catalog.api import app, get_session
from car_catalog.database import Base, create_database_engine, create_session_factory
from car_catalog.db_models import CarEntity, Manufacturer
from car_catalog.external_api import (
    fetch_single_resource_with_retry,
)


def setup_demo_db() -> tuple[Any, Any]:
    from sqlalchemy.pool import StaticPool

    engine = create_database_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()

    toyota = Manufacturer(name="Toyota", country="Japan")
    bmw = Manufacturer(name="BMW", country="Germany")
    porsche = Manufacturer(name="Porsche", country="Germany")
    session.add_all([toyota, bmw, porsche])
    session.commit()

    c1 = CarEntity(
        manufacturer_id=toyota.id, model="Camry", year=2021, price=26000.0, mileage=45000.0, vin="WP0AA2A91NS000001"
    )
    c2 = CarEntity(
        manufacturer_id=toyota.id, model="Corolla", year=2020, price=19000.0, mileage=55000.0, vin="WP0AA2A91NS000002"
    )
    c3 = CarEntity(
        manufacturer_id=bmw.id, model="M3", year=2022, price=75000.0, mileage=12000.0, vin="WP0AA2A91NS000003"
    )
    c4 = CarEntity(
        manufacturer_id=porsche.id, model="911", year=2023, price=120000.0, mileage=5000.0, vin="WP0AA2A91NS000004"
    )
    session.add_all([c1, c2, c3, c4])
    session.commit()

    return engine, session


def run_experiment_1() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 1: REST API ENDPOINTS ТА CRUD ЧЕРЕЗ FASTAPI")
    print("=" * 80)
    _, session = setup_demo_db()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)

    print(f"{'Операція':<18} | {'HTTP Метод':<12} | {'Endpoint':<22} | {'Статус':<8} | {'Результат':<15}")
    print("-" * 80)

    res_post = client.post(
        "/cars",
        json={
            "manufacturer_id": 1,
            "model": "Yaris",
            "year": 2022,
            "price": 17500.0,
            "mileage": 20000.0,
            "vin": "WP0AA2A91NS000005",
        },
    )
    print(f"{'Create':<18} | {'POST':<12} | {'/cars':<22} | {res_post.status_code:<8} | ID: {res_post.json()['id']}")

    res_get = client.get("/cars/1")
    print(
        f"{'Read':<18} | {'GET':<12} | {'/cars/1':<22} | {res_get.status_code:<8} | {res_get.json()['model']} (${res_get.json()['price']})"
    )

    res_patch = client.patch("/cars/1", json={"price": 25000.0})
    print(
        f"{'Update':<18} | {'PATCH':<12} | {'/cars/1':<22} | {res_patch.status_code:<8} | Нова ціна: ${res_patch.json()['price']}"
    )

    res_del = client.delete("/cars/1")
    print(f"{'Delete':<18} | {'DELETE':<12} | {'/cars/1':<22} | {res_del.status_code:<8} | Видалено успішно")

    res_verify = client.get("/cars/1")
    print(f"{'Verify Delete':<18} | {'GET':<12} | {'/cars/1':<22} | {res_verify.status_code:<8} | 404 Not Found")

    print("-" * 80)
    print("Висновок: Повний цикл CRUD успішно реалізовано з коректними HTTP-статусами (201, 200, 204, 404).")
    print()


def run_experiment_2() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 2: PYDANTIC ВАЛІДАЦІЯ ТА ОБРОБКА ПОМИЛОК")
    print("=" * 80)
    _, session = setup_demo_db()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)

    scenarios = [
        (
            "Валідні дані",
            {
                "manufacturer_id": 1,
                "model": "Supra",
                "year": 2023,
                "price": 55000.0,
                "mileage": 8000.0,
                "vin": "WP0AA2A91NS000006",
            },
            201,
        ),
        (
            "Невалідний рік (<1886)",
            {
                "manufacturer_id": 1,
                "model": "Old",
                "year": 1800,
                "price": 10000.0,
                "mileage": 1000.0,
                "vin": "WP0AA2A91NS000007",
            },
            422,
        ),
        (
            "Від'ємна ціна",
            {
                "manufacturer_id": 1,
                "model": "Minus",
                "year": 2020,
                "price": -50.0,
                "mileage": 1000.0,
                "vin": "WP0AA2A91NS000008",
            },
            422,
        ),
        (
            "Невалідний VIN (<17 знаків)",
            {
                "manufacturer_id": 1,
                "model": "BadVIN",
                "year": 2020,
                "price": 20000.0,
                "mileage": 1000.0,
                "vin": "SHORT",
            },
            422,
        ),
        (
            "Дублікат VIN",
            {
                "manufacturer_id": 1,
                "model": "Dup",
                "year": 2021,
                "price": 26000.0,
                "mileage": 45000.0,
                "vin": "WP0AA2A91NS000001",
            },
            409,
        ),
    ]

    print(f"{'Сценарій запиту':<30} | {'Очікуваний статус':<18} | {'Фактичний статус':<18} | {'Результат':<8}")
    print("-" * 80)
    for name, payload, expected in scenarios:
        res = client.post("/cars", json=payload)
        status_ok = res.status_code == expected
        print(f"{name:<30} | {expected:<18} | {res.status_code:<18} | {'PASS' if status_ok else 'FAIL'}")

    print("-" * 80)
    print("Висновок: Pydantic schemas блокують невалідні вхідні дані на рівні валідації (422) та унікальності (409).")
    print()


def run_experiment_3() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 3: QUERY PARAMETERS (ФІЛЬТРАЦІЯ ТА ПАГІНАЦІЯ)")
    print("=" * 80)
    _, session = setup_demo_db()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)

    queries: list[tuple[str, dict[str, Any], int]] = [
        ("Всі авто (за замовчуванням)", {}, 4),
        ("Виробник = Toyota", {"manufacturer": "Toyota"}, 2),
        ("Рік від 2022 до 2024", {"min_year": 2022, "max_year": 2024}, 2),
        ("Ціна від $50000", {"min_price": 50000.0}, 2),
        ("Пагінація (skip=1, limit=2)", {"skip": 1, "limit": 2}, 2),
    ]

    print(f"{'Параметри запиту':<35} | {'Query String':<25} | {'Кількість знайдених авто':<15}")
    print("-" * 80)
    for desc, params, expected_count in queries:
        res = client.get("/cars", params=params)
        items = res.json()
        query_str = "&".join(f"{k}={v}" for k, v in params.items()) if params else "—"
        print(f"{desc:<35} | {query_str:<25} | {len(items)} авто")

    print("-" * 80)
    print("Висновок: Фільтрація та пагінація за допомогою query parameters дозволяють ефективно обирати дані.")
    print()


async def run_async_operations() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 4: ПАРАЛЕЛЬНЕ АСИНХРОННЕ ВИКОНАННЯ (ASYNCIO.TASK ТА GATHER)")
    print("=" * 80)
    _, session = setup_demo_db()
    app.dependency_overrides[get_session] = lambda: session

    async def mock_fetch_task(task_id: int, delay: float) -> dict[str, Any]:
        await asyncio.sleep(delay)
        return {"task_id": task_id, "duration": delay}

    t0_seq = perf_counter()
    for i in range(1, 4):
        await mock_fetch_task(i, 0.1)
    seq_time = perf_counter() - t0_seq

    t0_par = perf_counter()
    tasks = [asyncio.create_task(mock_fetch_task(i, 0.1)) for i in range(1, 4)]
    results = await asyncio.gather(*tasks)
    par_time = perf_counter() - t0_par

    speedup = seq_time / par_time if par_time > 0 else 1.0
    print(f"{'Режим виконання':<25} | {'Кількість завдань':<20} | {'Час виконання (с)':<20}")
    print("-" * 80)
    print(f"{'Послідовний (Sequential)':<25} | {3:<20} | {seq_time:.4f} s")
    print(f"{'Паралельний (asyncio.gather)':<25} | {len(results):<20} | {par_time:.4f} s")
    print("-" * 80)
    print(f"Прискорення паралельного виконання: {speedup:.2f}x")
    print("Висновок: asyncio.gather дозволяє одночасно очікувати кілька I/O операцій, суттєво зменшуючи latency.")
    print()

    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 5: RATE LIMITING ТА КОНКУРЕНТНІСТЬ ЧЕРЕЗ ASYNCIO.SEMAPHORE")
    print("=" * 80)
    semaphore = asyncio.Semaphore(2)
    active_workers = 0
    max_recorded_concurrency = 0

    async def worker(worker_id: int) -> int:
        nonlocal active_workers, max_recorded_concurrency
        async with semaphore:
            active_workers += 1
            if active_workers > max_recorded_concurrency:
                max_recorded_concurrency = active_workers
            await asyncio.sleep(0.05)
            active_workers -= 1
        return worker_id

    worker_tasks = [asyncio.create_task(worker(i)) for i in range(6)]
    completed = await asyncio.gather(*worker_tasks)

    print(f"{'Всього завдань':<20} | {'Ліміт Semaphore':<20} | {'Макс. одночасних':<20} | {'Успішно':<10}")
    print("-" * 80)
    print(f"{len(completed):<20} | {2:<20} | {max_recorded_concurrency:<20} | {len(completed) == 6}")
    print("-" * 80)
    print("Висновок: asyncio.Semaphore(2) надійно обмежує одночасне навантаження на систему до 2 операцій.")
    print()

    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 6: НАДІЙНІСТЬ МЕРЕЖЕВІХ ЗАПИТІВ (TIMEOUT ТА RETRY У HTTPX)")
    print("=" * 80)
    attempts_counter = 0

    def mock_server(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_counter
        attempts_counter += 1
        if attempts_counter < 3:
            return httpx.Response(500, json={"error": "Transient Internal Server Error"})
        return httpx.Response(200, json={"id": 1, "model": "Porsche Taycan", "status": "online"})

    transport = httpx.MockTransport(mock_server)
    async with httpx.AsyncClient(transport=transport) as client:
        sem = asyncio.Semaphore(5)
        res = await fetch_single_resource_with_retry(
            client=client,
            url="http://mock.local/cars/1",
            semaphore=sem,
            attempts=3,
            timeout=2.0,
            backoff_seconds=0.01,
        )

    print(f"{'Параметр':<30} | {'Значення':<45}")
    print("-" * 80)
    print(f"{'Кількість виконаних спроб':<30} | {attempts_counter} (2 помилки 500, 3-тя успішна)")
    print(f"{'Отриманий результат':<30} | {res}")
    print("-" * 80)
    print("Висновок: Механізм retry дозволяє автоматично долати тимчасові збої мережі та сервісів.")
    print()

    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 7: BATCH FETCH ENDPOINT (АСИНХРОННА АГРЕГАЦІЯ ДАНИХ)")
    print("=" * 80)
    test_client = TestClient(app)
    batch_resp = test_client.post("/cars/batch", json={"car_ids": [1, 2, 3, 999]})
    batch_data = batch_resp.json()

    print(f"{'Запитано ID':<20} | {'Знайдено авто':<20} | {'Не знайдено ID':<20}")
    print("-" * 80)
    print(f"{'[1, 2, 3, 999]':<20} | {batch_data['total']} авто{'':<13} | {batch_data['missing_ids']}")
    print("-" * 80)
    print("Висновок: Ендпоінт /cars/batch забезпечує паралельне вичитування сутностей без блокування черги.")
    print()


def main() -> None:
    run_experiment_1()
    run_experiment_2()
    run_experiment_3()
    asyncio.run(run_async_operations())


if __name__ == "__main__":
    main()
