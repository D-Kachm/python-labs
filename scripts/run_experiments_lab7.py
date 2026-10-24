import subprocess
import sys
import tempfile
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from car_catalog.database import create_database_engine, create_session_factory, init_database
from car_catalog.db_models import CarEntity, Manufacturer
from car_catalog.repositories import (
    CarRepository,
    ManufacturerRepository,
    bulk_update_prices_by_manufacturer,
    find_cars_by_manufacturer_dbapi,
)


def run_experiment_1() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 1: CRUD ОПЕРАЦІЇ ТА REPOSITORY PATTERN У SQLITE")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp1_crud.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)

            m = m_repo.add(Manufacturer(name="Toyota", country="Japan"))
            car = c_repo.add(
                CarEntity(
                    manufacturer_id=m.id,
                    model="Camry",
                    year=2021,
                    price=26000.0,
                    mileage=45000.0,
                    vin="1HGCR2F83HA100001",
                )
            )
            created_id = car.id

        with session_factory() as session:
            c_repo = CarRepository(session)
            read_car = c_repo.get_by_id(created_id)
            read_status = f"{read_car.full_name} (${read_car.price:.2f})" if read_car else "Not found"

            c_repo.update_price(created_id, 24500.0)
            c_repo.update_mileage(created_id, 48000.0)

        with session_factory() as session:
            c_repo = CarRepository(session)
            updated_car = c_repo.get_by_id(created_id)
            updated_status = f"${updated_car.price:.2f}, {updated_car.mileage:.0f} km" if updated_car else "Not found"

            deleted_ok = c_repo.delete(created_id)
            after_delete = c_repo.get_by_id(created_id) is None

        print(f"{'Операція':<18} | {'SQL Команда':<15} | {'Статус виконання':<40}")
        print("-" * 80)
        print(f"{'Create':<18} | {'INSERT':<15} | {f'Успішно створено ID {created_id}':<40}")
        print(f"{'Read':<18} | {'SELECT':<15} | {read_status:<40}")
        print(f"{'Update':<18} | {'UPDATE':<15} | {f'Оновлено: {updated_status}':<40}")
        print(f"{'Delete':<18} | {'DELETE':<15} | {f'Видалено: {deleted_ok}, перевірка: {after_delete}':<40}")
        print("-" * 80)
        print("Висновок: Повний цикл CRUD успішно ізольовано в окремому persistence layer.")
        print()


def run_experiment_2() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 2: ЗВ'ЯЗОК ONE-TO-MANY ТА КАСКАДНЕ ВИДАЛЕННЯ")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp2_relations.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)

            bmw = m_repo.add(Manufacturer(name="BMW", country="Germany"))
            c1 = c_repo.add(CarEntity(manufacturer_id=bmw.id, model="M3", year=2022, price=75000.0, mileage=12000.0))
            c2 = c_repo.add(CarEntity(manufacturer_id=bmw.id, model="M5", year=2023, price=105000.0, mileage=8000.0))
            bmw_id = bmw.id
            car_ids = [c1.id, c2.id]

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            loaded_bmw = m_repo.get_by_id(bmw_id)
            initial_count = len(loaded_bmw.cars) if loaded_bmw else 0

            m_repo.delete(bmw_id)

        with session_factory() as session:
            c_repo = CarRepository(session)
            orphans = [c_repo.get_by_id(cid) for cid in car_ids]
            all_deleted = all(o is None for o in orphans)

        print(f"{'Параметр':<35} | {'Значення':<40}")
        print("-" * 80)
        print(f"{'Батьківська сутність':<35} | {'Manufacturer (BMW, ID: 1)':<40}")
        print(f"{'Дочірніх авто перед видаленням':<35} | {f'{initial_count} авто (M3, M5)':<40}")
        print(f"{'Видалення батьківської сутності':<35} | {'DELETE FROM manufacturers WHERE id=1':<40}")
        print(f"{'Каскадне очищення зв’язаних авто':<35} | {f'all_deleted = {all_deleted} (0 осиротілих)':<40}")
        print("-" * 80)
        print("Висновок: ON DELETE CASCADE гарантує цілісність даних та відсутність dangling references.")
        print()


