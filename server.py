#!/usr/bin/env python3

import sys
import getopt
import logging
import asyncio
import math
import time
import string
from geopy.geocoders import Nominatim
from metno_locationforecast import Place, Forecast

__version__ = '2021-04'
__url__ = 'https://github.com/ways/fingr'
__license__ = 'GPL License'
port=7979
input_limit = 30
user_agent = "fingr/%s https://graph.no" % __version__

geolocator = Nominatim(user_agent=user_agent)

def wind_direction (deg):
    ''' Return compass direction from degrees '''
    # TODO: increase resolution

    symbol = ''

    if 315 < deg < 45:
        symbol = ' N'
    elif 45 < deg < 135:
        symbol = ' E'
    elif 135 < deg < 225:
        symbol = ' S'
    #elif 225 < deg < 315:
    else:
        symbol = ' W'

    return symbol

def print_time ():
    return time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(time.time()))

def clean_input (data):
    ''' Only allow numbers, letters, and some special chars from user '''

    # TODO: include all weird characters for other languages
    SPECIAL_CHARS = ',/ øæåØÆÅé'
    return ''.join(c for c in data if c in string.digits + string.ascii_letters + SPECIAL_CHARS)

def resolve_location(data = "Oslo/Norway"):
    ''' Get coordinates from location name.
        Return lat, long, name.
    '''

    coordinate = geolocator.geocode(data)
    if coordinate:
        return coordinate.latitude, coordinate.longitude, coordinate.address
    return None, None, 'No location found'

def fetch_weather(lat, lon, address = ""):
    ''' Get forecast data '''

    location = Place(address, lat, lon)

    forecast = Forecast(location, user_agent=user_agent)
    forecast.update()

    return forecast

def format_meteogram(forecast, display_name = '<location>', offset = 0, hourstep = 1, screenwidth = 80):
    ''' Format a meteogram from forcast data '''

    output = ''
    imperial = False

    # Init graph
    graph=dict()
    tempheight = 10+1
    timeline = 13
    windline = 15
    windstrline = 16
    graph[timeline] = "   " #time
    graph[timeline+1] = "    " #date line
    graph[windline] = "   " #wind
    graph[windstrline] = "   " #wind strenght
    temphigh = -99
    templow = 99
    tempstep = -1
    hourcount = int((screenwidth-14)/3 + offset)

    # Rain in graph:
    rainheight = 10
    rainstep = -1
    rainhigh = 0 #highest rain on graph

    # First iteration to collect temperature and rain max, min.
    iteration = 0
    for interval in forecast.data.intervals:
        # variables ['air_pressure_at_sea_level', 'air_temperature', 
        # 'cloud_area_fraction', 'relative_humidity', 'wind_from_direction', 
        # 'wind_speed', 'precipitation_amount'])
        iteration += 1
        if iteration > hourcount:
            break

        temperature = int(interval.variables['air_temperature'].value)
        precipitation = 0
        try:
            precipitation = math.ceil(float(interval.variables['precipitation_amount'].value))
        except KeyError:
            pass

        if temperature > temphigh:
            temphigh = temperature

        if temperature < templow:
            templow = temperature

        if math.ceil(precipitation) > rainhigh:
            rainhigh = precipitation

    # Scale y-axis based on first iteration. default = -1
    if tempheight <= (temphigh - templow):
        tempstep = -2

    if temphigh == templow:
        templow = temphigh-1

    # Create temp range
    temps=[]
    for t in range(int(temphigh), int(templow)-1, tempstep):
        temps.append(t)

    # Extend temp range
    for t in range(0, tempheight):
        if len(temps)+1 < tempheight:
            if t%2 == 0: #extend down
                temps.append( temps[len(temps)-1] - abs(tempstep) )
            else: #extend up
                temps = [ temps[0] + abs(tempstep) ] + temps

    #write temps to graph
    for i in range(1, tempheight):
        try:
            graph[i] = str(temps[i-1]).rjust(3, ' ')
        except IndexError: #list empty
            pass

    #create rainaxis #TODO: make this scale
    rainaxis = []
    for r in range(rainheight, 0, rainstep):
        if r <= rainhigh: # + 1
            rainaxis.append('%2.0f mm ' % r)
        else:
            rainaxis.append(' ')

    #draw graph elements:
    iteration = 0
    for interval in forecast.data.intervals:
        temperature = int(interval.variables['air_temperature'].value)
        wind_from_direction = int(interval.variables['wind_from_direction'].value)
        wind_speed = int(interval.variables['wind_speed'].value)
        precipitation = 0
        try:
            rain = math.ceil(float(interval.variables['precipitation_amount'].value))
        except KeyError:
            pass

        iteration += 1
        if iteration > hourcount:
            break

        # Rain
        rainmax = 0 #max rain for this hour

        # Wind on x axis
        graph[windline] += " " + \
          (wind_direction(wind_from_direction) \
          if wind_speed != 0.0 else " O")

        # Wind strength on x axis
        graph[windstrline] += " " + '%2.0f' % wind_speed

        # Time on x axis
        spacer=' '
        date=str(interval.start_time)[8:10] + '/' + str(interval.start_time)[5:7]
        hour=str(interval.start_time)[11:13] #2012-01-17T21:00

        if hour == '01': # Date changed
            graph[timeline] = graph[timeline][:-2] + date
        else:
            graph[timeline] += spacer + hour

        #for each y (temp) look for matching temp, draw graph
        for i in range(1, tempheight): #draw temp
            try:
                #parse out numbers to be compared
                temptomatch = [temperature]
                tempingraph = int(graph[i][:3].strip())

                if tempstep < -1: #TODO: this should scale higher than one step
                    temptomatch.append(temptomatch[0] - 1)

                if tempingraph in temptomatch:
                    # Match symbols from https://api.met.no/weatherapi/weathericon/2.0/documentation
                    if not interval.symbol_code:
                        graph[i] += "   "
                    elif 'partlycloudy' in interval.symbol_code: #partly
                        graph[i] += "^^^"
                    elif 'cloudy' in interval.symbol_code or 'rain' in interval.symbol_code: #clouded, rain
                        graph[i] += "==="
                    elif 'thunder' in interval.symbol_code: #thunder
                        graph[i] += "=V="
                    elif 'fog' in interval.symbol_code: #fog
                        graph[i] += "###"
                    elif 'fair' in interval.symbol_code: #light clouds
                        graph[i] += "=--"
                    elif 'clearsky' in interval.symbol_code: #clear
                        graph[i] += "---"
                    else: #Shouldn't hit this
                        graph[i] += interval.symbol_code
                else:
                    graph[i] += "   "
            except KeyError:
                continue

            #compare rain, and print
            #TODO: scaling
            if (rain != 0) and (rain > 10-i):
                if 'sleet' in interval.symbol_code: #sleet
                    rainsymbol = "!"
                elif 'snow' in interval.symbol_code: #snow
                    rainsymbol = "*"
                else: #if int(item['symbolnumber']) in [5,6,9,10,11,14]: #rain
                    rainsymbol = "|"

                # if 0 > int(item['temperature']): #rain but cold
                #     rainsymbol = "*"

                # if verbose:
                #     print("rainmax: ", rainmax,"i",i,"rain",rain)

                #if overflow, print number at top
                if rain > 10 and i == 1:
                    rainsymbol = '%2.0f' % rain
                    graph[i] = graph[i][:-2] + rainsymbol
                else:
                    #print rainmax if larger than rain.
                    if rainmax > rain:
                        try:
                            graph[i-1] = graph[i-1][:-1] + "'"
                        except UnboundLocalError:
                            print("Err2: " + str(item['symbolnumber']))
                        except KeyError:
                            pass

                    #print rain
                    try:
                        graph[i] = graph[i][:-1] + rainsymbol
                    except UnboundLocalError:
                        print("Err: " + str(item['symbolnumber']))

    #Legends
    graph[0] = " 'C" + str.rjust('Rain (mm) ', screenwidth-3)
    if imperial:
        graph[0] = " 'F" + str.rjust('Rain', screenwidth-9)
    graph[windline] +=    " Wind dir."
    graph[windstrline] += " Wind(mps)"
    graph[timeline] +=    " Hour"

    #header
    headline = "-= Meteogram for %s =-" % display_name
    #    headline += " for the next " + str(hourcount) + " hours"
    output += str.center(headline, screenwidth) + "\n"

    #add rain to graph
    for i in range(1, tempheight):
        try:
            graph[i] += rainaxis[i-1]
        except IndexError:
            pass

    for k in sorted(graph.keys()):
        output += graph[k] + "\n"

    #legend
    output += "\nLegend left axis:   - Sunny   ^ Scattered   = Clouded   =V= Thunder   # Fog" +\
              "\nLegend right axis:  | Rain    ! Sleet       * Snow\n"

    return output

