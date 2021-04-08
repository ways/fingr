from yr.libyr import Yr

weather = Yr(location_name='Norge/Oslo/Oslo/Oslo', forecast_link='forecast_hour_by_hour')
#weather = Yr(location_name='Norge/Oslo', forecast_link='forecast_hour_by_hour')
now = weather.now(as_json=True)

for forecast in weather.forecast():
    print(forecast)