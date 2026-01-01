"""Configuration loading utilities."""

import os
import secrets

from .log import get_logger

logger = get_logger(__name__)


def load_filtered_list(filename: str) -> list[str]:
    output: list = []
    try:
        with open(filename, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if len(line) == 0:
                    continue
                output.append(line.strip())
        logger.info("Read file", file=filename)
    except FileNotFoundError:
        logger.warning(
            "Unable to read file",
            file=filename,
        )
    return output


def load_user_agent() -> str:
    """Load user agent string from file. Met.no requires a contact address as user agent."""
    uafile: str = "useragent.txt"
    try:
        return load_filtered_list(uafile)[0]
    except ValueError:
        return "default fingr useragent"


def load_motd_list() -> list[str]:
    """Load message of the day list from file."""
    motdfile: str = "motd.txt"
    motdlist: list[str] = []

    try:
        motdlist = load_filtered_list(motdfile)
        logger.info("Read motd file", lines=len(motdlist))
    except FileNotFoundError as err:
        logger.warning("Unable to read motd list", cwd=os.getcwd(), file=motdfile, error=str(err))

    return motdlist


def random_message(messages: list[str]) -> str:
    """Pick a random message of the day."""
    if len(messages) == 0:
        return ""
    return "[" + messages[secrets.randbelow(len(messages))] + "]\n"


def load_deny_list() -> list[str]:
    """Load list of IPs to deny service from file."""
    denyfile: str = "deny.txt"
    denylist = load_filtered_list(denyfile)
    logger.info("Read denylist", lines=len(denylist))
    return denylist
