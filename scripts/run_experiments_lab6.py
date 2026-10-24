import random
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from car_catalog.abstractions import PercentageDiscount
from car_catalog.models import Car
from car_catalog.protocols import ExternalVehicleInfoService, VehicleNotifier
from car_catalog.repositories import VehicleRepository
from car_catalog.services import CatalogService, VehicleEnrichmentService
from car_catalog.value_objects import Money

def run_experiment_1() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 1: WEAK VS STRONG TESTS (EXECUTION != VERIFICATION)")
    print("=" * 80)

    class BuggyDiscount:
        def __init__(self, percent: float) -> None:
            self.percent = percent

        def apply(self, price: float) -> float:
            return price + (price * self.percent / 100.0)

    buggy = BuggyDiscount(10.0)

    def weak_test() -> bool:
        try:
            _ = buggy.apply(100.0)
            return True
        except Exception:
            return False

    def strong_test() -> bool:
        try:
            result = buggy.apply(100.0)
            assert result == 90.0
            return True
        except AssertionError:
            return False

    weak_res = "PASSED (Silent Failure!)" if weak_test() else "FAILED"
    strong_res = "PASSED" if strong_test() else "FAILED (Defect caught!)"

    print(f"{'Тип тесту':<25} | {'Результат виконання':<30} | {'Висновок':<20}")
    print("-" * 80)
    print(f"{'Weak test (без assert)':<25} | {weak_res:<30} | {'Помилку не виявлено':<20}")
    print(f"{'Strong test (з assert)':<25} | {strong_res:<30} | {'Дефект зафіксовано':<20}")
    print("-" * 80)
    print("Висновок: Execution != Verification. Виконання рядка без перевірки не доводить правильність.")
    print()

def run_experiment_2() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 2: COVERAGE БЕЗ ASSERTIONS")
    print("=" * 80)

    def calculate_tax(price: float) -> float:
        tax_rate = 0.20
        calculated = price * tax_rate
        return 0.0

    statements = 3
    executed_statements = 3
    coverage_pct = (executed_statements / statements) * 100

    def test_without_assert() -> bool:
        _ = calculate_tax(100.0)
        return True

    def test_with_assert() -> bool:
        try:
            val = calculate_tax(100.0)
            assert val == 20.0
            return True
        except AssertionError:
            return False

    print(f"{'Метрика / Тест':<30} | {'Покриття коду (Coverage)':<25} | {'Виявлення багу':<18}")
    print("-" * 80)
    print(f"{'Тест без assert':<30} | {f'{coverage_pct:.1f}% Statement Coverage':<25} | {'НЕ виявлено (False Positive)':<18}")
    print(f"{'Тест із валідним assert':<30} | {f'{coverage_pct:.1f}% Statement Coverage':<25} | {'ВИЯВЛЕНО (AssertionError)':<18}")
    print("-" * 80)
    print("Висновок: 100% coverage не гарантує відсутність помилок. Змістовні assertions критично важливі.")
    print()

def run_experiment_3() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 3: STATEMENT COVERAGE VS BRANCH COVERAGE")
    print("=" * 80)

    def classify_car_price(price: float) -> str:
        if price >= 50000.0:
            return "premium"
        if price >= 20000.0:
            return "medium"
        return "budget"

    suite_1_inputs = [60000.0, 30000.0]
    suite_2_inputs = [60000.0, 30000.0, 10000.0]

    s1_branches = "2 із 3 гілок (66.7%)"
    s1_stmts = "4 із 5 рядків (80.0%)"

    s2_branches = "3 із 3 гілок (100.0%)"
    s2_stmts = "5 із 5 рядків (100.0%)"

    print(f"{'Набір тестів':<20} | {'Вхідні дані':<24} | {'Statement Coverage':<20} | {'Branch Coverage':<20}")
    print("-" * 90)
    print(f"{'Частковий suite':<20} | {str(suite_1_inputs):<24} | {s1_stmts:<20} | {s1_branches:<20}")
    print(f"{'Повний suite':<20} | {str(suite_2_inputs):<24} | {s2_stmts:<20} | {s2_branches:<20}")
    print("-" * 90)
    print("Висновок: Statement coverage не фіксує пропуск альтернативних гілок розгалуження (if/else).")
    print()

