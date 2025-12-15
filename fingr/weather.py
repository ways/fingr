"""Weather data fetching and processing."""

from typing import Any, Tuple

from metno_locationforecast import Forecast, Place  # type: ignore[import-untyped]


def fetch_weather(
    lat: float, lon: float, address: str = "", user_agent: str = ""
) -> Tuple[Any, Any]:
    """Get forecast data using metno-locationforecast."""
    location: Place = Place(address, lat, lon)
    forecast: Forecast = Forecast(location, user_agent=user_agent)
    updated: Any = forecast.update()
    if forecast.json["status_code"] != 200:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Forecast response: %s", forecast.json["status_code"])
    return forecast, updated


def calculate_wind_chill(temperature: float, wind_speed: float) -> int:
    return int(
        13.12
        + (0.615 * float(temperature))
        - (11.37 * (float(wind_speed) * 3.6) ** 0.16)
        + (0.3965 * float(temperature)) * ((float(wind_speed) * 3.6) ** 0.16)
    )
