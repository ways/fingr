"""Utility functions for data processing and validation."""

import string


def wind_direction(deg: int) -> str:
    """Return compass direction from degrees."""
    symbol: str = ""

    if 293 <= deg < 338:
        symbol = "NW"
    elif 338 <= deg < 360:
        symbol = " N"
    elif 0 <= deg < 23:
        symbol = " N"
    elif 23 <= deg < 68:
        symbol = "NE"
    elif 68 <= deg < 113:
        symbol = " E"
    elif 113 <= deg < 158:
        symbol = "SE"
    elif 158 <= deg < 203:
        symbol = " S"
    elif 203 <= deg < 248:
        symbol = "SW"
    elif 248 <= deg < 293:
        symbol = " W"
    else:
        symbol = " ?"
    return symbol


def clean_input(data: str) -> str:
    """Only allow numbers, letters, and some special chars from user."""
    # Change sub score to space
    data = data.replace("_", " ")

    # TODO: include all weird characters for other languages
    SPECIAL_CHARS: str = "^-.,:/~¤£ øæåØÆÅéüÜÉýÝ"
    allowed_chars: str = string.digits + string.ascii_letters + SPECIAL_CHARS
    return "".join(c for c in data if c in allowed_chars)
