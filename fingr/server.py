"""Server and request handling."""

import argparse
import asyncio
import sys
from typing import Any, Optional, Tuple

import redis
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError

from .config import load_deny_list, load_motd_list, load_user_agent, random_message
from .formatting import format_meteogram, format_oneliner
from .location import RedisClient, get_timezone, resolve_location
from .logging import get_logger
from .utils import clean_input
from .weather import fetch_weather

logger = get_logger(__name__)

# Global constants
input_limit: int = 30
last_reply_file: str = "/tmp/fingr"  # nosec B108

# Global runtime objects (initialized in main)
denylist: list[str] = []
motdlist: list[str] = []
user_agent: str = ""
r: RedisClient = None
geolocator: Optional[Nominatim] = None


def service_usage() -> str:
    return """Weather via finger, graph.no

* Code: https://github.com/ways/fingr/
* https://nominatim.org/ is used for location lookup.
* https://www.yr.no/ is used for weather data.
* Hosted by Copyleft Solutions AS: https://copyleft.no/
* Contact: finger@falkp.no

Usage:
    finger oslo@graph.no

Using coordinates:
    finger 59.1,10.1@graph.no

Using imperial units:
    finger ^oslo@graph.no

Using the Beaufort wind scale:
    finger £oslo@graph.no

Ask for wider output, longer forecast (~<screen width>):
    finger oslo~200@graph.no

Specify another location when names conflict:
    finger "oslo, united states"@graph.no

Display "wind chill" / "feels like" temperature:
    finger ¤oslo@graph.no

No graph, just a one-line forecast (needs improvement):
    finger o:oslo@graph.no

Hammering will get you blacklisted. Remember the data doesn't change more than once an hour.

News:
* Launched in 2012
* 2021-05: total rewrite due to API changes. Much better location searching, proper hour-by-hour for most of the world.
"""


async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Receives connections and responds."""
    global r, geolocator

    data: bytes = await reader.read(input_limit)
    response: str = ""
    updated: Any = None
    imperial: bool = False
    beaufort: bool = False
    oneliner: bool = False

    try:
        user_input: str = clean_input(data.decode())
        addr: Tuple[str, int] = writer.get_extra_info("peername")  # type: ignore[assignment]
        screenwidth: int = 80
        wind_chill: bool = False

        logger.debug("Request received", ip=addr[0], input=user_input)

        # Deny list
        if addr[0] in denylist:
            logger.info("Request from blacklisted IP", ip=addr[0], input=user_input)
            response = "You have been blacklisted for excessive use. Send a mail to blacklist@falkp.no to be delisted."
            return

        if user_input.startswith("o:"):
            oneliner = True
            user_input = user_input.replace("o:", "")

        # Imperial
        if user_input.startswith("^"):
            user_input = user_input[1:]
            imperial = True

        # Wind speed in the Beaufort scale
        if user_input.startswith("£"):
            user_input = user_input[1:]
            beaufort = True

        # Wind chill
        if user_input.startswith("¤"):
            user_input = user_input[1:]
            wind_chill = True

        # Parse screen width
        if "~" in user_input:
            try:
                user_input, width_str = user_input.split("~", 1)
                screenwidth = int(max(80, min(int(width_str), 200)))
            except ValueError:
                pass

        if user_input == "help" or len(user_input) == 0:
            logger.info("Help requested", ip=addr[0])
            response = service_usage()

        else:
            lat: Optional[float]
            lon: Optional[float]
            address: str
            cached_location: bool
            lat, lon, address, cached_location = resolve_location(r, geolocator, user_input)
            if not lat:
                if address == "No service":
                    response += "Error: address service down. You can still use coordinates."
                else:
                    logger.info("Location not found", ip=addr[0], input=user_input)
                    response += "Location not found. Try help."
            else:
                # At this point lat and lon are guaranteed to be float, not None
                if lat is None or lon is None:
                    response = "Location not found. Try help."
                else:
                    timezone: Any = get_timezone(lat, lon)
                    weather_data: Any
                    weather_data, updated = fetch_weather(lat, lon, address, user_agent)
                    logger.info(
                        "Request processed",
                        ip=addr[0],
                        input=user_input,
                        address=address,
                        location_cached=cached_location,
                        weather_updated=updated,
                        oneliner=oneliner,
                        imperial=imperial,
                        beaufort=beaufort,
                        wind_chill=wind_chill,
                    )

                    if not oneliner:
                        response = format_meteogram(
                            weather_data,
                            lat,
                            lon,
                            imperial=imperial,
                            beaufort=beaufort,
                            screenwidth=screenwidth,
                            wind_chill=wind_chill,
                            timezone=timezone,
                        )
                        response += random_message(motdlist)
                    else:
                        response = format_oneliner(
                            weather_data,
                            timezone=timezone,
                            imperial=imperial,
                            beaufort=beaufort,
                            wind_chill=wind_chill,
                        )

    finally:
        writer.write(response.encode())
        logger.debug("Response sent", ip=addr[0], bytes=len(response), weather_updated=updated)
        await writer.drain()
        writer.close()

        if last_reply_file:
            try:
                with open(last_reply_file, mode="w", encoding="utf-8") as f:
                    f.write(f"{addr[0]} {user_input}\n\n{response}")
            except OSError as err:
                logger.warning("Failed to write last reply file", error=str(err))


async def start_server(args: argparse.Namespace) -> None:
    """Start server and bind to port."""
    global r, geolocator, denylist, motdlist, user_agent

    # Load configuration
    denylist = load_deny_list()
    motdlist = load_motd_list()
    user_agent = load_user_agent()
    geolocator = Nominatim(user_agent=user_agent, timeout=3)

    # Connect to Redis with retry
    logger.info("Connecting to Redis", host=args.redis_host, port=args.redis_port)
    r = redis.Redis(host=args.redis_host, port=args.redis_port)
    max_retries: int = 10
    for attempt in range(max_retries):
        try:
            r.ping()
            logger.info("Redis connected")
            break
        except ConnectionError:
            if attempt < max_retries - 1:
                logger.warning(
                    "Redis not ready, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    retry_delay=2,
                )
                await asyncio.sleep(2)
            else:
                logger.error(
                    "Unable to connect to Redis", host=args.redis_host, port=args.redis_port
                )
                sys.exit(1)

    logger.info("Starting server", port=args.port)
    server: asyncio.AbstractServer = await asyncio.start_server(
        handle_request, args.host, args.port
    )

    addr: Tuple[str, int] = server.sockets[0].getsockname()  # type: ignore[assignment]
    logger.info("Server ready", host=addr[0], port=addr[1])

    async with server:
        await server.serve_forever()
