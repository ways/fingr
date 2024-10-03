# https://docs.python.org/3/library/unittest.html

import unittest
import fingr
verbose = True

class TestServerMethods(unittest.TestCase):

    def test_wind_direction(self):
        ''' Test results from wind direction '''
        symbol = fingr.wind_direction(123)
        self.assertEqual (symbol, 'SE')
        symbol = fingr.wind_direction(0)
        self.assertEqual (symbol, ' N')
        symbol = fingr.wind_direction(290)
        self.assertEqual (symbol, ' W')
        symbol = fingr.wind_direction(171)
        self.assertEqual (symbol, ' S')
        symbol = fingr.wind_direction(333)
        self.assertEqual (symbol, 'NW')

    def test_clean_input(self):
        ''' Test results from clean_input '''
        output = fingr.clean_input(';:')
        self.assertNotIn (';', output)

        output = fingr.clean_input('Ås')
        self.assertIn ('Å', output)

    def test_resolve_location(self):
        ''' Test results from resolve_location '''
        latitude, longitude, address, cached = fingr.resolve_location(data = "Oslo/Norway")
        self.assertEqual (latitude, 59.9133301)

if __name__ == '__main__':
    unittest.main()
