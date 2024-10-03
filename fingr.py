#!/usr/bin/env python3

import os
import argparse
import logging
import asyncio
import math
import datetime
import pytz
import secrets
import string
from geopy.geocoders import Nominatim
from metno_locationforecast import Place, Forecast
import redis
import pysolar
import timezonefinder
import socket  # To catch connection error

__version__ = "2024-10"
__url__ = "https://github.com/ways/fingr"
__license__ = "GPL3"
input_limit = 30
weather_legend = (
    "\nLegend left axis:   - Sunny   ^ Scattered   = Clouded   =V= Thunder   # Fog"
    + "\nLegend right axis:  | Rain    ! Sleet       * Snow\n"
)
last_reply_file = "/tmp/fingr"  # nosec B108


def read_useragent() -> str:
    """Met.no requires a contact address as user agent."""
    uafile = "useragent.txt"

    try:
        with open(uafile, mode="r", encoding="utf-8") as f:
            for line in f:
                return line.strip()
        logger.info("Read useragent file <%s>", uafile)
    except FileNotFoundError:
        logger.warning(
            "Unable to read useragent file <%s>. This is required by upstream API. You risk getting your IP banned.",
            uafile,
        )
    return "default fingr useragent"


def read_motdlist() -> list:
    """Random message to user."""
    motdfile = "motd.txt"
    motdlist = []
    count = 0

    try:
        with open(motdfile, mode="r", encoding="utf-8") as f:
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
        logger.warning(
            "Unable to read motd list, <%s/%s>. Warning: %s", os.getcwd(), motdfile, err
        )

    return motdlist


def random_message(messages) -> str:
    """Pick a random message of the day."""
    if 0 == len(messages):
        return ""
    return "[" + messages[secrets.randbelow(0, len(messages) - 1)] + "]\n"


def read_denylist() -> list:
    """Populate list of IPs to deny service."""
    denyfile = "deny.txt"
    denylist = []
    count = 0

    try:
        with open(denyfile, mode="r", encoding="utf-8") as f:
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
        logger.warning(
            "Unable to read deny list, <%s/%s>. Warning: %s", os.getcwd(), denyfile, err
        )

    return denylist


def get_timezone(lat, lon) -> str:
    """Return timezone for coordinate."""
    return pytz.timezone(timezone_finder.timezone_at(lng=lon, lat=lat))


def wind_direction(deg):
    """Return compass direction from degrees."""
    symbol = ""

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


def clean_input(data):
    """Only allow numbers, letters, and some special chars from user."""
    # Change sub score to space
    data = data.replace("_", " ")

    # TODO: include all weird characters for other languages
    SPECIAL_CHARS = "^-.,:/~¤ øæåØÆÅéüÜÉýÝ"
    return "".join(
        c for c in data if c in string.digits + string.ascii_letters + SPECIAL_CHARS
    )


def resolve_location(data="Oslo/Norway"):
    """Get coordinates from location name. Return lat, long, name."""
    cache = None

    # Check if coordinates
    if "," in data:
        lat, lon = data.split(",")
        try:
            lat = float(lat)
            lon = float(lon)
            return lat, lon, "coordinates %s, %s" % (lat, lon), False
        except ValueError:
            pass

    lat = None
    lon = None
    address = None

    # Check if in redis cache
    if r is not None:
        cache = r.get(data)
    if cache:
        lat, lon, address = cache.decode("utf-8").split("|")
        lat = float(lat)
        lon = float(lon)

    else:
        coordinate = None
        try:
            coordinate = geolocator.geocode(data, language="en")
        except socket.timeout as err:
            # nominatim.openstreetmap.org down
            print("nominatim.openstreetmap.org down. %s" % err)
            return None, None, "No service", False
        if coordinate:
            lat = coordinate.latitude
            lon = coordinate.longitude
            try:
                address = coordinate.address.decode("utf-8")
            except AttributeError:
                address = coordinate.address

    if lat:
        # Store to redis cache as <search>: "lat,lon,address"
        if cache is not None and not cache:
            r.setex(
                data,
                datetime.timedelta(days=7),
                "|".join([str(lat), str(lon), str(address)]),
            )
        return lat, lon, address, cache

    return None, None, "No location found", False


