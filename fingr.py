#!/usr/bin/env python3

import argparse
import asyncio
import datetime
import logging
import math
import os
import secrets  # Random selection
import socket  # To catch connection error
import string
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import pysolar  # type: ignore[import-untyped]
import pytz
import redis
import timezonefinder  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from metno_locationforecast import Forecast, Place  # type: ignore[import-untyped]
from prometheus_client import Counter, Histogram, start_http_server

# Quiet the specific pysolar leap-second message so it doesn't spam logs
warnings.filterwarnings(
    "ignore",
    message="I don't know about leap seconds after 2023",
    category=UserWarning,
    module=r"pysolar\.solartime",
)

# Versioning and metadata
__version__: str = "2025-10"
__url__: str = "https://github.com/ways/fingr"
__license__: str = "GPL3"

# Global constants and configuration
input_limit: int = 30
weather_legend: str = (
    "\nLegend left axis:   - Sunny   ^ Scattered   = Clouded   =V= Thunder   # Fog"
    + "\nLegend right axis:  | Rain    ! Sleet       * Snow\n"
)
last_reply_file: str = "/tmp/fingr"  # nosec B108

# Type aliases for clarity
RedisClient = Optional[redis.Redis]
Timezone = datetime.tzinfo

# Prometheus metrics
REQUEST_COUNT = Counter("fingr_requests_total", "Total number of requests", ["status"])
LOCATION_LOOKUP_TIME = Histogram(
    "fingr_location_lookup_seconds", "Time spent looking up location", ["cached"]
)
LOCATION_CACHE_HITS = Counter(
    "fingr_location_cache_total", "Location lookup cache hits/misses", ["cached"]
)
WEATHER_FETCH_TIME = Histogram(
    "fingr_weather_fetch_seconds", "Time spent fetching weather data", ["cached"]
)
WEATHER_CACHE_HITS = Counter(
    "fingr_weather_cache_total", "Weather data cache hits/misses", ["cached"]
)
RESPONSE_TIME = Histogram("fingr_response_seconds", "Total response time")
LOCATION_REQUESTS = Counter(
    "fingr_location_requests",
    "Number of requests per location with coordinates",
    ["location_name", "latitude", "longitude"],
)


def load_user_agent() -> str:
    """Load user agent string from file. Met.no requires a contact address as user agent."""
    uafile: str = "useragent.txt"

    try:
        with open(uafile, encoding="utf-8") as f:
            for line in f:
                return line.strip()
        logger.info("Read useragent file <%s>", uafile)
    except FileNotFoundError:
        logger.warning(
            "Unable to read useragent file <%s>. This is required by upstream API. You risk getting your IP banned.",
            uafile,
        )
    return "default fingr useragent"


def load_motd_list() -> List[str]:
    """Load message of the day list from file."""
    motdfile: str = "motd.txt"
    motdlist: List[str] = []
    count: int = 0

    try:
        with open(motdfile, encoding="utf-8") as f:
            for line in f:
                count += 1
                line = line.strip()
                if line.startswith("#"):
                    continue
                if len(line) == 0:
                    continue
                motdlist.append(line.strip())

        logger.info("Read motd file with <%s> lines.", count)
    except FileNotFoundError as err:
        logger.warning("Unable to read motd list, <%s/%s>. Warning: %s", os.getcwd(), motdfile, err)

    return motdlist


def random_message(messages: List[str]) -> str:
    """Pick a random message of the day."""
    if len(messages) == 0:
        return ""
    return "[" + messages[secrets.randbelow(len(messages))] + "]\n"


def load_deny_list() -> List[str]:
    """Load list of IPs to deny service from file."""
    denyfile: str = "deny.txt"
    denylist: List[str] = []
    count: int = 0

    try:
        with open(denyfile, encoding="utf-8") as f:
            for line in f:
                count += 1
                line = line.strip()
                if line.startswith("#"):
                    continue
                if len(line) == 0:
                    continue
                denylist.append(line.strip())

        logger.info("Read denylist with %s lines.", count)
    except FileNotFoundError as err:
        logger.warning("Unable to read deny list, <%s/%s>. Warning: %s", os.getcwd(), denyfile, err)

    return denylist


def get_timezone(lat: float, lon: float) -> Timezone:
    """Return timezone for coordinate."""
    # timezone_finder is a global instance created later; its timezone_at() returns a timezone name
    tzname: Optional[str] = timezone_finder.timezone_at(lng=lon, lat=lat)
    if not tzname:
        # Fallback to UTC when timezone cannot be determined
        return pytz.UTC
    return pytz.timezone(tzname)


