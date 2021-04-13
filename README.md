# Graph.no finger weather

Finger server, serving weather forcast

An ascii version of Yr.no's meteogram https://www.yr.no/en/forecast/graph/1-72837/Norway/Oslo/Oslo/Oslo

## Usage

Finger is supported on all major platforms (Windows, OS X, Linux, FreeBSD, Android, ...). Open up your terminal (or cmd.exe on Windows).

If you don't have finger available, but have some standard shell tools, try one of the following:

    echo oslo|nc graph.no 79
    telnet graph.no 79 (and then type oslo)

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

* Python3(.8)
* Pipenv https://pipenv.pypa.io/ for deps control
* geopy for location look-up via nominatim
* metno-locationforecast as met.no API lib

## More

* First version: https://github.com/ways/pyyrascii
* Second version, due to API changes: https://github.com/ways/fingr/

See legacy.txt for the transition from pyyrascii to this.