def fetch_weather(lat, lon, address=""):
    """Get forecast data using metno-locationforecast."""
    location = Place(address, lat, lon)
    forecast = Forecast(location, user_agent=user_agent)
    updated = forecast.update()
    if forecast.json["status_code"] != 200:
        logger.error("Forecast response: %s", forecast.json["status_code"])
    return forecast, updated


def calculate_wind_chill(temperature, wind_speed):
    return int(
        13.12
        + (0.615 * float(temperature))
        - (11.37 * (float(wind_speed) * 3.6) ** 0.16)
        + (0.3965 * float(temperature)) * ((float(wind_speed) * 3.6) ** 0.16)
    )


def sun_up(latitude, longitude, date):
    """Return symbols showing if sun is up at a place and time."""
    # alt = pysolar.solar.get_altitude(latitude, longitude, date)
    if 0 < pysolar.solar.get_altitude(latitude, longitude, date):
        return True
    return False


def format_meteogram(
    forecast,
    lat,
    lon,
    timezone,
    imperial=False,
    beaufort=False,
    offset=0,
    hourstep=1,
    screenwidth=80,
    wind_chill=False,
):
    """Format a meteogram from forcast data."""
    output = ""

    # Init graph
    graph = dict()
    tempheight = 11
    timeline = 13
    windline = 15
    windstrline = 16
    graph[timeline] = "   "  # time
    graph[timeline + 1] = "    "  # date line
    graph[windline] = "   "  # wind
    graph[windstrline] = "   "  # wind strenght
    hourcount = int((screenwidth - 14) / 3 + offset)

    # Rain in graph:
    rainheight = 10
    rainstep = -1
    rainhigh = 0  # highest rain on graph

    # First iteration to collect temperature and rain max, min.
    iteration = 0
    temphigh = -99
    templow = 99
    tempstep = -1
    for interval in forecast.data.intervals:
        iteration += 1
        if iteration > hourcount:
            break

        if imperial:
            interval.variables["air_temperature"].convert_to("fahrenheit")
        temperature = int(interval.variables["air_temperature"].value)
        if wind_chill:
            wind_speed = int(interval.variables["wind_speed"].value)
            temperature = calculate_wind_chill(temperature, wind_speed)

        precipitation = 0
        try:
            precipitation = math.ceil(
                float(interval.variables["precipitation_amount"].value)
            )
            if imperial:
                precipitation = (
                    precipitation / 25.4
                )  # No convert_to for this unit in lib
        except KeyError:
            pass

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
    temps = []
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
    rainaxis = []
    for r in range(rainheight, 0, rainstep):
        if r <= rainhigh:  # + 1
            rainaxis.append("%2.0f mm " % r)
        else:
            rainaxis.append(" ")

    # draw graph elements:
    iteration = 0
    for interval in forecast.data.intervals:
        temperature = int(interval.variables["air_temperature"].value)
        wind_from_direction = int(interval.variables["wind_from_direction"].value)
        wind_speed = int(interval.variables["wind_speed"].value)
        if wind_chill:
            temperature = calculate_wind_chill(temperature, wind_speed)
        if beaufort:
            interval.variables["wind_speed"].convert_to("beaufort")
        elif imperial:
            interval.variables["wind_speed"].convert_to("mph")
        precipitation = 0
        try:
            rain = math.ceil(float(interval.variables["precipitation_amount"].value))
            if imperial:
                rain = rain / 25.4  # No convert_to for this unit in lib
        except KeyError:
            pass

        iteration += 1
        if iteration > hourcount:
            break

        # Rain
        rainmax = 0  # max rain for this hour

        # Wind on x axis
        graph[windline] += " " + (
            wind_direction(wind_from_direction) if wind_speed != 0.0 else " O"
        )

        # Wind strength on x axis
        graph[windstrline] += " " + "%2.0f" % wind_speed

        # Time on x axis
        start_time = interval.start_time.replace(
            tzinfo=pytz.timezone("UTC")
        ).astimezone(timezone)
        date = start_time.strftime("%d/%m")
        hour = start_time.strftime("%H")
        if sun_up(latitude=lat, longitude=lon, date=start_time):
            spacer = "_"
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
                temptomatch = [temperature]
                tempingraph = int(graph[i][:3].strip())

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
                    rainsymbol = "!"
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
                    rainsymbol = "%2.0f" % rain
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

    graph = print_units(
        graph, screenwidth, imperial, beaufort, windline, windstrline, timeline
    )
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
    graph, screenwidth, imperial, beaufort, windline, windstrline, timeline
):
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


