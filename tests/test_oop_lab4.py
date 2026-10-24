import unittest
from dataclasses import FrozenInstanceError
from car_catalog.abstractions import NoDiscount, PercentageDiscount
from car_catalog.comparisons import (
    ComposedVehicleProcessor,
    CsvVehicleProcessor,
    DecoupledService,
    TightlyCoupledService,
    VehicleFormatter,
    VehicleParser,
    VehicleValidator,
)
from car_catalog.criteria import (
    AndCriteria,
    BrandAndModelCriteria,
    BrandCriteria,
    ElectricOnlyCriteria,
    MaxMileageCriteria,
    ModelCriteria,
    OrCriteria,
    PriceRangeCriteria,
    YearRangeCriteria,
)
from car_catalog.dto import (
    VehiclePayload,
    vehicle_from_payload,
    vehicle_to_payload,
)
from car_catalog.models import Car, ElectricCar, Vehicle, VehicleCatalog
from car_catalog.notifiers import RecordingNotifier
from car_catalog.protocols import SearchCriteria
from car_catalog.repositories import InMemoryRepository, VehicleRepository
from car_catalog.services import CatalogService
from car_catalog.specifications import VehicleSpecification
from car_catalog.value_objects import Mileage, Money, VIN


class TestValueObjects(unittest.TestCase):
    def test_money_valid_operations(self) -> None:
        m1 = Money(100.0, "USD")
        m2 = Money(50.0, "USD")
        self.assertEqual((m1 + m2).amount, 150.0)
        self.assertEqual((m1 - m2).amount, 50.0)
        self.assertEqual((m1 * 2.5).amount, 250.0)
        self.assertTrue(m2 < m1)
        self.assertEqual(str(m1), "100.00 USD")

    def test_money_validation_and_immutability(self) -> None:
        with self.assertRaises(ValueError):
            Money(-10.0, "USD")
        m = Money(100.0, "USD")
        with self.assertRaises(FrozenInstanceError):
            m.amount = 200.0  # type: ignore[misc]

    def test_money_currency_mismatch(self) -> None:
        m_usd = Money(100.0, "USD")
        m_eur = Money(100.0, "EUR")
        with self.assertRaises(ValueError):
            _ = m_usd + m_eur

    def test_mileage_and_vin(self) -> None:
        mil1 = Mileage(10000.0, "km")
        mil2 = Mileage(5000.0, "km")
        self.assertEqual((mil1 + mil2).value, 15000.0)
        self.assertTrue(mil2 < mil1)
        self.assertEqual(str(mil1), "10000.0 km")

        with self.assertRaises(ValueError):
            Mileage(-1.0, "km")

        vin = VIN("1HGCR2F83HA123456")
        self.assertEqual(str(vin), "1HGCR2F83HA123456")

        with self.assertRaises(ValueError):
            VIN("12")


