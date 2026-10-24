import asyncio
from typing import Any
import httpx
import pytest
from fastapi.testclient import TestClient
from car_catalog.external_api import (
    fetch_resources_concurrently,
    fetch_single_resource_with_retry,
)


def test_api_root(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "1.0.0"
    assert "message" in payload


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] in {"development", "production", "test", "staging"}


def test_get_cars_all(api_client: TestClient) -> None:
    response = api_client.get("/cars")
    assert response.status_code == 200
    cars = response.json()
    assert len(cars) >= 4
    assert cars[0]["model"] in {"Camry", "Corolla", "M3", "Model 3"}


def test_get_cars_filter_by_manufacturer(api_client: TestClient) -> None:
    response = api_client.get("/cars", params={"manufacturer": "Toyota"})
    assert response.status_code == 200
    cars = response.json()
    assert len(cars) == 2
    assert all(c["manufacturer"]["name"] == "Toyota" for c in cars)


def test_get_cars_filter_by_year_and_price(api_client: TestClient) -> None:
    response = api_client.get(
        "/cars",
        params={"min_year": 2021, "max_year": 2023, "min_price": 25000.0, "max_price": 50000.0},
    )
    assert response.status_code == 200
    cars = response.json()
    assert len(cars) >= 2
    for car in cars:
        assert 2021 <= car["year"] <= 2023
        assert 25000.0 <= car["price"] <= 50000.0


def test_get_car_by_id_success(api_client: TestClient) -> None:
    response = api_client.get("/cars/1")
    assert response.status_code == 200
    car = response.json()
    assert car["id"] == 1
    assert car["model"] == "Camry"
    assert car["manufacturer"]["name"] == "Toyota"


def test_get_car_by_id_not_found(api_client: TestClient) -> None:
    response = api_client.get("/cars/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_car_success(api_client: TestClient) -> None:
    payload = {
        "manufacturer_id": 1,
        "model": "RAV4",
        "year": 2023,
        "price": 32000.0,
        "mileage": 10000.0,
        "vin": "2T3F1REV8MW000099",
    }
    response = api_client.post("/cars", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["id"] is not None
    assert created["model"] == "RAV4"
    assert created["vin"] == "2T3F1REV8MW000099"


def test_create_car_validation_error(api_client: TestClient) -> None:
    payload = {
        "manufacturer_id": 1,
        "model": "",
        "year": 1800,
        "price": -500.0,
        "mileage": -100.0,
        "vin": "SHORT_VIN",
    }
    response = api_client.post("/cars", json=payload)
    assert response.status_code == 422


def test_create_car_invalid_manufacturer(api_client: TestClient) -> None:
    payload = {
        "manufacturer_id": 99999,
        "model": "Ghost",
        "year": 2023,
        "price": 350000.0,
        "mileage": 1000.0,
        "vin": "SCA664S59EU000001",
    }
    response = api_client.post("/cars", json=payload)
    assert response.status_code == 404


def test_create_car_duplicate_vin(api_client: TestClient) -> None:
    payload = {
        "manufacturer_id": 1,
        "model": "Yaris",
        "year": 2020,
        "price": 15000.0,
        "mileage": 60000.0,
        "vin": "1HGCR2F83HA000001",
    }
    response = api_client.post("/cars", json=payload)
    assert response.status_code == 409


def test_patch_car_success(api_client: TestClient) -> None:
    update_data = {"price": 24000.0, "mileage": 49000.0}
    response = api_client.patch("/cars/1", json=update_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["price"] == 24000.0
    assert updated["mileage"] == 49000.0


def test_patch_car_not_found(api_client: TestClient) -> None:
    response = api_client.patch("/cars/99999", json={"price": 30000.0})
    assert response.status_code == 404


def test_delete_car_success(api_client: TestClient) -> None:
    response = api_client.delete("/cars/1")
    assert response.status_code == 204
    check = api_client.get("/cars/1")
    assert check.status_code == 404


def test_delete_car_not_found(api_client: TestClient) -> None:
    response = api_client.delete("/cars/99999")
    assert response.status_code == 404


def test_get_manufacturers_and_create(api_client: TestClient) -> None:
    response = api_client.get("/manufacturers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

    create_resp = api_client.post(
        "/manufacturers",
        json={"name": "Porsche", "country": "Germany"},
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    dup_resp = api_client.post(
        "/manufacturers",
        json={"name": "Porsche", "country": "Germany"},
    )
    assert dup_resp.status_code == 409

    get_one = api_client.get(f"/manufacturers/{created_id}")
    assert get_one.status_code == 200
    assert get_one.json()["name"] == "Porsche"


def test_get_cars_by_manufacturer_id(api_client: TestClient) -> None:
    response = api_client.get("/manufacturers/2/cars")
    assert response.status_code == 200
    cars = response.json()
    assert len(cars) == 1
    assert cars[0]["model"] == "M3"


def test_delete_manufacturer_cascade(api_client: TestClient) -> None:
    response = api_client.delete("/manufacturers/3")
    assert response.status_code == 204
    car_check = api_client.get("/cars/3")
    assert car_check.status_code == 404


def test_analytics_endpoints(api_client: TestClient) -> None:
    summary_resp = api_client.get("/cars/analytics/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_cars"] >= 1
    assert summary["average_price"] > 0
    assert summary["most_expensive_car"] is not None

    stats_resp = api_client.get("/manufacturers/analytics/statistics")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert len(stats) >= 1
    assert "average_price" in stats[0]


def test_batch_fetch_cars_endpoint(api_client: TestClient) -> None:
    response = api_client.post("/cars/batch", json={"car_ids": [2, 4, 99999]})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert 99999 in data["missing_ids"]
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_async_api_client_root(async_api_client: Any) -> None:
    response = await async_api_client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Car Catalog REST API is running"


@pytest.mark.asyncio
async def test_external_api_retry_and_semaphore() -> None:
    call_counts: dict[str, int] = {"url1": 0, "url2": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "url1" in url_str:
            call_counts["url1"] += 1
            if call_counts["url1"] < 3:
                return httpx.Response(500)
            return httpx.Response(200, json={"id": 101, "model": "AsyncCar"})
        call_counts["url2"] += 1
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        semaphore = asyncio.Semaphore(2)
        res1 = await fetch_single_resource_with_retry(
            client=client,
            url="http://mock.test/url1",
            semaphore=semaphore,
            attempts=3,
            backoff_seconds=0.01,
        )
        assert res1 is not None
        assert res1["id"] == 101
        assert call_counts["url1"] == 3

        success, failed = await fetch_resources_concurrently(
            urls=["http://mock.test/url1", "http://mock.test/url2"],
            max_concurrency=2,
            timeout=3.0,
            attempts=2,
            custom_client=client,
        )
        assert len(success) == 1
        assert len(failed) == 1
