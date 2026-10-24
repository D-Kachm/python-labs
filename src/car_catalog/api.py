import asyncio
from collections.abc import Generator
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from car_catalog.database import create_database_engine, create_session_factory
from car_catalog.db_models import CarEntity, Manufacturer
from car_catalog.external_api import fetch_resources_concurrently
from car_catalog.repositories import CarRepository, ManufacturerRepository
from car_catalog.schemas import (
    AnalyticsSummaryResponse,
    BatchFetchRequest,
    BatchFetchResponse,
    CarCreate,
    CarResponse,
    CarUpdate,
    ManufacturerCreate,
    ManufacturerResponse,
    ManufacturerStatisticsResponse,
    RemoteBatchRequest,
    RemoteBatchResponse,
)

def get_session() -> Generator[Session, None, None]:
    engine = create_database_engine()
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()

app = FastAPI(
    title="Car Catalog REST API",
    description="High-performance asynchronous REST API for Car Catalog management",
    version="0.8.0",
)

@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": "Car Catalog REST API is running",
        "version": "0.8.0",
        "docs_url": "/docs",
    }

@app.get("/cars", response_model=list[CarResponse], tags=["Cars"])
async def get_cars(
    manufacturer: str | None = Query(default=None),
    min_year: int | None = Query(default=None, ge=1886),
    max_year: int | None = Query(default=None, le=2050),
    min_price: float | None = Query(default=None, ge=0.0),
    max_price: float | None = Query(default=None, ge=0.0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[CarEntity]:
    car_repo = CarRepository(session)
    if manufacturer is not None:
        cars = car_repo.find_by_manufacturer_name(manufacturer)
    elif min_year is not None and max_year is not None:
        cars = car_repo.filter_by_year_range(min_year, max_year)
    else:
        cars = car_repo.get_all()

    if min_price is not None:
        cars = [c for c in cars if c.price >= min_price]
    if max_price is not None:
        cars = [c for c in cars if c.price <= max_price]
    if min_year is not None and max_year is None:
        cars = [c for c in cars if c.year >= min_year]
    if max_year is not None and min_year is None:
        cars = [c for c in cars if c.year <= max_year]

    return cars[skip : skip + limit]

@app.get("/cars/analytics/summary", response_model=AnalyticsSummaryResponse, tags=["Analytics"])
async def get_cars_analytics(session: Session = Depends(get_session)) -> AnalyticsSummaryResponse:
    car_repo = CarRepository(session)
    all_cars = car_repo.get_all()
    if not all_cars:
        return AnalyticsSummaryResponse(total_cars=0, average_price=0.0)
    most_expensive = car_repo.get_most_expensive_car()
    lowest_mileage = car_repo.get_lowest_mileage_car()
    avg_price = car_repo.get_average_price()
    return AnalyticsSummaryResponse(
        total_cars=len(all_cars),
        average_price=round(avg_price, 2),
        most_expensive_car=CarResponse.model_validate(most_expensive) if most_expensive else None,
        lowest_mileage_car=CarResponse.model_validate(lowest_mileage) if lowest_mileage else None,
    )

@app.get("/cars/{car_id}", response_model=CarResponse, tags=["Cars"])
async def get_car(car_id: int, session: Session = Depends(get_session)) -> CarEntity:
    car_repo = CarRepository(session)
    car = car_repo.get_by_id(car_id)
    if car is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Car with ID {car_id} not found")
    return car

@app.post("/cars", response_model=CarResponse, status_code=status.HTTP_201_CREATED, tags=["Cars"])
async def create_car(data: CarCreate, session: Session = Depends(get_session)) -> CarEntity:
    manufacturer_repo = ManufacturerRepository(session)
    car_repo = CarRepository(session)
    manufacturer = manufacturer_repo.get_by_id(data.manufacturer_id)
    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with ID {data.manufacturer_id} not found",
        )
    car = CarEntity(
        manufacturer_id=data.manufacturer_id,
        model=data.model,
        year=data.year,
        price=data.price,
        mileage=data.mileage,
        vin=data.vin,
    )
    try:
        return car_repo.add(car)
    except IntegrityError as err:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Car with VIN '{data.vin}' already exists",
        ) from err

@app.patch("/cars/{car_id}", response_model=CarResponse, tags=["Cars"])
async def update_car(car_id: int, data: CarUpdate, session: Session = Depends(get_session)) -> CarEntity:
    car_repo = CarRepository(session)
    car = car_repo.get_by_id(car_id)
    if car is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Car with ID {car_id} not found")

    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        return car

    for key, value in update_dict.items():
        setattr(car, key, value)

    try:
        session.commit()
        session.refresh(car)
        return car
    except IntegrityError as err:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict updating car fields: duplicate unique key constraint",
        ) from err

