# https://docs.python.org/3/library/unittest.html

import datetime
import tempfile
import unittest
from threading import Thread
from typing import Any
from unittest.mock import MagicMock

import pytz
import redis
from fakeredis import TcpFakeServer
from geopy.geocoders import Nominatim

from fingr.config import load_filtered_list, random_message
from fingr.formatting import (
    format_meteogram,
    format_oneliner,
    print_meteogram_header,
    print_units,
    sun_up,
)
from fingr.location import get_timezone, resolve_location
from fingr.server import service_usage
from fingr.utils import clean_input, wind_direction
from fingr.weather import calculate_wind_chill

verbose = True

# Initialize geolocator for tests
geolocator = Nominatim(user_agent="fingr_test", timeout=3)


def make_mock_interval(
    temperature: float = 5.0,
    wind_speed: float = 3.0,
    wind_from_direction: float = 180.0,
    precipitation: float = 0.0,
    symbol_code: str = "clearsky_day",
    start_time: datetime.datetime | None = None,
) -> Any:
    """Create a mock forecast interval."""
    if start_time is None:
        start_time = datetime.datetime(2024, 1, 15, 12, 0, 0)

    interval = MagicMock()
    interval.start_time = start_time
    interval.symbol_code = symbol_code

    def make_var(value: float, unit: str = "") -> Any:
        var = MagicMock()
        var.value = value
        return var

    interval.variables = {
        "air_temperature": make_var(temperature),
        "wind_speed": make_var(wind_speed),
        "wind_from_direction": make_var(wind_from_direction),
        "precipitation_amount": make_var(precipitation),
    }
    return interval


def make_mock_forecast(
    place_name: str = "Oslo",
    num_hours: int = 10,
    temperature: float = 5.0,
    symbol_code: str = "clearsky_day",
) -> Any:
    """Create a mock Forecast object with num_hours intervals."""
    forecast = MagicMock()
    forecast.place.name = place_name

    base_time = datetime.datetime(2024, 1, 15, 6, 0, 0)
    intervals = [
        make_mock_interval(
            temperature=temperature + (i % 3),
            wind_speed=3.0,
            wind_from_direction=180.0,
            precipitation=0.0,
            symbol_code=symbol_code,
            start_time=base_time + datetime.timedelta(hours=i),
        )
        for i in range(num_hours)
    ]
    forecast.data.intervals = intervals
    forecast.json = {
        "data": {
            "properties": {
                "timeseries": [
                    {"data": {"next_6_hours": {"summary": {"symbol_code": symbol_code}}}}
                ]
            }
        }
    }
    return forecast


class TestServerMethods(unittest.TestCase):
    def test_wind_direction(self):
        """Test results from wind direction"""
        symbol = wind_direction(123)
        self.assertEqual(symbol, "SE")
        symbol = wind_direction(0)
        self.assertEqual(symbol, " N")
        symbol = wind_direction(290)
        self.assertEqual(symbol, " W")
        symbol = wind_direction(171)
        self.assertEqual(symbol, " S")
        symbol = wind_direction(333)
        self.assertEqual(symbol, "NW")

    def test_clean_input(self):
        """Test results from clean_input"""
        output = clean_input(";:")
        self.assertNotIn(";", output)

        output = clean_input("Ås")
        self.assertIn("Å", output)

    def test_resolve_location(self):
        """Test results from resolve_location"""
        server_address = ("127.0.0.1", 16379)
        server = TcpFakeServer(server_address)
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()

        r = redis.Redis(host=server_address[0], port=server_address[1])

        latitude, longitude, address, cached = resolve_location(r, geolocator, data="Oslo/Norway")
        self.assertEqual(latitude, 59.9133301)
        self.assertEqual(longitude, 10.7389701)
        self.assertEqual(address, "Oslo, Norway")

    def test_random_message(self):
        msglist = ["one", "two", "three"]
        msg1 = msg2 = None
        counts = 0
        while msg1 is None and msg2 is None and counts < 100:
            counts += 1
            msg1 = random_message(msglist)
            msg2 = random_message(msglist)
            if msg1 != msg2:
                break

        self.assertIn(msg1.strip().replace("[", "").replace("]", ""), msglist)

    def test_get_timezone(self):
        tz = get_timezone(lat=59, lon=11)
        # pytz timezone objects have a 'zone' attribute
        self.assertEqual(tz.zone, "Europe/Oslo")  # type: ignore[attr-defined]

    def test_sun_up(self):
        dt = datetime.datetime.fromtimestamp(1727987676, tz=pytz.timezone("UTC"))
        test = sun_up(latitude=59, longitude=11, date=dt)
        self.assertFalse(test)


