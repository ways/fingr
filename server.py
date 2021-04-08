#!/usr/bin/env python3

import sys
import getopt
import logging
import asyncio

import redis # Cache data in redis
r = redis.Redis()

from yr.libyr import Yr

version = 1
port=7979
cache_time = False

def clean_input (data):
    # TODO
    return data

def resolve_location(data):
    ''' Get a valid Yr location from name.
        Return status and yr location, i.e. True, 'Norge/Oslo/Oslo/Oslo'
    '''

    # TODO
    if 'oslo' in data:
        return True, 'Norge/Oslo/Oslo/Oslo'
    else:
        return False, ''

def fetch_weather(location):
    ''' Get forecast data from cache, or from Yr, then update cache. '''
    # TODO check cache timestamp

    weather_data = r.get(location)
    if weather_data:
        return weather_data

    weather = Yr(location_name=location, forecast_link='forecast_hour_by_hour')
    r.mset({location: weather.forecast()})

    return weather.forecast()

async def handle_request(reader, writer):
    data = await reader.read(30)
    user_input = clean_input(data.decode())
    addr = writer.get_extra_info('peername')
    response = ''

    logging.info(f"{addr!r} Received: {user_input!r}")

    location_status, location = resolve_location(user_input)
    if not location_status:
        response += 'Location <%s> not found.' % user_input
    else:
        weather_data = fetch_weather(location)
        response = weather_data

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