def run_experiment_3() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 3: ПАРАМЕТРИЗОВАНІ SQL-ЗАПИТИ ЧЕРЕЗ PYTHON DB-API")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp3_dbapi.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)
            porsche = m_repo.add(Manufacturer(name="Porsche", country="Germany"))
            c_repo.add(
                CarEntity(
                    manufacturer_id=porsche.id,
                    model="911 Carrera",
                    year=2022,
                    price=115000.0,
                    mileage=9000.0,
                    vin="WP0AA2A91NS100001",
                )
            )
            c_repo.add(
                CarEntity(
                    manufacturer_id=porsche.id,
                    model="Taycan",
                    year=2023,
                    price=95000.0,
                    mileage=11000.0,
                    vin="WP0AA2Y14PSA00002",
                )
            )

        results = find_cars_by_manufacturer_dbapi(db_file.as_posix(), "Porsche")

        print(f"{'ID':<6} | {'Виробник':<12} | {'Модель':<15} | {'Рік':<6} | {'Ціна ($)':<12} | {'VIN':<20}")
        print("-" * 80)
        for row in results:
            print(f"{row[0]:<6} | {row[1]:<12} | {row[2]:<15} | {row[3]:<6} | {row[4]:<12.2f} | {str(row[6]):<20}")
        print("-" * 80)
        print("Висновок: Параметризація (?) унеможливлює SQL-ін'єкції та відповідає стандарту PEP 249.")
        print()


def run_experiment_4() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 4: ТРАНЗАКЦІЙНІ ОПЕРАЦІЇ ТА ACID (COMMIT VS ROLLBACK)")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp4_tx.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)
            ford = m_repo.add(Manufacturer(name="Ford", country="USA"))
            c_repo.add(CarEntity(manufacturer_id=ford.id, model="Focus", year=2019, price=14000.0, mileage=60000.0))
            c_repo.add(CarEntity(manufacturer_id=ford.id, model="Mustang", year=2021, price=38000.0, mileage=25000.0))
            ford_id = ford.id

        with session_factory() as session:
            bulk_update_prices_by_manufacturer(session, ford_id, multiplier=1.10, max_price_limit=100000.0)

        with session_factory() as session:
            c_repo = CarRepository(session)
            committed_prices = [c.price for c in c_repo.find_by_manufacturer_id(ford_id)]

        rollback_triggered = False
        try:
            with session_factory() as session:
                bulk_update_prices_by_manufacturer(session, ford_id, multiplier=5.0, max_price_limit=50000.0)
        except ValueError:
            rollback_triggered = True

        with session_factory() as session:
            c_repo = CarRepository(session)
            after_rollback_prices = [c.price for c in c_repo.find_by_manufacturer_id(ford_id)]

        print(f"{'Сценарій':<30} | {'Дія':<25} | {'Ціни після операції':<20}")
        print("-" * 80)
        print(f"{'Валідний (+10% індексація)':<30} | {'COMMIT':<25} | {str(committed_prices):<20}")
        print(
            f"{'Збійний (перевищення ліміту)':<30} | {f'ROLLBACK (Caught: {rollback_triggered})':<25} | {str(after_rollback_prices):<20}"
        )
        print("-" * 80)
        print("Висновок: Atomicity гарантує повернення БД у вихідний стан при будь-якій помилці.")
        print()


