# Planning for a rewrite of finger weather service at graph.no

## Legacy components

* finger handler (source was never published) using SocketServer
* https://gitlab.com/larsfp/pyyrascii
* https://github.com/ways/pyyrlib
* https://github.com/ways/pyofflinefilecache

All in python 2. Looks up location via a one-time imported mysql database.

## Important features to keep
- [ ] Usage text
- [ ] Imperial units
- [ ] Caching forecast data (required by API)
- [ ] Caching location data

## Important features to add/improve

- [x] Better location searching (country -> city)
- [ ] Feels-like
- [ ] Better logging
- [x] Dates if period cross days
- [ ] Unit testing

## Features that can be dropped

- [ ] One-liner

## Show stoppers

- [x] Searching improvements may be dependent on changes to the library (library replaced)

## Nice to have

- [ ] Deny-list, for abusers
- [ ] Options like %, ~ and +
- [ ] Random message at bottom

## Techs

* Python3(.8)
* Pipenv https://pipenv.pypa.io/ for deps control
* geopy for location look-up via nominatim
* metno-locationforecast as met.no API lib

