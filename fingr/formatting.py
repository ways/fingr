"""Output formatting for meteograms and forecasts."""

import datetime
import math
from typing import Any, Dict, List, Optional, Union

import pysolar.solar  # type: ignore[import-untyped]
import pytz  # type: ignore[import-untyped]

from .utils import wind_direction
from .weather import calculate_wind_chill

# Type aliases
Timezone = Union[datetime.tzinfo, type(pytz.UTC), type(pytz.timezone("UTC"))]

weather_legend: str = (
    "\nLegend left axis:   - Sunny   ^ Scattered   = Clouded   =V= Thunder   # Fog"
    + "\nLegend right axis:  | Rain    ! Sleet       * Snow\n"
)


def sun_up(latitude: float, longitude: float, date: datetime.datetime) -> bool:
    """Return symbols showing if sun is up at a place and time."""
    altitude: float = pysolar.solar.get_altitude(latitude, longitude, date)  # type: ignore[attr-defined]
    return 0 < altitude


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
            wind_speed_val: int = int(interval.variables["wind_speed"].value)
            temperature = calculate_wind_chill(temperature, wind_speed_val)

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
        wind_speed: int
        if wind_chill:
            wind_speed_for_chill: int = int(interval.variables["wind_speed"].value)
            temperature = calculate_wind_chill(temperature, wind_speed_for_chill)
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
        start_time: datetime.datetime = interval.start_time.replace(
            tzinfo=pytz.timezone("UTC")
        ).astimezone(timezone)
        date: str = start_time.strftime("%d/%m")
        hour: str = start_time.strftime("%H")
        if sun_up(latitude=lat, longitude=lon, date=start_time):
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
    next6: str = forecast.json["data"]["properties"]["timeseries"][0]["data"]["next_6_hours"]

    for interval in forecast.data.intervals:
        start_time = interval.start_time.replace(tzinfo=pytz.timezone("UTC")).astimezone(timezone)
        break

    return f"{start_time} {place} next 6 hours: {next6}"
