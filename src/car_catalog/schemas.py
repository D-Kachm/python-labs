from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ManufacturerBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str = Field(default="Unknown", min_length=1, max_length=100)


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerResponse(ManufacturerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CarBase(BaseModel):
    model: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1886, le=2050)
    price: float = Field(ge=0.0)
    mileage: float = Field(ge=0.0)
    vin: str = Field(min_length=17, max_length=17, pattern=r"^[A-HJ-NPR-Z0-9]{17}$")


class CarCreate(CarBase):
    manufacturer_id: int = Field(gt=0)


class CarUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=100)
    year: int | None = Field(default=None, ge=1886, le=2050)
    price: float | None = Field(default=None, ge=0.0)
    mileage: float | None = Field(default=None, ge=0.0)
    vin: str | None = Field(default=None, min_length=17, max_length=17, pattern=r"^[A-HJ-NPR-Z0-9]{17}$")


class CarResponse(CarBase):
    id: int
    manufacturer_id: int
    manufacturer: ManufacturerResponse | None = None
    model_config = ConfigDict(from_attributes=True)


class ManufacturerStatisticsResponse(BaseModel):
    manufacturer: str
    total_cars: int
    average_price: float
    min_price: float
    max_price: float


class AnalyticsSummaryResponse(BaseModel):
    total_cars: int
    average_price: float
    most_expensive_car: CarResponse | None = None
    lowest_mileage_car: CarResponse | None = None


class BatchFetchRequest(BaseModel):
    car_ids: list[int] = Field(min_length=1, max_length=100)


class BatchFetchResponse(BaseModel):
    items: list[CarResponse]
    total: int
    missing_ids: list[int]


class RemoteBatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)


class RemoteBatchResponse(BaseModel):
    results: list[dict[str, Any]]
    failed_urls: list[str]