def print_meteogram_header(display_name, screenwidth):
    """Return the header."""
    headline = "-= Meteogram for %s =-" % display_name
    return str.center(headline, screenwidth) + "\n"


def format_oneliner(
    forecast, timezone, imperial=False, beaufort=False, offset=0, wind_chill=False
):
    """Return a one-line weather forecast. TODO: remove json, respect windchill, imperial, etc."""
    start_time = None
    place = forecast.place.name
    next6 = forecast.json["data"]["properties"]["timeseries"][0]["data"]["next_6_hours"]

    for interval in forecast.data.intervals:
        start_time = interval.start_time.replace(
            tzinfo=pytz.timezone("UTC")
        ).astimezone(timezone)
        break

    return "%s %s next 6 hours: %s" % (start_time, place, next6)


async def handle_request(reader, writer):
    """Receives connections and responds."""
    data = await reader.read(input_limit)
    response = ""
    updated = None
    imperial = False
    beaufort = False
    oneliner = False

    try:
        user_input = clean_input(data.decode())
        addr = writer.get_extra_info("peername")
        screenwidth = 80
        wind_chill = False

        logger.debug('%s GET "%s"', addr[0], user_input)

        # Deny list
        if addr[0] in denylist:
            logger.info('%s BLACKLISTED "%s"', addr[0], user_input)
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

        if "~" in user_input:
            screenwidth = int(user_input.split("~")[1])
            user_input = user_input.split("~")[0]

        if user_input == "help" or len(user_input) == 0:
            logger.info("%s help", addr[0])
            response = service_usage()

        else:
            lat, lon, address, cached_location = resolve_location(user_input)
            if not lat:
                if address == "No service":
                    response += (
                        "Error: address service down. You can still use coordinates."
                    )
                else:
                    logger.info('%s NOTFOUND "%s"', addr[0], user_input)
                    response += "Location not found. Try help."
            else:
                timezone = get_timezone(lat, lon)
                weather_data, updated = fetch_weather(lat, lon, address)
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
        logger.debug(
            "%s Replied with %s bytes. Weatherdata: %s", addr[0], len(response), updated
        )
        await writer.drain()
        writer.close()

        if last_reply_file:
            with open(last_reply_file, mode="w", encoding="utf-8") as f:
                f.write(addr[0] + " " + user_input + "\n\n")
                f.write(response)


async def main(args):
    """Start server and bind to port."""
    global r

    print("Connecting to redis host %s port %s" % (args.redis_host, args.redis_port))
    r = redis.Redis(host=args.redis_host, port=args.redis_port)
    r.ping()
    logger.debug("Redis connected")

    logger.debug("Starting on port %s", args.port)
    server = await asyncio.start_server(handle_request, args.host, args.port)

    addr = server.sockets[0].getsockname()
    logger.debug("Ready to serve on address %s:%s", addr[0], addr[1])

    async with server:
        await server.serve_forever()


def service_usage():
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


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z"
)
logger = logging.getLogger()

denylist = read_denylist()
motdlist = read_motdlist()
user_agent = read_useragent()
r = None  # redis.Redis()
geolocator = Nominatim(user_agent=user_agent)
timezone_finder = timezonefinder.TimezoneFinder()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fingr")
    # parser.add_argument('-h', '--help')
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-o", "--host", dest="host", default="127.0.0.1", action="store")
    parser.add_argument("-p", "--port", dest="port", default=7979, action="store")
    parser.add_argument(
        "-r", "--redis_host", dest="redis_host", default="localhost", action="store"
    )
    parser.add_argument(
        "-n", "--redis_port", dest="redis_port", default=6379, action="store"
    )

    args = parser.parse_args()

    asyncio.run(main(args))