@app.delete("/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Cars"])
async def delete_car(car_id: int, session: Session = Depends(get_session)) -> None:
    car_repo = CarRepository(session)
    deleted = car_repo.delete(car_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Car with ID {car_id} not found")

@app.post("/cars/batch", response_model=BatchFetchResponse, tags=["Cars"])
async def batch_fetch_cars(request: BatchFetchRequest, session: Session = Depends(get_session)) -> BatchFetchResponse:
    car_repo = CarRepository(session)
    semaphore = asyncio.Semaphore(10)

    async def get_car_task(car_id: int) -> tuple[int, CarEntity | None]:
        async with semaphore:
            return car_id, car_repo.get_by_id(car_id)

    tasks = [asyncio.create_task(get_car_task(cid)) for cid in request.car_ids]
    results = await asyncio.gather(*tasks)

    found_cars: list[CarResponse] = []
    missing_ids: list[int] = []
    for cid, entity in results:
        if entity is not None:
            found_cars.append(CarResponse.model_validate(entity))
        else:
            missing_ids.append(cid)

    return BatchFetchResponse(items=found_cars, total=len(found_cars), missing_ids=missing_ids)

@app.get("/manufacturers", response_model=list[ManufacturerResponse], tags=["Manufacturers"])
async def get_manufacturers(session: Session = Depends(get_session)) -> list[Manufacturer]:
    manufacturer_repo = ManufacturerRepository(session)
    return manufacturer_repo.get_all()

@app.post(
    "/manufacturers",
    response_model=ManufacturerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Manufacturers"],
)
async def create_manufacturer(data: ManufacturerCreate, session: Session = Depends(get_session)) -> Manufacturer:
    manufacturer_repo = ManufacturerRepository(session)
    existing = manufacturer_repo.get_by_name(data.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Manufacturer '{data.name}' already exists",
        )
    manufacturer = Manufacturer(name=data.name, country=data.country)
    try:
        return manufacturer_repo.add(manufacturer)
    except IntegrityError as err:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Manufacturer '{data.name}' already exists",
        ) from err

@app.get("/manufacturers/{manufacturer_id}", response_model=ManufacturerResponse, tags=["Manufacturers"])
async def get_manufacturer(manufacturer_id: int, session: Session = Depends(get_session)) -> Manufacturer:
    manufacturer_repo = ManufacturerRepository(session)
    manufacturer = manufacturer_repo.get_by_id(manufacturer_id)
    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with ID {manufacturer_id} not found",
        )
    return manufacturer

@app.get("/manufacturers/{manufacturer_id}/cars", response_model=list[CarResponse], tags=["Manufacturers"])
async def get_cars_by_manufacturer(
    manufacturer_id: int,
    session: Session = Depends(get_session),
) -> list[CarEntity]:
    manufacturer_repo = ManufacturerRepository(session)
    car_repo = CarRepository(session)
    manufacturer = manufacturer_repo.get_by_id(manufacturer_id)
    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with ID {manufacturer_id} not found",
        )
    return car_repo.find_by_manufacturer_name(manufacturer.name)

@app.delete("/manufacturers/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Manufacturers"])
async def delete_manufacturer(manufacturer_id: int, session: Session = Depends(get_session)) -> None:
    manufacturer_repo = ManufacturerRepository(session)
    deleted = manufacturer_repo.delete(manufacturer_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer with ID {manufacturer_id} not found",
        )

@app.get(
    "/manufacturers/analytics/statistics",
    response_model=list[ManufacturerStatisticsResponse],
    tags=["Analytics"],
)
async def get_manufacturers_statistics(
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    car_repo = CarRepository(session)
    return car_repo.get_manufacturer_statistics()

@app.post("/external/batch-fetch", response_model=RemoteBatchResponse, tags=["Async HTTPX"])
async def external_batch_fetch(request: RemoteBatchRequest) -> RemoteBatchResponse:
    try:
        successful, failed = await fetch_resources_concurrently(
            urls=request.urls,
            max_concurrency=5,
            timeout=8.0,
            attempts=3,
        )
        return RemoteBatchResponse(results=successful, failed_urls=failed)
    except TimeoutError as err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Batch external fetch operation timed out",
        ) from err
