#!/usr/bin/env python3

import sys
import getopt
import logging
import asyncio

version = 1
port=79

async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')

    logging.info(f"Received {message!r} from {addr!r}")

    logging.info(f"Send: {message!r}")
    writer.write(data)
    await writer.drain()

    logging.info("Closing the connection")
    writer.close()

async def main():
    server = await asyncio.start_server(
        handle_echo, '0.0.0.0', port)

    addr = server.sockets[0].getsockname()
    logging.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


if __name__ == "__main__":

    try:
        opts, args = getopt.getopt(sys.argv,"hp:")
    except getopt.GetoptError:
        print (f'{sys.argv[0]} -p <port number>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print (f'{sys.argv[0]} -h')
            sys.exit()
        if opt == '-p':
            port = arg
            logging.info(f'Port set to {port}')

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
