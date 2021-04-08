from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="graph.no")
location = geolocator.geocode("Oslo/Norway")

print(location.address)
print((location.latitude, location.longitude))
print(location.raw)