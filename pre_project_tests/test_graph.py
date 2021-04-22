from metno_locationforecast import Place, Forecast
new_york = Place("Oslo/Norway", 59, 10)
ny_forecast = Forecast(new_york, "fingr/1.0 https://graph.no")
ny_forecast.update()

import server

response = server.format_meteogram(ny_forecast)
print (response)