async def handle_request(reader, writer):
    ''' Receives connections and responds. '''

    data = await reader.read(input_limit)
    user_input = clean_input(data.decode())
    addr = writer.get_extra_info('peername')
    response = ''

    logging.info('%s - [%s] GET "%s"', addr[0], print_time(), user_input)

    lat, lon, address = resolve_location(user_input)
    if not lat:
        logging.info('%s - [%s] NOTFOUND "%s"', addr[0], print_time(), user_input)
        response += 'Location <%s> not found.' % user_input
    else:
        logging.info('%s - [%s] Resolved "%s" to "%s"', addr[0], print_time(), user_input, address)
        weather_data = fetch_weather(lat, lon, address)
        response = format_meteogram(weather_data, address)

    writer.write(response.encode())
    logging.info("%s - [%s] Reply %s bytes", addr[0], print_time(), len(response))
    await writer.drain()
    writer.close()

async def main():
    ''' Start server and bind to port '''

    logging.debug('%s Starting on port %s', print_time(), port)
    server = await asyncio.start_server(
        handle_request, '0.0.0.0', port)

    addr = server.sockets[0].getsockname()
    logging.debug('%s Ready to serve on address %s:%s', print_time(), addr[0], addr[1])

    async with server:
        await server.serve_forever()

def show_help():
    print ("Arguments:\n-h\tHelp\n-p\tPort number (default 7979)")
    sys.exit()


if __name__ == "__main__":

    try:
        options, remainder = getopt.getopt(sys.argv[1:],"hvp:")
    except getopt.GetoptError:
        print("Error, check arguments.")
        show_help()

    for opt, arg in options:
        if opt in ['-h', '--help']:
            show_help()
        if opt in ['-v', '--verbose']:
            logging.basicConfig(level=logging.INFO)
        if opt == '-p':
            port = arg
            logging.info('Port set to %s', port)

    asyncio.run(main())