class TestDomainEntitiesAndInheritance(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = VehicleSpecification(
            engine_type="2.0L Turbo",
            transmission="Automatic",
            horsepower=250,
            fuel_type="Gasoline",
            body_type="Sedan",
        )
        self.car = Car(
            id=1,
            brand="Audi",
            model="A4",
            year=2021,
            price=30000.0,
            mileage=40000.0,
            specification=self.spec,
        )
        self.ev = ElectricCar(
            id=2,
            brand="Tesla",
            model="Model 3",
            year=2023,
            price=45000.0,
            mileage=15000.0,
            battery_capacity=75.0,
            range_km=500.0,
        )

    def test_car_properties_and_encapsulation(self) -> None:
        self.assertEqual(self.car.full_name, "Audi A4")
        self.assertEqual(self.car.age, 2026 - 2021)
        self.assertEqual(self.car.price_money, Money(30000.0, "USD"))
        self.assertEqual(self.car.mileage_vo, Mileage(40000.0, "km"))

        self.car.price = 28000.0
        self.assertEqual(self.car.price, 28000.0)

        with self.assertRaises(ValueError):
            self.car.price = -500.0

        with self.assertRaises(ValueError):
            self.car.mileage = -100.0

    def test_electric_car_inheritance_and_specifics(self) -> None:
        self.assertIsInstance(self.ev, Car)
        self.assertIsInstance(self.ev, Vehicle)
        self.assertEqual(self.ev.energy_consumption, 15.0)
        self.assertIn("battery_capacity", self.ev.to_dict())

        with self.assertRaises(ValueError):
            ElectricCar(3, "Nissan", "Leaf", 2020, 15000.0, 50000.0, battery_capacity=-40.0, range_km=250.0)

    def test_replace_methods(self) -> None:
        updated_car = self.car.replace(price=25000.0)
        self.assertEqual(updated_car.price, 25000.0)
        self.assertEqual(updated_car.id, self.car.id)

        updated_ev = self.ev.replace(range_km=520.0)
        self.assertEqual(updated_ev.range_km, 520.0)
        self.assertEqual(updated_ev.battery_capacity, 75.0)


class TestVehicleCatalogCollection(unittest.TestCase):
    def setUp(self) -> None:
        self.c1 = Car(1, "Toyota", "Corolla", 2018, 15000.0, 80000.0)
        self.c2 = Car(2, "Honda", "Civic", 2020, 20000.0, 50000.0)
        self.ev = ElectricCar(3, "Tesla", "Model Y", 2022, 50000.0, 20000.0, 75.0, 480.0)
        self.catalog = VehicleCatalog([self.c1, self.c2, self.ev])

    def test_dunder_methods(self) -> None:
        self.assertEqual(len(self.catalog), 3)
        self.assertEqual(self.catalog[0], self.c1)
        self.assertIn(self.c2, self.catalog)
        self.assertIn(1, self.catalog)
        self.assertNotIn(999, self.catalog)

        all_items = list(self.catalog)
        self.assertEqual(len(all_items), 3)

        c3 = Car(4, "Mazda", "3", 2019, 17000.0, 60000.0)
        cat2 = VehicleCatalog([c3])
        combined = self.catalog + cat2
        self.assertEqual(len(combined), 4)

    def test_analytics(self) -> None:
        self.assertEqual(self.catalog.average_price(), round((15000 + 20000 + 50000) / 3, 2))
        self.assertEqual(self.catalog.most_expensive(), self.ev)
        self.assertEqual(self.catalog.lowest_mileage(), self.ev)


class TestSearchCriteriaStrategy(unittest.TestCase):
    def setUp(self) -> None:
        self.car = Car(1, "BMW", "X5", 2022, 60000.0, 30000.0)
        self.ev = ElectricCar(2, "Tesla", "Model S", 2023, 90000.0, 10000.0, 100.0, 650.0)

    def test_criteria_matches(self) -> None:
        self.assertTrue(BrandCriteria("BMW").matches(self.car))
        self.assertFalse(BrandCriteria("Tesla").matches(self.car))

        self.assertTrue(ModelCriteria("X5").matches(self.car))
        self.assertTrue(BrandAndModelCriteria("BMW", "X5").matches(self.car))

        self.assertTrue(YearRangeCriteria(2021, 2023).matches(self.car))
        self.assertFalse(YearRangeCriteria(2023, 2024).matches(self.car))

        self.assertTrue(PriceRangeCriteria(50000.0, 70000.0).matches(self.car))
        self.assertTrue(MaxMileageCriteria(40000.0).matches(self.car))
        self.assertTrue(ElectricOnlyCriteria().matches(self.ev))
        self.assertFalse(ElectricOnlyCriteria().matches(self.car))

    def test_composite_criteria(self) -> None:
        and_crit = AndCriteria([BrandCriteria("BMW"), PriceRangeCriteria(50000.0, 70000.0)])
        self.assertTrue(and_crit.matches(self.car))

        or_crit = OrCriteria([BrandCriteria("Audi"), ElectricOnlyCriteria()])
        self.assertTrue(or_crit.matches(self.ev))
        self.assertFalse(or_crit.matches(self.car))

    def test_runtime_checkable_protocol(self) -> None:
        crit = BrandCriteria("BMW")
        self.assertIsInstance(crit, SearchCriteria)


class TestGenericRepositoryAndDI(unittest.TestCase):
    def test_repository_operations(self) -> None:
        repo: InMemoryRepository[Vehicle] = InMemoryRepository[Vehicle]()
        c1 = Car(1, "Ford", "Focus", 2017, 11000.0, 95000.0)
        c2 = Car(2, "Opel", "Astra", 2018, 12000.0, 85000.0)
        repo.add(c1)
        repo.add(c2)

        self.assertEqual(repo.count(), 2)
        self.assertEqual(repo.get(1), c1)
        self.assertIsNone(repo.get(999))
        self.assertEqual(len(repo.all()), 2)

        filtered = repo.filter(lambda v: v.price > 11500)
        self.assertEqual(filtered, [c2])

        self.assertTrue(repo.remove(1))
        self.assertFalse(repo.remove(1))
        self.assertEqual(repo.count(), 1)

    def test_catalog_service_with_dependency_injection(self) -> None:
        repo = VehicleRepository()
        notifier = RecordingNotifier()
        discount = PercentageDiscount(15.0)

        service = CatalogService(repository=repo, notifier=notifier, discount_policy=discount)

        c1 = Car(1, "Kia", "Sportage", 2021, 24000.0, 35000.0)
        res_add = service.add_vehicle(c1)
        self.assertTrue(res_add.success)
        self.assertEqual(len(notifier.messages), 1)

        res_dup = service.add_vehicle(c1)
        self.assertFalse(res_dup.success)

        res_checkout = service.checkout_vehicle(1, "buyer@domain.ua")
        self.assertTrue(res_checkout.success)
        self.assertIsNotNone(res_checkout.value)
        assert res_checkout.value is not None
        self.assertEqual(res_checkout.value.amount, 20400.0)
        self.assertEqual(len(notifier.messages), 2)


class TestDTOAndComparisons(unittest.TestCase):
    def test_dto_payload_conversion(self) -> None:
        payload: VehiclePayload = {
            "id": 10,
            "brand": "Skoda",
            "model": "Octavia",
            "year": 2020,
            "price": 18500.0,
            "mileage": 60000.0,
            "horsepower": 150,
            "body_type": "Wagon",
        }
        car = vehicle_from_payload(payload)
        self.assertEqual(car.full_name, "Skoda Octavia")
        self.assertIsNotNone(car.specification)
        assert car.specification is not None
        self.assertEqual(car.specification.horsepower, 150)

        converted_payload = vehicle_to_payload(car)
        self.assertEqual(converted_payload["id"], 10)
        self.assertEqual(converted_payload["body_type"], "Wagon")

    def test_comparisons_and_architectures(self) -> None:
        # Section 72
        tight = TightlyCoupledService()
        loose = DecoupledService(VehicleRepository(), RecordingNotifier(), NoDiscount())
        car = Car(1, "Seat", "Leon", 2019, 14000.0, 70000.0)
        tight.register_car(car)
        loose.register_car(car)

        # Section 73
        line = "5,Renault,Megane,2018,12500.0,90000.0"
        inh_proc = CsvVehicleProcessor()
        comp_proc = ComposedVehicleProcessor(VehicleParser(), VehicleValidator(), VehicleFormatter())

        res1 = inh_proc.process(line)
        res2 = comp_proc.process_lines([line])
        self.assertEqual(res1[0].full_name, res2[0].full_name)
        self.assertEqual(res1[0].price, res2[0].price)


if __name__ == "__main__":
    unittest.main()
