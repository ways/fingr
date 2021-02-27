# Planning for a rewrite of finger weather service at graph.no

## Legacy components

* finger handler (source was never published) using SocketServer
* https://gitlab.com/larsfp/pyyrascii
* https://github.com/ways/pyyrlib
* https://github.com/ways/pyofflinefilecache

All in python 2. Looks up location via a one-time imported mysql database.

## Important features to keep

## Important features to add/improve

* Better location searching (country -> city)
* Feels-like
* Proper logging
* Dates if period cross days
* Imperial units

## Features that can be dropped

* One-liner

## Show stoppers

* Searching improvements may be dependent on changes to the library

## Nice to have

* Deny-list, for abusers
* Random message at bottom

## Techs

* Python3(.8)
* Lib python-yr seems like a good match
* Pipenv https://pipenv.pypa.io/