def run_experiment_4() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 4: MOCK VS FAKE REPOSITORY")
    print("=" * 80)

    car = Car(1, "Toyota", "Camry", 2021, 26000.0, 45000.0)

    class FakeRepository:
        def __init__(self) -> None:
            self.items: dict[int, Car] = {}

        def add(self, item: Car) -> None:
            self.items[item.id] = item

        def get(self, item_id: int) -> Car | None:
            return self.items.get(item_id)

    fake_repo = FakeRepository()
    fake_repo.add(car)
    state_verified = fake_repo.get(1) == car

    mock_notifier = Mock(spec=VehicleNotifier)
    service = CatalogService(VehicleRepository(), mock_notifier, PercentageDiscount(10.0))
    service.add_vehicle(car)
    interaction_verified = mock_notifier.send.called

    print(f"{'Підхід':<20} | {'Що перевіряється':<30} | {'Зчеплення (Coupling)':<25}")
    print("-" * 80)
    print(f"{'Fake Repository':<20} | {'State testing (стан пам’яті)':<30} | {'Низьке (перевірка контракту)':<25}")
    print(f"{'Mock Notifier':<20} | {'Interaction testing (виклик)':<30} | {'Тісне з інтерфейсом виклику':<25}")
    print("-" * 80)
    print(f"Результат Fake: {state_verified} | Результат Mock: {interaction_verified}")
    print("Висновок: Fake краще для збереження стану, Mock — для зовнішніх сайд-ефектів (нотифікацій/API).")
    print()

def run_experiment_5() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 5: FLAKY TEST VS DETERMINISTIC TEST")
    print("=" * 80)

    def flaky_operation() -> bool:
        return random.random() > 0.4

    flaky_runs = [flaky_operation() for _ in range(10)]
    flaky_passed = sum(1 for r in flaky_runs if r)

    def deterministic_operation(value_generator: float) -> bool:
        return value_generator > 0.4

    det_runs = [deterministic_operation(0.8) for _ in range(10)]
    det_passed = sum(1 for r in det_runs if r)

    print(f"{'Тип тесту':<25} | {'Кількість запусків':<20} | {'Passed':<12} | {'Стабільність':<15}")
    print("-" * 80)
    print(f"{'Flaky (random/time)':<25} | {'10':<20} | {f'{flaky_passed}/10':<12} | {'Нестабільний':<15}")
    print(f"{'Deterministic (mocked)':<25} | {'10':<20} | {f'{det_passed}/10':<12} | {'100% повторюваний':<15}")
    print("-" * 80)
    print("Висновок: Flaky tests руйнують довіру до CI. Залежності від часу/рандому повинні бути детерміновані.")
    print()

def run_experiment_6() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 6: TMP_PATH ISOLATION")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmp_dir_1:
        p1 = Path(tmp_dir_1) / "test_artifact.json"
        p1.write_text('{"run": 1}', encoding="utf-8")
        exists_during_1 = p1.exists()

    exists_after_1 = p1.exists()

    with tempfile.TemporaryDirectory() as tmp_dir_2:
        p2 = Path(tmp_dir_2) / "test_artifact.json"
        p2.write_text('{"run": 2}', encoding="utf-8")
        exists_during_2 = p2.exists()

    exists_after_2 = p2.exists()

    print(f"{'Ізольоване середовище':<25} | {'Під час виконання':<22} | {'Після завершення (Cleanup)':<25}")
    print("-" * 80)
    print(f"{'Run 1 (tmp_path 1)':<25} | {f'Exists: {exists_during_1}':<22} | {f'Exists: {exists_after_1} (Cleaned)':<25}")
    print(f"{'Run 2 (tmp_path 2)':<25} | {f'Exists: {exists_during_2}':<22} | {f'Exists: {exists_after_2} (Cleaned)':<25}")
    print("-" * 80)
    print("Висновок: tmp_path гарантує hermetic environment: відсутність конфліктів та сміття в робочій директорії.")
    print()

def run_experiment_7() -> None:
    print("=" * 80)
    print("ЕКСПЕРИМЕНТ 7: FAILURE PATH TESTING ТА ABSENCE OF UNWANTED INTERACTIONS")
    print("=" * 80)

    external_mock = Mock(spec=ExternalVehicleInfoService)
    external_mock.fetch_vehicle_specs.side_effect = ConnectionError("Connection refused by vendor")
    enrichment = VehicleEnrichmentService(external_mock)

    notifier_mock = Mock(spec=VehicleNotifier)

    failure_caught = False
    try:
        enrichment.enrich_specs("1HGCR2F83HA123456")
        notifier_mock.send("admin@cars.ua", "Specs enriched")
    except ConnectionError:
        failure_caught = True

    notifier_called = notifier_mock.send.called

    print(f"{'Сценарій':<25} | {'Зовнішній виклик':<25} | {'Exception спіймано':<20} | {'Unwanted Call':<15}")
    print("-" * 90)
    print(f"{'Збій зовнішнього API':<25} | {'ConnectionError raised':<25} | {f'{failure_caught}':<20} | {f'Notifier called: {notifier_called}':<15}")
    print("-" * 90)
    print("Висновок: Failure path тестує не лише генерацію винятку, а й відсутність небажаних сайд-ефектів.")
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
