"""GeoIP lookup for request originator locations."""

from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)

# Global GeoIP reader (initialized in server startup)
geoip_reader: Optional[object] = None


def init_geoip() -> None:
    """Initialize GeoIP reader with MaxMind database."""
    global geoip_reader
    try:
        import geoip2.database

        # Try to load GeoLite2-City database from common locations
        database_paths = [
            "/usr/share/GeoIP/GeoLite2-City.mmdb",
            "/var/lib/GeoIP/GeoLite2-City.mmdb",
            "./GeoLite2-City.mmdb",
            "/etc/fingr/GeoLite2-City.mmdb",
        ]

        for db_path in database_paths:
            try:
                geoip_reader = geoip2.database.Reader(db_path)
                logger.info("GeoIP database loaded", path=db_path)
                return
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning("Failed to load GeoIP database", path=db_path, error=str(e))

        logger.warning(
            "GeoIP database not found. Originator location tracking disabled. "
            "Install GeoLite2-City.mmdb to enable."
        )
    except ImportError:
        logger.warning("geoip2 library not available. Originator location tracking disabled.")


def lookup_ip_location(ip_address: str) -> tuple[Optional[float], Optional[float], str]:
    """
    Lookup geographic location for an IP address.

    Returns:
        Tuple of (latitude, longitude, location_name)
        Returns (None, None, "unknown") if lookup fails or database not available.
    """
    # Skip private/local IPs first (regardless of database availability)
    if ip_address in ("127.0.0.1", "::1", "localhost") or ip_address.startswith("192.168."):
        return None, None, "local"

    if geoip_reader is None:
        return None, None, "unknown"

    try:
        response = geoip_reader.city(ip_address)  # type: ignore[attr-defined]
        lat = response.location.latitude
        lon = response.location.longitude

        # Build location name
        parts = []
        if response.city.name:
            parts.append(response.city.name)
        if response.country.name:
            parts.append(response.country.name)

        location_name = ", ".join(parts) if parts else "unknown"

        logger.debug(
            "GeoIP lookup successful", ip=ip_address, lat=lat, lon=lon, location=location_name
        )
        return lat, lon, location_name

    except Exception as e:
        logger.debug("GeoIP lookup failed", ip=ip_address, error=str(e))
        return None, None, "unknown"