class TestCalculateWindChill(unittest.TestCase):
    def test_typical_values(self) -> None:
        """Wind chill should be lower than air temperature in cold windy conditions."""
        result = calculate_wind_chill(temperature=0.0, wind_speed=5.0)
        self.assertIsInstance(result, int)
        self.assertLess(result, 0)

    def test_no_wind(self) -> None:
        """With negligible wind, wind chill is close to air temperature."""
        result = calculate_wind_chill(temperature=10.0, wind_speed=0.0)
        self.assertIsInstance(result, int)

    def test_known_value(self) -> None:
        """Test a known wind chill calculation result."""
        # At -10°C and 10 m/s the formula yields a specific value
        result = calculate_wind_chill(temperature=-10.0, wind_speed=10.0)
        self.assertLess(result, -10)


class TestLoadFilteredList(unittest.TestCase):
    def test_loads_lines(self) -> None:
        """Should return non-comment, non-empty lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# comment\n\nline1\nline2\n")
            fname = f.name
        result = load_filtered_list(fname)
        self.assertEqual(result, ["line1", "line2"])

    def test_missing_file_returns_empty(self) -> None:
        """Should return empty list when file is missing."""
        result = load_filtered_list("/nonexistent/path/file.txt")
        self.assertEqual(result, [])

    def test_strips_whitespace(self) -> None:
        """Lines should be stripped of leading/trailing whitespace."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("  hello  \n")
            fname = f.name
        result = load_filtered_list(fname)
        self.assertEqual(result, ["hello"])


class TestPrintMeteogramHeader(unittest.TestCase):
    def test_contains_place_name(self) -> None:
        header = print_meteogram_header("Oslo", screenwidth=80)
        self.assertIn("Oslo", header)
        self.assertIn("Meteogram", header)

    def test_centered(self) -> None:
        header = print_meteogram_header("Oslo", screenwidth=80)
        # Header line (without newline) should be 80 chars
        self.assertEqual(len(header.rstrip("\n")), 80)


class TestPrintUnits(unittest.TestCase):
    def test_metric_units(self) -> None:
        graph: dict[int, str] = {0: "", 13: "", 15: "", 16: ""}
        result = print_units(
            graph,
            screenwidth=80,
            imperial=False,
            beaufort=False,
            windline=15,
            windstrline=16,
            timeline=13,
        )
        self.assertIn("'C", result[0])
        self.assertIn("m/s", result[16])

    def test_imperial_units(self) -> None:
        graph: dict[int, str] = {0: "", 13: "", 15: "", 16: ""}
        result = print_units(
            graph,
            screenwidth=80,
            imperial=True,
            beaufort=False,
            windline=15,
            windstrline=16,
            timeline=13,
        )
        self.assertIn("'F", result[0])
        self.assertIn("mph", result[16])

    def test_beaufort_units(self) -> None:
        graph: dict[int, str] = {0: "", 13: "", 15: "", 16: ""}
        result = print_units(
            graph,
            screenwidth=80,
            imperial=False,
            beaufort=True,
            windline=15,
            windstrline=16,
            timeline=13,
        )
        self.assertIn("Bft", result[16])


class TestFormatMeteogram(unittest.TestCase):
    def setUp(self) -> None:
        self.timezone = pytz.timezone("Europe/Oslo")
        self.forecast = make_mock_forecast(num_hours=10, temperature=5.0)

    def test_output_is_string(self) -> None:
        output = format_meteogram(self.forecast, lat=59.9, lon=10.7, timezone=self.timezone)
        self.assertIsInstance(output, str)

    def test_contains_place_name(self) -> None:
        output = format_meteogram(self.forecast, lat=59.9, lon=10.7, timezone=self.timezone)
        self.assertIn("Oslo", output)

    def test_contains_legend(self) -> None:
        output = format_meteogram(self.forecast, lat=59.9, lon=10.7, timezone=self.timezone)
        self.assertIn("Legend", output)

    def test_each_hour_has_temperature_entry(self) -> None:
        """Every hour in the timeline must have a corresponding temperature symbol."""
        num_hours = 8
        forecast = make_mock_forecast(
            num_hours=num_hours, temperature=5.0, symbol_code="clearsky_day"
        )
        output = format_meteogram(forecast, lat=59.9, lon=10.7, timezone=self.timezone)

        lines = output.splitlines()
        # Find the timeline (Hour) line
        timeline_line = next((line for line in lines if "Hour" in line), None)
        self.assertIsNotNone(timeline_line, "Timeline line not found in output")

        # Count hour entries: each hour is a 2-char block (padded) in the line
        # Timeline is built as "   " + (" " + hour) * n + " Hour"
        # Strip the label and leading padding
        time_part = timeline_line.replace(" Hour", "").strip()  # type: ignore[union-attr]
        # Each hour token is 3 chars wide (" HH")
        hour_count = len(time_part) // 3
        self.assertGreaterEqual(hour_count, 1)

        # Find the temperature/weather rows (rows that are not wind/time/legend rows)
        # These are rows with weather symbols (---, ^^^, ===, etc.)
        symbol_chars = {"=", "-", "^", "#", "V"}
        temp_rows = [
            line for line in lines if any(c in line for c in symbol_chars) and "Legend" not in line
        ]
        self.assertGreater(len(temp_rows), 0, "No temperature rows with weather symbols found")

        # Each temperature row that has content should have exactly hour_count symbol groups
        for row in temp_rows:
            # Strip the left axis (3 chars) and right axis (rain label)
            content = row[3 : 3 + hour_count * 3]
            # Ensure content length matches expected hours
            self.assertEqual(
                len(content), hour_count * 3, f"Row '{row}' does not have {hour_count} hour entries"
            )

    def test_imperial_output(self) -> None:
        output = format_meteogram(
            self.forecast, lat=59.9, lon=10.7, timezone=self.timezone, imperial=True
        )
        self.assertIn("'F", output)
        self.assertIn("mph", output)

    def test_beaufort_output(self) -> None:
        output = format_meteogram(
            self.forecast, lat=59.9, lon=10.7, timezone=self.timezone, beaufort=True
        )
        self.assertIn("Bft", output)

    def test_wind_chill_label(self) -> None:
        output = format_meteogram(
            self.forecast, lat=59.9, lon=10.7, timezone=self.timezone, wind_chill=True
        )
        self.assertIn("wind chill", output)

    def test_various_symbol_codes(self) -> None:
        """Test that different symbol codes produce valid output."""
        for symbol in ["partlycloudy_day", "cloudy", "heavyrain", "thunder", "fog", "fair_day"]:
            forecast = make_mock_forecast(num_hours=5, symbol_code=symbol)
            output = format_meteogram(forecast, lat=59.9, lon=10.7, timezone=self.timezone)
            self.assertIsInstance(output, str)
            self.assertGreater(len(output), 0)


