from typing import Callable
from car_catalog.analytics import (
    calculate_average_price,
    find_lowest_mileage_car,
    find_most_expensive_car,
    sort_by_price,
)
from car_catalog.batches import batched_cars, dynamic_batched
from car_catalog.filters import (
    filter_by_brand_and_year_stream,
    filter_by_brand_stream,
    filter_by_year_stream,
    filter_cars_stream,
    validate_cars,
)
from car_catalog.models import Car
from car_catalog.parsers import clean_lines, parse_csv_rows
from car_catalog.pipeline import (
    build_streaming_pipeline,
    export_stream_to_csv,
    find_first_car,
)
from car_catalog.processors import (
    create_car_index,
    filter_by_brand,
    filter_by_year,
    find_car_by_id,
    get_unique_brands,
)
from car_catalog.readers import infinite_car_stream, read_lines, read_multiple_files
from car_catalog.streaming_analytics import (
    streaming_accumulate_prices,
    streaming_average_price,
    streaming_find_lowest_mileage,
    streaming_find_most_expensive,
    streaming_groupby_brand,
    streaming_min_max_price,
    streaming_pairwise_price_diff,
    streaming_statistics,
)
from car_catalog.transformations import (
    apply_price_discount,
    convert_currency,
    normalize_car_names,
)

def search_by_brand(cars: list[Car], brand: str) -> list[Car]:
    return filter_by_brand(cars, brand)

def process_pipeline(cars: list[Car], *operations: Callable[[list[Car]], list[Car]]) -> list[Car]:
    result = cars
    for op in operations:
        result = op(result)
    return result
