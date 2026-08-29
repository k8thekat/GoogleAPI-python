"""Developer driver for GAP. Gitignored and NOT shipped in the package.

Run things by hand without having to spin up a REPL:

    python local.py -local          # run local_test()
    python local.py -local -debug   # ... with DEBUG logging
    python local.py -info           # INFO logging
    python local.py --upgrade <pkg> # uv sync -n --upgrade-package <pkg>

Reads `local.ini` for the token path and my Calendar IDs — copy
`local_example.ini` over to it before the first run. Both this file and
`local.ini` are gitignored.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Union

from gap import CalendarColorEnum, CalendarService, EventsDraft, LocalTimeZoneEnum

if TYPE_CHECKING:
    from argparse import Namespace

    from gap._types import EventsDraftTyped

LOGGER: logging.Logger = logging.getLogger()
LOG_PATH: Path = Path(__file__).parent.joinpath("logs")
TIMESTAMP_FORMAT = "%d/%m | %H:%M(%Z)"

# My gitignored dev config. Real Calendar IDs live in here, not in this file.
# Copy `local_example.ini` to `local.ini` if you do not have one yet.
CONFIG_PATH: Path = Path(__file__).parent.joinpath("local.ini")

# The Calendar I test against, as named in the ini's [GAP.Calendars] section.
DWEEB_FAMILY_NAME = "Dweeb Family"


class LogHandler:
    """Stdout plus a rotating file handler, so a long session leaves a trail."""

    def __init__(self, level: int = logging.INFO) -> None:
        LOG_PATH.mkdir(exist_ok=True)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt=TIMESTAMP_FORMAT,
        )

        stream = logging.StreamHandler(stream=sys.stdout)
        stream.setFormatter(formatter)

        rotating = TimedRotatingFileHandler(
            filename=LOG_PATH.joinpath("gap.log"),
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        rotating.setFormatter(formatter)

        LOGGER.setLevel(level)
        LOGGER.addHandler(stream)
        LOGGER.addHandler(rotating)


def build_test_draft(calendar_id: str) -> EventsDraft:
    """Build the throwaway Event I use to smoke test `create_event`.

    Parameters
    -----------
    calendar_id: :class:`str`
        The Calendar to hang the Event off of — see `CalendarService.resolve_calendar()`.

    Returns
    --------
    :class:`EventsDraft`
        The unsent draft.

    """
    data: EventsDraftTyped = {
        "summary": "Kat - Google API Test Event",
        "location": "Seattle, Washington",
        "description": "The answer to everything is 42....",
        "start": {"dateTime": (datetime.now(tz=UTC) + timedelta(hours=4)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
        "end": {"dateTime": (datetime.now(tz=UTC) + timedelta(hours=5)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
        "reminders": {"useDefault": True},
        "colorId": CalendarColorEnum.bold_red,
    }
    return EventsDraft(calendar_id=calendar_id, data=data)


def local_test() -> None:
    """Scratch space — put whatever you are poking at right now in here."""
    calendar = CalendarService.from_ini(file=CONFIG_PATH)
    print(calendar.get_calendar_list())

    # ⚠ This writes a real Event to a real calendar. Uncomment deliberately.
    # event = calendar.create_event(event=build_test_draft(calendar_id=calendar.resolve_calendar(name=DWEEB_FAMILY_NAME)))
    # print(event)
    # calendar.delete_event(event=event)


def upgrade(package: str) -> None:
    """Bump a single dependency via uv without touching the rest of the lock."""
    subprocess.run(args=["uv", "sync", "-n", "--upgrade-package", package], check=True)


class Launcher(argparse.Namespace):
    """The argparse namespace, typed so the attribute access below checks."""

    local: bool
    info: bool
    debug: bool
    upgrade: Union[str, None]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GAP developer driver.")
    parser.add_argument("-local", help="Run the local_test() function.", action="store_true")
    parser.add_argument("-info", help="Enable INFO logging.", action="store_true")
    parser.add_argument("-debug", help="Enable DEBUG logging.", action="store_true")
    parser.add_argument("--upgrade", help="Upgrade a single package via uv.", type=str, default=None)

    args: Namespace = parser.parse_args(namespace=Launcher())

    if args.debug:
        LogHandler(level=logging.DEBUG)
    elif args.info:
        LogHandler(level=logging.INFO)

    if args.upgrade is not None:
        upgrade(package=args.upgrade)

    if args.local:
        local_test()
