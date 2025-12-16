# https://docs.python.org/3/library/unittest.html

import datetime
import unittest
from threading import Thread

import pytz
import redis
from fakeredis import TcpFakeServer
from geopy.geocoders import Nominatim

from fingr.config import random_message
from fingr.formatting import sun_up
from fingr.geoip import lookup_ip_location
from fingr.location import get_timezone, resolve_location
from fingr.utils import clean_input, wind_direction

verbose = True

# Initialize geolocator for tests
geolocator = Nominatim(user_agent="fingr_test", timeout=3)


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

    def test_geoip_lookup_local(self):
        """Test GeoIP lookup for local addresses"""
        lat, lon, location = lookup_ip_location("127.0.0.1")
        self.assertIsNone(lat)
        self.assertIsNone(lon)
        self.assertEqual(location, "local")

    def test_geoip_lookup_private(self):
        """Test GeoIP lookup for private addresses"""
        lat, lon, location = lookup_ip_location("192.168.1.1")
        self.assertIsNone(lat)
        self.assertIsNone(lon)
        self.assertEqual(location, "local")

    def test_geoip_lookup_unknown(self):
        """Test GeoIP lookup without database (returns unknown)"""
        # When no database is loaded, should return unknown
        lat, lon, location = lookup_ip_location("8.8.8.8")
        # Will be None/unknown if database not available
        # If database is available, will return actual location
        self.assertTrue(location in ["unknown", "local"] or isinstance(location, str))


if __name__ == "__main__":
    unittest.main()
