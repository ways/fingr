"""Prometheus metrics for fingr."""

import time
from contextlib import contextmanager
from typing import Generator

from prometheus_client import Counter, Histogram

# Request metrics
requests_total = Counter(
    "fingr_requests_total",
    "Total number of fingr requests",
    ["status"],
)

request_duration = Histogram(
    "fingr_request_duration_seconds",
    "Request processing duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# API metrics
api_requests_total = Counter(
    "fingr_api_requests_total",
    "Total number of met.no API requests",
    ["status"],
)

api_request_duration = Histogram(
    "fingr_api_request_duration_seconds",
    "Met.no API request duration in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Location cache metrics
location_cache_operations = Counter(
    "fingr_location_cache_operations_total",
    "Location cache hits and misses",
    ["operation"],  # hit, miss, direct_coordinates
)

# Weather data metrics
weather_data_freshness = Counter(
    "fingr_weather_data_freshness_total",
    "Weather data freshness status",
    ["status"],  # updated, cached
)

# Geographic metrics
location_requests = Counter(
    "fingr_location_requests_total",
    "Requests by geographic location",
    ["latitude_bucket", "longitude_bucket", "address"],
)

originator_requests = Counter(
    "fingr_originator_requests_total",
    "Requests by originator geographic location",
    ["latitude_bucket", "longitude_bucket", "location"],
)

# Processing time breakdown
location_resolution_duration = Histogram(
    "fingr_location_resolution_duration_seconds",
    "Location resolution duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5),
)

weather_fetch_duration = Histogram(
    "fingr_weather_fetch_duration_seconds",
    "Weather data fetch duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

formatting_duration = Histogram(
    "fingr_formatting_duration_seconds",
    "Response formatting duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)


@contextmanager
def track_time(histogram: Histogram) -> Generator[None, None, None]:
    """Context manager to track execution time."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        histogram.observe(duration)


def bucket_coordinate(value: float, bucket_size: float = 0.01) -> str:
    """Bucket coordinates for grouping in metrics."""
    bucket = int(value / bucket_size) * bucket_size
    return f"{bucket:.3f}"


def record_location_request(lat: float, lon: float, address: str) -> None:
    """Record a location request with bucketed coordinates."""
    lat_bucket = bucket_coordinate(lat)
    lon_bucket = bucket_coordinate(lon)
    # Truncate address to avoid cardinality explosion
    address_short = address[:50] if len(address) > 50 else address
    location_requests.labels(
        latitude_bucket=lat_bucket,
        longitude_bucket=lon_bucket,
        address=address_short,
    ).inc()


def record_originator_request(lat: float, lon: float, location: str) -> None:
    """Record an originator request with bucketed coordinates."""
    lat_bucket = bucket_coordinate(lat)
    lon_bucket = bucket_coordinate(lon)
    # Truncate location to avoid cardinality explosion
    location_short = location[:50] if len(location) > 50 else location
    originator_requests.labels(
        latitude_bucket=lat_bucket,
        longitude_bucket=lon_bucket,
        location=location_short,
    ).inc()
