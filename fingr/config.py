"""Configuration loading utilities."""

import logging
import os
import secrets
from typing import List

logger = logging.getLogger(__name__)


def load_user_agent() -> str:
    """Load user agent string from file. Met.no requires a contact address as user agent."""
    uafile: str = "useragent.txt"

    try:
        with open(uafile, encoding="utf-8") as f:
            for line in f:
                return line.strip()
        logger.info("Read useragent file <%s>", uafile)
    except FileNotFoundError:
        logger.warning(
            "Unable to read useragent file <%s>. This is required by upstream API. You risk getting your IP banned.",
            uafile,
        )
    return "default fingr useragent"


def load_motd_list() -> List[str]:
    """Load message of the day list from file."""
    motdfile: str = "motd.txt"
    motdlist: List[str] = []
    count: int = 0

    try:
        with open(motdfile, encoding="utf-8") as f:
            for line in f:
                count += 1
                line = line.strip()
                if line.startswith("#"):
                    continue
                if len(line) == 0:
                    continue
                motdlist.append(line.strip())

        logger.info("Read motd file with <%s> lines.", count)
    except FileNotFoundError as err:
        logger.warning("Unable to read motd list, <%s/%s>. Warning: %s", os.getcwd(), motdfile, err)

    return motdlist


def random_message(messages: List[str]) -> str:
    """Pick a random message of the day."""
    if len(messages) == 0:
        return ""
    return "[" + messages[secrets.randbelow(len(messages))] + "]\n"


def load_deny_list() -> List[str]:
    """Load list of IPs to deny service from file."""
    denyfile: str = "deny.txt"
    denylist: List[str] = []
    count: int = 0

    try:
        with open(denyfile, encoding="utf-8") as f:
            for line in f:
                count += 1
                line = line.strip()
                if line.startswith("#"):
                    continue
                if len(line) == 0:
                    continue
                denylist.append(line.strip())

        logger.info("Read denylist with %s lines.", count)
    except FileNotFoundError as err:
        logger.warning("Unable to read deny list, <%s/%s>. Warning: %s", os.getcwd(), denyfile, err)

    return denylist
