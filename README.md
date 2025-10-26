# Graph.no finger weather

Finger server, serving weather forcast

An ascii version of Yr.no's meteogram <https://www.yr.no/en/forecast/graph/1-72837/Norway/Oslo/Oslo/Oslo>

## Usage

If you just want to use the service, type: `finger oslo@graph.no` (replace oslo with your city). Finger is supported on all major platforms (Windows, MacOS, Linux, FreeBSD, Android, ...).

If you don't have finger available, but have some standard shell tools, try one of the following:

    echo oslo|nc graph.no 79
    telnet graph.no 79 (and then type oslo)

If you want to run the server yourself, read on below.

## Example output

    $ finger oslo@graph.no

            -= Meteogram for norway/oslo/oslo/oslo =-                    
    'C                                                                   Rain
    9                                                         --------- 
    8                                                   =-----          
    7                                                                   
    6                                                =--                
    5                                             ---                   
    4=--                                       ---                      
    3                                                                   
    2   ------                              ---                         
    1         ---------               ------                            
    0                  ---------                                        
        21 22 23 00 01 02 03 04 05 06_07_08_09_10_11_12_13_14_15_16_17_18 Hour
    
        N NE SE SE SE  S  S SE SE SE SE  S SW SW  S SW SW SW SW SW  S SE Wind dir.
        3  2  2  2  2  1  1  1  0  1  1  1  1  1  2  2  2  2  2  2  2  2 Wind(mps)

    Legend left axis:   - Sunny   ^ Scattered   = Clouded   =V= Thunder   # Fog
    Legend right axis:  | Rain    ! Sleet       * Snow

## Techs

* Python
* geopy for location look-up via nominatim
* metno-locationforecast as met.no API lib <https://github.com/Rory-Sullivan/metno-locationforecast/>
* redis for caching location lookups.
* [pysolar](https://pysolar.readthedocs.io/) for sun location

## Thanks

Contributions from:
* <https://github.com/neo954>
* <https://github.com/sotpapathe>

## Server install or running locally

Using uv (recommended):

* Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
* Install dependencies: `uv sync`
* Start redis: `docker run -it --rm --network host redis`
* Run fingr: `uv run python fingr.py`

Using Docker:

* With docker compose: `docker compose up`
* With Ubuntu-based image: `docker build -t fingr -f Dockerfile . && docker run -it --rm fingr`
* With distroless image: `docker build -t fingr -f Dockerfile.distroless . && docker run -it --rm fingr`

Or using pip:

* Start redis: `docker run -it --rm --network host redis`
* Install: `pip install -e .`
* Start fingr.py

If you don't see real IPs in the log, you may need to set this in /etc/docker/daemon.json:

    {
        "userland-proxy": false
    }

## Testing

    - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - Run `uv run tox`
    
Or with pip:
    
    - Install: `pip install -e .[dev]`
    - Run: `tox`

## More

* Previous version: <https://github.com/ways/pyyrascii>

See legacy.txt for the transition from pyyrascii to this.

## TODO

* Return error when no location found.
* Merge read_denylist, read_motdlist.
* Set default dirs for configs.
* Mount configs in docker compose file.
