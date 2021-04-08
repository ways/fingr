#!/usr/bin/env python3

import sys
import getopt
import logging
import asyncio
import math

__version__ = '2021-04'
__url__ = 'https://github.com/ways/fingr'
__license__ = 'GPL License'
port=7979
cache_time = False
input_limit = 30
user_agent = "fingr/1.0 https://graph.no"

from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent=user_agent)

from metno_locationforecast import Place, Forecast

def wind_direction (deg):
    ''' Return compass direction from degrees '''
    # TODO: increase resolution

    symbol = ''

    if deg < 315 and deg > 45:
        symbol = 'N'
    elif deg < 45 and deg > 135:
        symbol = 'E'
    elif deg < 135 and deg > 225:
        symbol = 'S'
    #elif deg < 225 and deg > 315:
    else:
        symbol = 'W'

    return symbol

def clean_input (data):
    # TODO
    return data

def resolve_location(data = "Oslo/Norway"):
    ''' Get a coordinate from location name.
        Return lat, long.
    '''

    coordinate = geolocator.geocode(data)
    logging.info(f"Resolved: {data} to {coordinate.address}.")
    return coordinate.latitude, coordinate.longitude, coordinate.address

def fetch_weather(lat, lon, address = ""):
    ''' Get forecast data '''

    location = Place(address, lat, lon)

    forecast = Forecast(location, user_agent=user_agent)
    forecast.update()

    return forecast

def format_meteogram(forecast, offset = 0, hourstep = 1, screenwidth = 80):
    ''' Format a meteogram from forcast data '''

    output = ''
    verbose = False
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
        # variables ['air_pressure_at_sea_level', 'air_temperature', 'cloud_area_fraction', 'relative_humidity', 'wind_from_direction', 'wind_speed', 'precipitation_amount'])
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
    time=[]

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
          if 0.0 != wind_speed else " O")

        # Wind strength on x axis
        graph[windstrline] += " " + '%2.0f' % wind_speed

        # Time on x axis
        spacer=' '
        date=str(interval.start_time)[0:10]
        hour=str(interval.start_time)[11:13] #2012-01-17T21:00
        graph[timeline] += spacer + hour

        # Create time range
        time.append(hour)

        # Date
        if '00' == hour:
            graph[timeline+1] += date
        else:
            graph[timeline+1] += '   '


        #for each y (temp) look for matching temp, draw graph
        for i in range(1, tempheight):
            #draw temp
            try:
                #parse out numbers to be compared
                temptomatch = temperature
                tempingraph = int(graph[i][:3].strip())

                if tempstep < -1: #TODO: this should scale higher than one step
                    temptomatch.append(temptomatch[0] - 1)

                if tempingraph == temptomatch:
                    # Match symbols from https://api.met.no/weatherapi/weathericon/2.0/documentation
                    if not interval.symbol_code:
                        graph[i] += "???"
                    elif interval.symbol_code in ['partlycloudy']: #partly
                        graph[i] += "^^^"
                    elif interval.symbol_code in ['cloudy']: #clouded
                        graph[i] += "==="
                    elif 'thunder' in interval.symbol_code: #lightning
                        graph[i] += "=V="
                    elif interval.symbol_code == ['fog']: #fog
                        graph[i] += "###"
                    elif interval.symbol_code == ['fair']: #light clouds
                        graph[i] += "=--"
                    elif interval.symbol_code in ['clearsky']: #clear
                        graph[i] += "---"
                    else: #Shouldn't hit this
                        graph[i] += "???"
                else:
                    graph[i] += "   "
            except KeyError:
                continue

            # #compare rain, and print
            # #TODO: scaling
            # if (rain != 0) and (rain > 10-i):
            #     if int(item['symbolnumber']) in [7,12]: #sleet
            #         rainsymbol = "!"
            #     elif int(item['symbolnumber']) in [8,13]: #snow
            #         rainsymbol = "*"
            #     else: #if int(item['symbolnumber']) in [5,6,9,10,11,14]: #rain
            #         rainsymbol = "|"

            #     if 0 > int(item['temperature']): #rain but cold
            #         rainsymbol = "*"

            #     if verbose:
            #         print("rainmax: ", rainmax,"i",i,"rain",rain)
            #     #if overflow, print number at top
            #     if rain > 10 and i == 1:
            #         rainsymbol = '%2.0f' % rain
            #         graph[i] = graph[i][:-2] + rainsymbol
            #     else:
            #         #print rainmax if larger than rain.
            #         if rainmax > rain:
            #             try:
            #                 graph[i-1] = graph[i-1][:-1] + "'"
            #             except UnboundLocalError:
            #                 print("Err2: " + str(item['symbolnumber']))
            #             except KeyError:
            #                 pass

            #         #print rain
            #         try:
            #             graph[i] = graph[i][:-1] + rainsymbol
            #         except UnboundLocalError:
            #             print("Err: " + str(item['symbolnumber']))

    #Legends
    graph[0] = " 'C" + str.rjust('Rain (mm) ', screenwidth-3)
    if imperial:
        graph[0] = " 'F" + str.rjust('Rain', screenwidth-9)
    graph[windline] +=    " Wind dir."
    graph[windstrline] += " Wind(mps)"
    graph[timeline] +=    " Hour"

    #header
    headline = "-= Meteogram for "
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
    data = await reader.read(input_limit)
    user_input = clean_input(data.decode())
    addr = writer.get_extra_info('peername')
    response = ''

    logging.info(f"{addr!r} Received: {user_input!r}")

    lat, lon, address = resolve_location(user_input)
    if not lat:
        response += 'Location <%s> not found.' % user_input
    else:
        weather_data = fetch_weather(lat, lon, address)
        response = format_meteogram(weather_data)

    writer.write(response)
    logging.info(f"{addr!r} Sent reply")
    await writer.drain()

    logging.info(f"{addr!r} Closing connection")
    writer.close()

