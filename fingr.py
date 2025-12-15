#!/usr/bin/env python3
"""
Fingr - Weather via finger service.

This uses the modular structure from fingr/ package.
"""

import argparse
import asyncio
import logging
import warnings

# Quiet the specific pysolar leap-second message so it doesn't spam logs
warnings.filterwarnings(
    "ignore",
    message="I don't know about leap seconds after 2023",
    category=UserWarning,
    module=r"pysolar\.solartime",
)

from fingr import __license__, __url__, __version__
from fingr.server import start_server

def main() -> None:
    """Parse arguments and start the server."""
    parser = argparse.ArgumentParser(description="fingr")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-o", "--host", dest="host", default="127.0.0.1", action="store")
    parser.add_argument("-p", "--port", dest="port", default=7979, action="store")
    parser.add_argument(
        "-r", "--redis_host", dest="redis_host", default="localhost", action="store"
    )
    parser.add_argument("-n", "--redis_port", dest="redis_port", default=6379, action="store")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z"
    )

    asyncio.run(start_server(args))


if __name__ == "__main__":
    main()