class TestFormatOneliner(unittest.TestCase):
    def test_output_contains_place_and_time(self) -> None:
        timezone = pytz.timezone("Europe/Oslo")
        forecast = make_mock_forecast(place_name="Bergen", num_hours=3)
        output = format_oneliner(forecast, timezone=timezone)
        self.assertIn("Bergen", output)
        self.assertIn("next 6 hours", output)


class TestServiceUsage(unittest.TestCase):
    def test_contains_usage_info(self) -> None:
        output = service_usage()
        self.assertIn("finger", output)
        self.assertIn("Usage", output)

    def test_contains_graph_no(self) -> None:
        output = service_usage()
        self.assertIn("graph.no", output)


class TestResolveLocationCoordinates(unittest.TestCase):
    def test_parses_lat_lon(self) -> None:
        """Comma-separated coordinates should be parsed directly without geocoding."""
        server_address = ("127.0.0.1", 16380)
        server = TcpFakeServer(server_address)
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        r = redis.Redis(host=server_address[0], port=server_address[1])

        lat, lon, address, cached = resolve_location(r, None, data="59.9,10.7")
        self.assertAlmostEqual(lat, 59.9)
        self.assertAlmostEqual(lon, 10.7)
        self.assertFalse(cached)

    def test_negative_coordinates(self) -> None:
        """Negative coordinates should parse correctly."""
        server_address = ("127.0.0.1", 16381)
        server = TcpFakeServer(server_address)
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        r = redis.Redis(host=server_address[0], port=server_address[1])

        lat, lon, address, cached = resolve_location(r, None, data="-33.9,151.2")
        self.assertAlmostEqual(lat, -33.9)
        self.assertAlmostEqual(lon, 151.2)


class TestWindDirectionBoundaries(unittest.TestCase):
    def test_all_cardinal_directions(self) -> None:
        self.assertEqual(wind_direction(0), " N")
        self.assertEqual(wind_direction(45), "NE")
        self.assertEqual(wind_direction(90), " E")
        self.assertEqual(wind_direction(135), "SE")
        self.assertEqual(wind_direction(180), " S")
        self.assertEqual(wind_direction(225), "SW")
        self.assertEqual(wind_direction(270), " W")
        self.assertEqual(wind_direction(315), "NW")
        self.assertEqual(wind_direction(359), " N")

    def test_boundary_values(self) -> None:
        """Test exact boundary values between directions."""
        self.assertEqual(wind_direction(293), "NW")
        self.assertEqual(wind_direction(338), " N")
        self.assertEqual(wind_direction(23), "NE")
        self.assertEqual(wind_direction(68), " E")
        self.assertEqual(wind_direction(113), "SE")
        self.assertEqual(wind_direction(158), " S")
        self.assertEqual(wind_direction(203), "SW")
        self.assertEqual(wind_direction(248), " W")


class TestRandomMessage(unittest.TestCase):
    def test_empty_list_returns_empty_string(self) -> None:
        self.assertEqual(random_message([]), "")

    def test_single_item(self) -> None:
        result = random_message(["hello"])
        self.assertIn("hello", result)

    def test_result_is_wrapped(self) -> None:
        result = random_message(["test"])
        self.assertTrue(result.startswith("["))
        self.assertIn("]", result)


if __name__ == "__main__":
    unittest.main()
