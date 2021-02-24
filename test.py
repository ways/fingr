from yr.libyr import Yr

weather = Yr(location_name='Norge/Oslo/Oslo/Oslo')
now = weather.now(as_json=True)

print(now)