async def main():
    # Add test data
    #     r.mset({"Norge/Oslo/Oslo/Oslo": """OrderedDict([('@from', '2021-04-08T03:00:00'), ('@to', '2021-04-08T04:00:00'), ('symbol', OrderedDict([('@number', '1'), ('@numberEx', '1'), ('@name', 'Clear sky'), ('@var', '01n')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '188.1'), ('@code', 'S'), ('@name', 'South')])), ('windSpeed', OrderedDict([('@mps', '1.1'), ('@name', 'Light air')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '2')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1008.2')]))])
    # OrderedDict([('@from', '2021-04-08T04:00:00'), ('@to', '2021-04-08T05:00:00'), ('symbol', OrderedDict([('@number', '1'), ('@numberEx', '1'), ('@name', 'Clear sky'), ('@var', '01n')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '169.6'), ('@code', 'S'), ('@name', 'South')])), ('windSpeed', OrderedDict([('@mps', '2.0'), ('@name', 'Light breeze')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '1')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1008.5')]))])
    # OrderedDict([('@from', '2021-04-08T05:00:00'), ('@to', '2021-04-08T06:00:00'), ('symbol', OrderedDict([('@number', '2'), ('@numberEx', '2'), ('@name', 'Fair'), ('@var', '02n')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '157.0'), ('@code', 'SSE'), ('@name', 'South-southeast')])), ('windSpeed', OrderedDict([('@mps', '1.5'), ('@name', 'Light air')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '0')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1008.6')]))])
    # OrderedDict([('@from', '2021-04-08T06:00:00'), ('@to', '2021-04-08T07:00:00'), ('symbol', OrderedDict([('@number', '3'), ('@numberEx', '3'), ('@name', 'Partly cloudy'), ('@var', '03n')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '140.2'), ('@code', 'SE'), ('@name', 'Southeast')])), ('windSpeed', OrderedDict([('@mps', '1.7'), ('@name', 'Light breeze')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '0')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1008.7')]))])
    # OrderedDict([('@from', '2021-04-08T07:00:00'), ('@to', '2021-04-08T08:00:00'), ('symbol', OrderedDict([('@number', '4'), ('@numberEx', '4'), ('@name', 'Cloudy'), ('@var', '04')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '141.7'), ('@code', 'SE'), ('@name', 'Southeast')])), ('windSpeed', OrderedDict([('@mps', '1.4'), ('@name', 'Light air')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '0')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1009.0')]))])
    # OrderedDict([('@from', '2021-04-08T08:00:00'), ('@to', '2021-04-08T09:00:00'), ('symbol', OrderedDict([('@number', '4'), ('@numberEx', '4'), ('@name', 'Cloudy'), ('@var', '04')])), ('precipitation', OrderedDict([('@value', '0')])), ('windDirection', OrderedDict([('@deg', '172.8'), ('@code', 'S'), ('@name', 'South')])), ('windSpeed', OrderedDict([('@mps', '1.3'), ('@name', 'Light air')])), ('temperature', OrderedDict([('@unit', 'celsius'), ('@value', '1')])), ('pressure', OrderedDict([('@unit', 'hPa'), ('@value', '1009.0')]))])
    # """})
    #print(r.get("Norge/Oslo/Oslo/Oslo"))

    server = await asyncio.start_server(
        handle_request, '0.0.0.0', port)

    addr = server.sockets[0].getsockname()
    logging.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

def help():
    print ("Arguments:\n-h\tHelp\n-p\tPort number (default 79, needs root)")
    sys.exit()


if __name__ == "__main__":

    try:
        options, remainder = getopt.getopt(sys.argv[1:],"hvp:")
    except getopt.GetoptError:
        print("Error, check arguments.")
        help()

    for opt, arg in options:
        if opt in ['-h', '--help']:
            help()
        if opt in ['-v', '--verbose']:
            logging.basicConfig(level=logging.INFO)
        if opt == '-p':
            port = arg
            logging.info(f'Port set to {port}')

    asyncio.run(main())