def wind_direction(deg: int) -> str:
    """Return compass direction from degrees."""
    symbol: str = ""

    if 293 <= deg < 338:
        symbol = "NW"
    elif 338 <= deg < 360:
        symbol = " N"
    elif 0 <= deg < 23:
        symbol = " N"
    elif 23 <= deg < 68:
        symbol = "NE"
    elif 68 <= deg < 113:
        symbol = " E"
    elif 113 <= deg < 158:
        symbol = "SE"
    elif 158 <= deg < 203:
        symbol = " S"
    elif 203 <= deg < 248:
        symbol = "SW"
    elif 248 <= deg < 293:
        symbol = " W"
    else:
        symbol = " ?"
    return symbol


def clean_input(data: str) -> str:
    """Only allow numbers, letters, and some special chars from user."""
    # Change sub score to space
    data = data.replace("_", " ")

    # TODO: include all weird characters for other languages
    SPECIAL_CHARS: str = "^-.,:/~¤£ øæåØÆÅéüÜÉýÝ"
    allowed_chars: str = string.digits + string.ascii_letters + SPECIAL_CHARS
    return "".join(c for c in data if c in allowed_chars)


def resolve_location(
    redis_client: RedisClient, geolocator: Nominatim, data: str = "Oslo/Norway"
) -> Tuple[Optional[float], Optional[float], str, bool]:
    """Get coordinates from location name. Return lat, long, name, cached."""
    start_time = time.time()
    cached = False

    try:
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
            cached = True
            LOCATION_CACHE_HITS.labels(cached="True").inc()
            return float(lat_str), float(lon_str), address, True

        # Geocode the location
        try:
            coordinate = geolocator.geocode(data, language="en")
        except socket.timeout as err:
            logger.warning("Geocoding service timeout: %s", err)
            return None, None, "No service", False

        if not coordinate:
            return None, None, "No location found", False

        lat = coordinate.latitude
        lon = coordinate.longitude
        address = (
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
            except redis.exceptions.RedisError as err:
                logger.warning("Redis cache write failed: %s", err)

        LOCATION_CACHE_HITS.labels(cached="False").inc()
        return lat, lon, address, False
    finally:
        LOCATION_LOOKUP_TIME.labels(cached=str(cached)).observe(time.time() - start_time)


def fetch_weather(lat: float, lon: float, address: str = "") -> Tuple[Any, Any]:
    """Get forecast data using metno-locationforecast."""
    start_time = time.time()
    updated: Any = None
    cached = False

    try:
        location: Place = Place(address, lat, lon)
        forecast: Forecast = Forecast(location, user_agent=user_agent)
        updated = forecast.update()
        if forecast.json["status_code"] != 200:
            logger.error("Forecast response: %s", forecast.json["status_code"])

        # Check if data was cached (not modified = cached)
        # "Data-Not-Expired" = cached, still valid
        # "Data-Not-Modified" = cached, checked but unchanged
        # "Data-Modified" = fresh data from API
        cached = updated in ("Data-Not-Expired", "Data-Not-Modified")
        WEATHER_CACHE_HITS.labels(cached=str(cached)).inc()

        return forecast, updated
    finally:
        WEATHER_FETCH_TIME.labels(cached=str(cached)).observe(time.time() - start_time)


def calculate_wind_chill(temperature: float, wind_speed: float) -> int:
    return int(
        13.12
        + (0.615 * float(temperature))
        - (11.37 * (float(wind_speed) * 3.6) ** 0.16)
        + (0.3965 * float(temperature)) * ((float(wind_speed) * 3.6) ** 0.16)
    )


def sun_up(latitude: float, longitude: float, date: datetime.datetime) -> bool:
    """Return symbols showing if sun is up at a place and time."""
    return 0 < pysolar.solar.get_altitude(latitude, longitude, date)


def format_meteogram(
    forecast: Any,
    lat: float,
    lon: float,
    timezone: Timezone,
    imperial: bool = False,
    beaufort: bool = False,
    offset: int = 0,
    hourstep: int = 1,
    screenwidth: int = 80,
    wind_chill: bool = False,
) -> str:
    """Format a meteogram from forecast data."""
    output: str = ""

    # Init graph
    graph: Dict[int, str] = {}
    tempheight: int = 11
    timeline: int = 13
    windline: int = 15
    windstrline: int = 16
    graph[timeline] = "   "  # time
    graph[timeline + 1] = "    "  # date line
    graph[windline] = "   "  # wind
    graph[windstrline] = "   "  # wind strength
    hourcount: int = int((screenwidth - 14) / 3 + offset)

    # Rain in graph:
    rainheight: int = 10
    rainstep: int = -1
    rainhigh: int = 0  # highest rain on graph

    # First iteration to collect temperature and rain max, min.
    iteration: int = 0
    temphigh: int = -99
    templow: int = 99
    tempstep: int = -1
    for interval in forecast.data.intervals:
        iteration += 1
        if iteration > hourcount:
            break

        if imperial:
            interval.variables["air_temperature"].convert_to("fahrenheit")
        temperature: int = int(interval.variables["air_temperature"].value)
        if wind_chill:
            wind_speed: int = int(interval.variables["wind_speed"].value)
            temperature = calculate_wind_chill(temperature, wind_speed)

        try:
            precipitation: int = math.ceil(float(interval.variables["precipitation_amount"].value))
            if imperial:
                precipitation = int(precipitation / 25.4)  # No convert_to for this unit in lib
        except KeyError:
            precipitation = 0

        if temperature > temphigh:
            temphigh = temperature

        if temperature < templow:
            templow = temperature

        if math.ceil(precipitation) > rainhigh:
            rainhigh = precipitation

    # Scale y-axis based on first iteration. default = -1
    if tempheight <= (temphigh - templow):
        tempstep = -2

    if temphigh == templow:
        templow = temphigh - 1

    # Create temp range
    temps: List[int] = []
    for t in range(int(temphigh), int(templow) - 1, tempstep):
        temps.append(t)

    # Extend temp range
    for t in range(0, tempheight):
        if len(temps) + 1 < tempheight:
            if t % 2 == 0:  # extend down
                temps.append(temps[len(temps) - 1] - abs(tempstep))
            else:  # extend up
                temps = [temps[0] + abs(tempstep)] + temps

    # write temps to graph
    for i in range(1, tempheight):
        try:
            graph[i] = str(temps[i - 1]).rjust(3, " ")
        except IndexError:  # list empty
            pass

    # create rainaxis #TODO: make this scale
    rainaxis: List[str] = []
    for r in range(rainheight, 0, rainstep):
        if r <= rainhigh:  # + 1
            rainaxis.append(f"{r:2.0f} mm ")
        else:
            rainaxis.append(" ")

    # draw graph elements:
    iteration = 0
    for interval in forecast.data.intervals:
        temperature = int(interval.variables["air_temperature"].value)
        wind_from_direction: int = int(interval.variables["wind_from_direction"].value)
        if wind_chill:
            temperature = calculate_wind_chill(temperature, wind_speed)  # type: ignore[name-defined]
        if beaufort:
            interval.variables["wind_speed"].convert_to("beaufort")
        elif imperial:
            interval.variables["wind_speed"].convert_to("mph")
        wind_speed = int(interval.variables["wind_speed"].value)
        try:
            rain: int = math.ceil(float(interval.variables["precipitation_amount"].value))
            if imperial:
                rain = int(rain / 25.4)  # No convert_to for this unit in lib
        except KeyError:
            rain = 0

        iteration += 1
        if iteration > hourcount:
            break

        # Rain
        rainmax: int = 0  # max rain for this hour

        # Wind on x axis
        graph[windline] += " " + (
            wind_direction(wind_from_direction) if wind_speed != 0.0 else " O"
        )

        # Wind strength on x axis
        graph[windstrline] += " " + f"{wind_speed:2.0f}"

        # Time on x axis
        start_time_interval: datetime.datetime = interval.start_time.replace(
            tzinfo=pytz.timezone("UTC")
        ).astimezone(timezone)
        date: str = start_time_interval.strftime("%d/%m")
        hour: str = start_time_interval.strftime("%H")
        if sun_up(latitude=lat, longitude=lon, date=start_time_interval):
            spacer: str = "_"
        else:
            spacer = " "

        if hour == "01":  # Date changed
            graph[timeline] = graph[timeline][:-2] + date
        else:
            graph[timeline] += spacer + hour

        # for each y (temp) look for matching temp, draw graph
        for i in range(1, tempheight):  # draw temp
            try:
                # parse out numbers to be compared
                temptomatch: List[int] = [temperature]
                tempingraph: int = int(graph[i][:3].strip())

                if tempstep < -1:  # TODO: this should scale higher than one step
                    temptomatch.append(temptomatch[0] - 1)

                if tempingraph in temptomatch:
                    # Match symbols from https://api.met.no/weatherapi/weathericon/2.0/documentation
                    if not interval.symbol_code:
                        graph[i] += "   "
                    elif "partlycloudy" in interval.symbol_code:  # partly
                        graph[i] += "^^^"
                    elif (
                        "cloudy" in interval.symbol_code
                        or "rain" in interval.symbol_code
                        or "sleet" in interval.symbol_code
                        or "snow" in interval.symbol_code
                    ):  # clouded, rain
                        graph[i] += "==="
                    elif "thunder" in interval.symbol_code:  # thunder
                        graph[i] += "=V="
                    elif "fog" in interval.symbol_code:  # fog
                        graph[i] += "###"
                    elif "fair" in interval.symbol_code:  # light clouds
                        graph[i] += "=--"
                    elif "clearsky" in interval.symbol_code:  # clear
                        graph[i] += "---"
                    else:  # Shouldn't hit this
                        graph[i] += interval.symbol_code
                else:
                    graph[i] += "   "
            except KeyError:
                continue

            # compare rain, and print
            # TODO: scaling
            if (rain != 0) and (rain > 10 - i):
                if "sleet" in interval.symbol_code:  # sleet
                    rainsymbol: str = "!"
                elif "snow" in interval.symbol_code:  # snow
                    rainsymbol = "*"
                else:  # if int(item['symbolnumber']) in [5,6,9,10,11,14]: #rain
                    rainsymbol = "|"

                # if 0 > int(item['temperature']): #rain but cold
                #     rainsymbol = "*"

                # if verbose:
                #     print("rainmax: ", rainmax,"i",i,"rain",rain)

                # if overflow, print number at top
                if rain > 10 and i == 1:
                    rainsymbol = f"{rain:2.0f}"
                    graph[i] = graph[i][:-2] + rainsymbol
                else:
                    # print rainmax if larger than rain.
                    if rainmax > rain:
                        try:
                            graph[i - 1] = graph[i - 1][:-1] + "'"
                        except KeyError:
                            pass

                    # print rain
                    graph[i] = graph[i][:-1] + rainsymbol

    graph = print_units(graph, screenwidth, imperial, beaufort, windline, windstrline, timeline)
    output += print_meteogram_header(
        forecast.place.name + (" (wind chill)" if wind_chill else ""), screenwidth
    )

    # add rain to graph
    for i in range(1, tempheight):
        try:
            graph[i] += rainaxis[i - 1]
        except IndexError:
            pass

    for k in sorted(graph.keys()):
        output += graph[k] + "\n"

    # Weather legend
    output += weather_legend

    return output


def print_units(
    graph: Dict[int, str],
    screenwidth: int,
    imperial: bool,
    beaufort: bool,
    windline: int,
    windstrline: int,
    timeline: int,
) -> Dict[int, str]:
    """Add units for rain, wind, etc."""
    graph[0] = " 'C" + str.rjust("Rain (mm) ", screenwidth - 3)
    if imperial:
        graph[0] = " 'F" + str.rjust("Rain (in)", screenwidth - 3)
    graph[windline] += " Wind dir."
    if beaufort:
        graph[windstrline] += " Wind(Bft)"
    elif imperial:
        graph[windstrline] += " Wind(mph)"
    else:
        graph[windstrline] += " Wind(m/s)"
    graph[timeline] += " Hour"

    return graph


def print_meteogram_header(display_name: str, screenwidth: int) -> str:
    """Return the header."""
    headline: str = f"-= Meteogram for {display_name} =-"
    return str.center(headline, screenwidth) + "\n"


def format_oneliner(
    forecast: Any,
    timezone: Timezone,
    imperial: bool = False,
    beaufort: bool = False,
    offset: int = 0,
    wind_chill: bool = False,
) -> str:
    """Return a one-line weather forecast. TODO: remove json, respect windchill, imperial, etc."""
    start_time: Optional[datetime.datetime] = None
    place: str = forecast.place.name
    next6: Any = forecast.json["data"]["properties"]["timeseries"][0]["data"]["next_6_hours"]

    for interval in forecast.data.intervals:
        start_time = interval.start_time.replace(tzinfo=pytz.timezone("UTC")).astimezone(timezone)
        break

    return f"{start_time} {place} next 6 hours: {next6}"


async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Receives connections and responds."""
    global r, geolocator

    request_start_time = time.time()
    data: bytes = await reader.read(input_limit)
    response: str = ""
    updated: Any = None
    imperial: bool = False
    beaufort: bool = False
    oneliner: bool = False
    status: str = "success"

    try:
        user_input: str = clean_input(data.decode())
        addr: Tuple[str, int] = writer.get_extra_info("peername")  # type: ignore[assignment]
        screenwidth: int = 80
        wind_chill: bool = False

        logger.debug('%s GET "%s"', addr[0], user_input)

        # Deny list
        if addr[0] in denylist:
            logger.info('%s BLACKLISTED "%s"', addr[0], user_input)
            response = "You have been blacklisted for excessive use. Send a mail to blacklist@falkp.no to be delisted."
            status = "blacklisted"
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
                screenwidth = max(80, min(int(width_str), 200))
            except ValueError:
                pass

        if user_input == "help" or len(user_input) == 0:
            logger.info("%s help", addr[0])
            response = service_usage()
            status = "help"

        else:
            lat, lon, address, cached_location = resolve_location(r, geolocator, user_input)
            if not lat:
                if address == "No service":
                    response += "Error: address service down. You can still use coordinates."
                    status = "error_no_service"
                else:
                    logger.info('%s NOTFOUND "%s"', addr[0], user_input)
                    response += "Location not found. Try help."
                    status = "not_found"
            else:
                # At this point lat and lon are guaranteed to be float, not None
                if lat is None or lon is None:
                    response = "Location not found. Try help."
                    status = "not_found"
                else:
                    timezone: Timezone = get_timezone(lat, lon)
                    weather_data, updated = fetch_weather(lat, lon, address)

                    # Track location on map - increment counter for each request
                    LOCATION_REQUESTS.labels(
                        location_name=address[:100],  # Limit length for label
                        latitude=f"{lat:.4f}",
                        longitude=f"{lon:.4f}",
                    ).inc()

                    logger.info(
                        '%s Resolved "%s" to "%s". location cached: %s. '
                        + "Weatherdata: %s. o:%s, ^:%s, £:%s, ¤:%s",
                        addr[0],
                        user_input,
                        address,
                        bool(cached_location),
                        updated,
                        bool(oneliner),
                        bool(imperial),
                        bool(beaufort),
                        bool(wind_chill),
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
        logger.debug("%s Replied with %s bytes. Weatherdata: %s", addr[0], len(response), updated)
        await writer.drain()
        writer.close()

        if last_reply_file:
            try:
                with open(last_reply_file, mode="w", encoding="utf-8") as f:
                    f.write(f"{addr[0]} {user_input}\n\n{response}")
            except OSError as err:
                logger.warning("Failed to write last reply file: %s", err)

        REQUEST_COUNT.labels(status=status).inc()
        RESPONSE_TIME.observe(time.time() - request_start_time)


async def main(args: argparse.Namespace) -> None:
    """Start server and bind to port."""
    global r

    logger.info(f"Connecting to redis host {args.redis_host} port {args.redis_port}")
    r = redis.Redis(host=args.redis_host, port=args.redis_port)
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        logger.error("Unable to connect to redis at <%s>:<%s>", args.redis_host, args.redis_port)
        sys.exit(1)
    logger.info("Redis connected")

    # Start Prometheus metrics server
    if args.metrics_port:
        start_http_server(args.metrics_port)
        logger.info("Prometheus metrics server started on port %s", args.metrics_port)

    logger.info("Starting on port %s", args.port)
    server: asyncio.AbstractServer = await asyncio.start_server(
        handle_request, args.host, args.port
    )

    addr = server.sockets[0].getsockname()
    logger.info("Ready to serve on address %s:%s", addr[0], addr[1])

    async with server:
        await server.serve_forever()


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


# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z"
)
logger = logging.getLogger()

# Global runtime objects (with types)
denylist: List[str] = load_deny_list()
motdlist: List[str] = load_motd_list()
user_agent: str = load_user_agent()
r: RedisClient = None  # type: ignore[assignment]
geolocator: Nominatim = Nominatim(user_agent=user_agent, timeout=3)
timezone_finder: timezonefinder.TimezoneFinder = timezonefinder.TimezoneFinder()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fingr")
    # parser.add_argument('-h', '--help')
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-o", "--host", dest="host", default="127.0.0.1", action="store")
    parser.add_argument("-p", "--port", dest="port", default=7979, action="store")
    parser.add_argument(
        "-r", "--redis_host", dest="redis_host", default="localhost", action="store"
    )
    parser.add_argument("-n", "--redis_port", dest="redis_port", default=6379, action="store")
    parser.add_argument(
        "-m",
        "--metrics-port",
        dest="metrics_port",
        type=int,
        default=8000,
        help="Port for Prometheus metrics endpoint (default: 8000)",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