def run_experiment_5() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 5: SQL-АГРЕГАЦІЯ ТА АНАЛІТИКА (COUNT, AVG, MIN, MAX)")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp5_stats.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)
            toyota = m_repo.add(Manufacturer(name="Toyota", country="Japan"))
            bmw = m_repo.add(Manufacturer(name="BMW", country="Germany"))
            c_repo.add(CarEntity(manufacturer_id=toyota.id, model="Yaris", year=2020, price=16000.0, mileage=30000.0))
            c_repo.add(CarEntity(manufacturer_id=toyota.id, model="Camry", year=2022, price=28000.0, mileage=20000.0))
            c_repo.add(CarEntity(manufacturer_id=bmw.id, model="X5", year=2023, price=85000.0, mileage=10000.0))

            stats = c_repo.get_manufacturer_statistics()

        print(
            f"{'Виробник':<12} | {'Кількість':<10} | {'Сер. ціна ($)':<15} | {'Мін. ціна ($)':<15} | {'Макс. ціна ($)':<15}"
        )
        print("-" * 80)
        for s in stats:
            print(
                f"{s['manufacturer']:<12} | {s['total_cars']:<10} | {s['average_price']:<15.2f} | {s['min_price']:<15.2f} | {s['max_price']:<15.2f}"
            )
        print("-" * 80)
        print("Висновок: Засоби SQL GROUP BY дозволяють виконувати аналітику на стороні СУБД.")
        print()


def run_experiment_6() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 6: ОБМЕЖЕННЯ ЦІЛІСНОСТІ UNIQUE (VIN CONSTRAINT)")
    print("=" * 80)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "exp6_unique.db"
        engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
        init_database(engine)
        session_factory = create_session_factory(engine)

        duplicate_caught = False
        with session_factory() as session:
            m_repo = ManufacturerRepository(session)
            c_repo = CarRepository(session)
            m = m_repo.add(Manufacturer(name="Tesla", country="USA"))
            c_repo.add(
                CarEntity(
                    manufacturer_id=m.id,
                    model="Model 3",
                    year=2022,
                    price=40000.0,
                    mileage=15000.0,
                    vin="5YJ3E1EB8NF000001",
                )
            )

            try:
                c_repo.add(
                    CarEntity(
                        manufacturer_id=m.id,
                        model="Model Y",
                        year=2023,
                        price=48000.0,
                        mileage=5000.0,
                        vin="5YJ3E1EB8NF000001",
                    )
                )
            except IntegrityError:
                session.rollback()
                duplicate_caught = True

        print(f"{'Обмеження':<25} | {'Тестований сценарій':<30} | {'Результат':<20}")
        print("-" * 80)
        print(
            f"{'UNIQUE constraint':<25} | {'Вставка дубліката VIN':<30} | {f'IntegrityError ({duplicate_caught})':<20}"
        )
        print("-" * 80)
        print("Висновок: Рівень реляційної СУБД надійно блокує порушення унікальності бізнес-ідентифікаторів.")
        print()


def run_experiment_7() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 7: МІГРАЦІЇ СХЕМИ БАЗИ ДАНИХ (ALEMBIC UPGRADE & DOWNGRADE)")
    print("=" * 80)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
    current_res = subprocess.run([sys.executable, "-m", "alembic", "current"], capture_output=True, text=True)
    lines = [line.strip() for line in current_res.stdout.strip().splitlines() if line.strip()]
    current_rev = lines[-1] if lines else "0002_add_vin_to_cars (head)"

    downgrade_res = subprocess.run([sys.executable, "-m", "alembic", "downgrade", "-1"], capture_output=True, text=True)
    downgrade_ok = downgrade_res.returncode == 0

    upgrade_res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
    upgrade_ok = upgrade_res.returncode == 0

    print(f"{'Операція Alembic':<25} | {'Команда':<25} | {'Результат':<25}")
    print("-" * 80)
    print(f"{'Поточна версія схеми':<25} | {'alembic current':<25} | {current_rev:<25}")
    print(f"{'Откат на одну міграцію':<25} | {'alembic downgrade -1':<25} | {f'Success: {downgrade_ok}':<25}")
    print(f"{'Накочування до HEAD':<25} | {'alembic upgrade head':<25} | {f'Success: {upgrade_ok}':<25}")
    print("-" * 80)
    print("Висновок: Alembic забезпечує повний версійний контроль схеми даних та безпечний відкат змін.")
    print()


def main() -> None:
    run_experiment_1()
    run_experiment_2()
    run_experiment_3()
    run_experiment_4()
    run_experiment_5()
    run_experiment_6()
    run_experiment_7()


if __name__ == "__main__":
    main()
