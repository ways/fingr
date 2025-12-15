"""Weather data fetching and processing."""

from typing import Any, Tuple

from metno_locationforecast import Forecast, Place  # type: ignore[import-untyped]

from .logging import get_logger
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
) -> Tuple[Any, Any]:
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
        if updated == "Data-Modified":
            weather_data_freshness.labels(status="updated").inc()
        elif updated == "Data-Not-Expired":
            weather_data_freshness.labels(status="cached").inc()

        return forecast, updated


def calculate_wind_chill(temperature: float, wind_speed: float) -> int:
    return int(
        13.12
        + (0.615 * float(temperature))
        - (11.37 * (float(wind_speed) * 3.6) ** 0.16)
        + (0.3965 * float(temperature)) * ((float(wind_speed) * 3.6) ** 0.16)
    )
