# https://docs.python.org/3/library/unittest.html

import unittest
import datetime
import pytz
import fingr
from threading import Thread
from fakeredis import TcpFakeServer
import redis

verbose = True


class TestServerMethods(unittest.TestCase):

    def test_wind_direction(self):
        """Test results from wind direction"""
        symbol = fingr.wind_direction(123)
        self.assertEqual(symbol, "SE")
        symbol = fingr.wind_direction(0)
        self.assertEqual(symbol, " N")
        symbol = fingr.wind_direction(290)
        self.assertEqual(symbol, " W")
        symbol = fingr.wind_direction(171)
        self.assertEqual(symbol, " S")
        symbol = fingr.wind_direction(333)
        self.assertEqual(symbol, "NW")

    def test_clean_input(self):
        """Test results from clean_input"""
        output = fingr.clean_input(";:")
        self.assertNotIn(";", output)

        output = fingr.clean_input("Ås")
        self.assertIn("Å", output)

    def test_resolve_location(self):
        """Test results from resolve_location"""
        server_address = ("127.0.0.1", 16379)
        server = TcpFakeServer(server_address)
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()

        r = redis.Redis(host=server_address[0], port=server_address[1])

        latitude, longitude, address, cached = fingr.resolve_location(
            r, data="Oslo/Norway"
        )
        self.assertEqual(latitude, 59.9133301)
        self.assertEqual(longitude, 10.7389701)
        self.assertEqual(address, "Oslo, Norway")

    def test_random_message(self):
        msglist = ["one", "two", "three"]
        msg1 = msg2 = None
        counts = 0
        while msg1 is None and msg2 is None and counts < 100:
            counts += 1
            msg1 = fingr.random_message(msglist)
            msg2 = fingr.random_message(msglist)
            if msg1 != msg2:
                break

        if verbose:
            print("Count", counts)
        self.assertIn(msg1.strip().replace("[", "").replace("]", ""), msglist)

    def test_get_timezone(self):
        tz = fingr.get_timezone(lat=59, lon=11)
        self.assertEqual(tz.zone, "Europe/Oslo")

    def test_sun_up(self):
        dt = datetime.datetime.fromtimestamp(1727987676, tz=pytz.timezone("UTC"))
        test = fingr.sun_up(latitude=59, longitude=11, date=dt)
        self.assertFalse(test)


if __name__ == "__main__":
    unittest.main()
