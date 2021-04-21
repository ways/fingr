from pysolar.solar import *
import datetime

latitude = 59.206
longitude = 10.382

date = datetime.datetime(2021, 4, 20, 3, 13, 1, 130320, tzinfo=datetime.timezone.utc)
print(get_altitude(latitude, longitude, date))

from timezonefinder import TimezoneFinder

tf = TimezoneFinder()
latitude, longitude = 59.5061, 10.358
print(tf.timezone_at(lng=longitude, lat=latitude))  # returns 'Europe/Berlin'