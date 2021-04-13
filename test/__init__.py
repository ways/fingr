# https://docs.python.org/3/library/unittest.html

import unittest
import server
verbose = False

class TestServerMethods(unittest.TestCase):

    def test_wind_direction(self):
        ''' Test results from wind direction '''
        symbol = server.wind_direction(123)
        self.assertEqual (symbol, ' E')

    def test_print_time(self):
        ''' Test results from print_time '''
        time = server.print_time()
        self.assertIn ('20', time)

    def test_clean_input(self):
        ''' Test results from clean_input '''
        output = server.clean_input(';:')
        self.assertNotIn (';', output)

        output = server.clean_input('Ås')
        self.assertIn ('Å', output)

    def test_resolve_location(self):
        ''' Test results from resolve_location '''
        latitude, longitude, address = server.resolve_location(data = "Oslo/Norway")
        self.assertEqual (latitude, 59.9133301)

