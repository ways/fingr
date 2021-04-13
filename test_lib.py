from metno_locationforecast import Place, Forecast
import datetime as dt

new_york = Place("Bergen/Norway", 60.3, 5.3)
ny_forecast = Forecast(new_york, forecast_type="complete", user_agent="fingr/1.0 https://graph.no")
ny_forecast.update()
# print(ny_forecast)

first_interval = ny_forecast.data.intervals[0]
print(first_interval)

# Access the interval's duration attribute.
print(f"Duration: {first_interval.duration} - {first_interval.symbol_code}")

print()  # Blank line

# Access a particular variable from the interval.
rain = first_interval.variables["precipitation_amount"]
print(rain)

# Access the variables value and unit attributes.
print(f"Rain value: {rain.value}")
print(f"Rain units: {rain.units}")

# Get a full list of variables available in the interval.
print(first_interval.variables.keys())

print(vars(ny_forecast.data).keys())