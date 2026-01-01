"""Location resolution and timezone handling."""

import datetime
import socket
from typing import Any, Optional, Union

import pytz  # type: ignore[import-untyped]
import redis
import timezonefinder  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError, RedisError

from .logging import get_logger
from .metrics import location_cache_operations, location_resolution_duration, track_time

logger = get_logger(__name__)

# Type aliases
RedisClient = Optional[redis.Redis]
Timezone = Union[datetime.tzinfo, pytz.tzinfo.BaseTzInfo]

# Global timezone finder instance
timezone_finder: timezonefinder.TimezoneFinder = timezonefinder.TimezoneFinder()


def get_timezone(lat: float, lon: float) -> Timezone:
    """Return timezone for coordinate."""
    tzname: Optional[str] = timezone_finder.timezone_at(lng=lon, lat=lat)
    if not tzname:
        return pytz.UTC
    return pytz.timezone(tzname)


def resolve_location(
    redis_client: RedisClient, geolocator: Optional[Nominatim], data: str = "Oslo/Norway"
) -> tuple[Optional[float], Optional[float], str, bool]:
    """Get coordinates from location name. Return lat, long, name, cached."""
    with track_time(location_resolution_duration):
        # Check if coordinates
        if "," in data:
            try:
                lat_str, lon_str = data.split(",", 1)
                lat = float(lat_str)
                lon = float(lon_str)
                location_cache_operations.labels(operation="direct_coordinates").inc()
                return lat, lon, f"coordinates {lat}, {lon}", False
            except (ValueError, IndexError):
                pass

        # Check if in redis cache
        try:
            cache: Optional[bytes] = (
                redis_client.get(data) if redis_client is not None else None  # type: ignore[assignment]
            )
        except (ConnectionError, RedisError) as err:
            logger.error("Redis connection error", err)
            return None, None, "Internal error", False

        if cache:
            lat_str, lon_str, address = cache.decode("utf-8").split("|", 2)
            location_cache_operations.labels(operation="hit").inc()
            return float(lat_str), float(lon_str), address, True

        # Geocode the location
        location_cache_operations.labels(operation="miss").inc()
        if geolocator is None:
            return None, None, "No service", False

        try:
            coordinate: Any = geolocator.geocode(data, language="en")
        except socket.timeout as err:
            logger.warning("Geocoding service timeout", error=str(err))
            return None, None, "No service", False

        if not coordinate:
            return None, None, "No location found", False

        lat: float = coordinate.latitude
        lon: float = coordinate.longitude
        address: str = (
            coordinate.address if isinstance(coordinate.address, str) else str(coordinate.address)
        )

        # Store to redis cache as <search>: "lat|lon|address"
        if redis_client is not None:
            try:
                redis_client.setex(
                    data,
                    datetime.timedelta(days=7),
                    "|".join([str(lat), str(lon), address]),
                )
            except RedisError as err:
                logger.warning("Redis cache write failed", error=str(err))

        return lat, lon, address, False
