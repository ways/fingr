#!/usr/bin/env python3

import sys
import getopt
import logging
import asyncio

version = 1
port=79

async def handle_request(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')

    logging.info(f"{addr!r} Received: {message!r}")

    logging.info(f"{addr!r} Sent: {message!r}")
    writer.write(data)
    await writer.drain()

    logging.info("{addr!r} Closing connection")
    writer.close()

async def main():
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
