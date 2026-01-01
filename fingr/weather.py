"""Weather data fetching and processing."""

from typing import Any

from metno_locationforecast import Forecast, Place  # type: ignore[import-untyped]

from .log import get_logger
from .metrics import (
    api_request_duration,
    api_requests_total,
    track_time,
    weather_data_freshness,
    weather_fetch_duration,
)

logger = get_logger(__name__)


def fetch_weather(
    lat: float, lon: float, address: str = "", user_agent: str = ""
) -> tuple[Any, Any]:
    """Get forecast data using metno-locationforecast."""
    with track_time(weather_fetch_duration):
        location: Place = Place(address, lat, lon)
        forecast: Forecast = Forecast(location, user_agent=user_agent)

        with track_time(api_request_duration):
            updated: Any = forecast.update()

        if forecast.json["status_code"] != 200:
            logger.error("Forecast response error", status_code=forecast.json["status_code"])
            api_requests_total.labels(status="error").inc()
        else:
            api_requests_total.labels(status="success").inc()

        # Track weather data freshness
        logger.debug("Weather data status", status=updated)
        if updated == "Data-Modified":
            weather_data_freshness.labels(status="updated").inc()
        elif updated in ("Data-Not-Expired", "Data-Not-Modified"):
            weather_data_freshness.labels(status="cached").inc()

        return forecast, updated


def calculate_wind_chill(temperature: float, wind_speed: float) -> int:
    """Calculate wind chill temperature using the formula.

    Args:
        temperature: Temperature in Celsius
        wind_speed: Wind speed in m/s

    Returns:
        Wind chill temperature as integer
    """
    return int(
        13.12
        + (0.615 * float(temperature))
        - (11.37 * (float(wind_speed) * 3.6) ** 0.16)
        + (0.3965 * float(temperature)) * ((float(wind_speed) * 3.6) ** 0.16)
    )
