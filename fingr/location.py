"""Location resolution and timezone handling."""

import datetime
import logging
import socket
from typing import Any, Optional, Tuple, Union

import pytz  # type: ignore[import-untyped]
import redis
import timezonefinder  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

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
) -> Tuple[Optional[float], Optional[float], str, bool]:
    """Get coordinates from location name. Return lat, long, name, cached."""
    # Check if coordinates
    if "," in data:
        try:
            lat_str, lon_str = data.split(",", 1)
            lat = float(lat_str)
            lon = float(lon_str)
            return lat, lon, f"coordinates {lat}, {lon}", False
        except (ValueError, IndexError):
            pass

    # Check if in redis cache
    cache: Optional[bytes] = redis_client.get(data) if redis_client is not None else None
    if cache:
        lat_str, lon_str, address = cache.decode("utf-8").split("|", 2)
        return float(lat_str), float(lon_str), address, True

    # Geocode the location
    if geolocator is None:
        return None, None, "No service", False

    try:
        coordinate: Any = geolocator.geocode(data, language="en")
    except socket.timeout as err:
        logger.warning("Geocoding service timeout: %s", err)
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
            logger.warning("Redis cache write failed: %s", err)

    return lat, lon, address, False
