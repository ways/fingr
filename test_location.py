from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="graph.no")
location = geolocator.geocode("Bergen/Norway")

print(location.address)
print((location.latitude, location.longitude))
print(location.raw)