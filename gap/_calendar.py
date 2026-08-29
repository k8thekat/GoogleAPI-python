"""Copyright (C) 2021-2026 Katelynn Cadwallader.

This file is part of GoogleAPI-Python.

GoogleAPI-Python is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option)
any later version.

GoogleAPI-Python is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
License for more details.

You should have received a copy of the GNU General Public License
along with GoogleAPI-Python; see the file COPYING.  If not, write to the Free
Software Foundation, 51 Franklin Street - Fifth Floor, Boston, MA
02110-1301, USA.

"""

# * Calendar data models.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Union

from ._enums import CalendarColorEnum, EventTransparencyEnum, EventTypeEnum
from ._utils import to_camel_case, to_snake_case

if TYPE_CHECKING:
    from ._enums import LocalTimeZoneEnum
    from ._types import EventsDraftTyped, EventTimeTyped, EventUserTyped, RemindersTyped

__all__ = (
    "CalendarList",
    "CalendarListEntry",
    "Events",
    "EventsDraft",
    "EventsList",
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class CalendarList:
    """A single Calendar entry on the user's calendar list.

    https://developers.google.com/calendar/api/v3/reference/calendarList

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one calendarList entry.

    """

    id: str  # The unique Calendar ID, this is what every other call wants.
    summary: str  # aka the calendar Title or Name.
    summary_override: str
    color_id: str
    hidden: bool
    selected: bool
    primary: bool
    deleted: bool
    default_reminders: list[dict[str, Union[str, int]]]
    notification_settings: dict[str, list[dict[str, str]]]

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'summary', '<no summary>')} | {getattr(self, 'id', '<no id>')} | {getattr(self, 'color_id', '')}"


class CalendarListEntry:
    """The list of Calendars available to the Google Account (shared, owned, etc).

    Tied to the response of `calendarList().list()`.
    https://developers.google.com/calendar/api/v3/reference/calendarList/list

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response of a `calendarList().list()` call.

    Attributes
    -----------
    events: list[:class:`CalendarList`]
        The calendars from the response `items` array.

    """

    kind: str
    etag: str
    next_page_token: Union[str, None]
    next_sync_token: Union[str, None]
    # ?SUGGESTION: Consider renaming to `calendars` in the next major version.
    #  Named `events` historically; actually holds the Calendar entries from `items`.
    events: list[CalendarList]

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        # Defaults first so a response missing these keys still leaves us usable.
        self.next_page_token = None
        self.next_sync_token = None
        self.events = []
        for key, value in kwargs.items():
            # `items` is the array of calendars; everything else is scalar metadata.
            if key == "items":
                self.events = [CalendarList(**entry) for entry in value]
            else:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'kind', '<no kind>')} | Calendars: {len(self.events)}"


class Events:
    """A single Calendar Event, built from an API response.

    https://developers.google.com/calendar/api/v3/reference/events

    Parameters
    -----------
    calendar_id: :class:`str`
        The ID of the Calendar this Event belongs to. Tracked locally because the
        API does not echo it back on the Event body.
    **kwargs: :class:`Any`
        The JSON response for one Event.

    """

    # ! Attributes tracked locally — must NOT be sent back to the API.
    _LOCAL_ATTRS: ClassVar[set[str]] = {"_raw", "calendar_id"}

    kind: str
    etag: str
    id: str
    calendar_id: str
    status: str
    html_link: str
    created: str  # ISO format
    updated: str  # ISO format
    summary: str
    creator: Union[EventUserTyped, dict[str, Any]]
    organizer: Union[EventUserTyped, dict[str, Any]]
    start: EventTimeTyped
    end: EventTimeTyped
    recurring_event_id: str
    original_start_time: Union[EventTimeTyped, None]
    transparency: str
    visibility: str
    ical_uid: str
    sequence: int
    attendees: list[EventUserTyped]
    attendees_omitted: bool
    extended_properties: dict[str, dict[str, str]]
    description: Union[str, None]
    location: Union[str, None]
    reminders: RemindersTyped
    color_id: Union[CalendarColorEnum, None]

    def __init__(self, calendar_id: str, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.calendar_id = calendar_id
        # Optional fields the __repr__ reads; default them so a sparse response
        # does not blow up on attribute access.
        self.description = None
        self.location = None
        self.color_id = None
        self.start = {}
        self.end = {}
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __lt__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id < other.id

    def __repr__(self) -> str:
        temp: list[str] = [
            f"Title: {getattr(self, 'summary', '<no title>')} | ID: {getattr(self, 'id', '<no id>')}",
            f"Start: {self.start.get('date', self.start.get('dateTime'))}",
            f"End: {self.end.get('date', self.end.get('dateTime'))}",
            f"Description: {self.description}",
            f"Location: {self.location}",
            f"CalendarID: {self.calendar_id}",
        ]
        return "\n".join(temp)

    def to_dict(self) -> dict[str, Any]:
        """Build the API request body for this Event.

        Strips our locally tracked attributes (`_raw`, `calendar_id`) — the API
        rejects or ignores unknown fields and we should not be sending them — and
        puts the field names back into Google's camelCase.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The Event body suitable for `events().insert()` / `events().update()`.

        """
        return {to_camel_case(key): value for key, value in self.__dict__.items() if key not in self._LOCAL_ATTRS}


class EventsList:
    """The response of an `events().list()` call.

    https://developers.google.com/calendar/api/v3/reference/events/list

    Parameters
    -----------
    calendar_id: :class:`str`
        The ID of the Calendar these Events belong to.
    **kwargs: :class:`Any`
        The JSON response of the list call.

    Attributes
    -----------
    events: list[:class:`Events`]
        The Events from the response `items` array.

    """

    kind: str
    etag: str
    summary: str
    description: str
    updated: str  # ISO format
    time_zone: str
    access_role: str
    default_reminders: list[dict[str, Union[str, int]]]
    next_page_token: str
    next_sync_token: str
    events: list[Events]
    calendar_id: str

    def __init__(self, calendar_id: str, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.calendar_id = calendar_id
        # Build the Events once, up front. Doing this inside the key loop meant a
        # response where `items` was not the last key wiped the list back out.
        self.events = [Events(calendar_id=calendar_id, **entry) for entry in kwargs.get("items", [])]
        for key, value in kwargs.items():
            if key != "items":
                setattr(self, to_snake_case(key), value)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Any:
        return iter(self.events)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "\n\n".join(repr(event) for event in self.events)


class EventsDraft:
    """An Event to be created via :meth:`gap.services.CalendarService.create_event`.

    Parameters
    -----------
    calendar_id: :class:`str`
        The ID of the Calendar to create the Event on.
    data: :class:`EventsDraftTyped`
        The Event fields. `start` and `end` are required and are validated on build.

    Notes
    ------
    summary:
        The Title for the Event.
    description:
        The Description for the Event.
    color_id:
        The color for the Event, by default :attr:`CalendarColorEnum.bold_red`.
    event_type:
        The Type of Event, by default :attr:`EventTypeEnum.default`.
    id:
        Generated by the Google API when the Event is inserted; you rarely set this.
    location:
        Where the Event takes place. A Google Maps style address.
    transparency:
        Whether the Event blocks time on the calendar. See :class:`EventTransparencyEnum`.
    reminders:
        Event specific reminders, max 5 overrides. Defaults to the Calendar's defaults.
    start / end:
        You MUST have either a `date` or a `dateTime`; `timeZone` is required with `dateTime`.

    """

    # ! `calendar_id` is ours, not the API's — keep it out of the request body.
    _LOCAL_ATTRS: ClassVar[set[str]] = {"calendar_id"}

    calendar_id: str
    summary: str
    end: EventTimeTyped
    start: EventTimeTyped
    color_id: CalendarColorEnum
    description: str
    event_type: EventTypeEnum
    id: Union[str, None]
    location: Union[str, None]
    transparency: EventTransparencyEnum
    reminders: RemindersTyped

    def __init__(self, calendar_id: str, data: EventsDraftTyped) -> None:
        self.calendar_id = calendar_id
        # Defaults, overwritten by anything the caller actually passed.
        self.color_id = CalendarColorEnum.bold_red
        self.event_type = EventTypeEnum.default
        self.reminders = {"useDefault": True}

        for key, value in data.items():
            # `EventsDraftTyped` is the API's own camelCase shape, but a snake_case key
            # passes through this unchanged — so either spelling works at the call site.
            attribute: str = to_snake_case(key)
            if attribute in {"start", "end"} and isinstance(value, dict):
                self.validate_keys(attribute=attribute, data=value)
            setattr(self, attribute, value)

    def __repr__(self) -> str:
        return f"Draft: {getattr(self, 'summary', '<no title>')} | Calendar: {self.calendar_id}"

    def to_dict(self) -> dict[str, Any]:
        """Build the API request body for this draft, back in Google's camelCase.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The Event body suitable for `events().insert()`.

        """
        return {to_camel_case(key): value for key, value in self.__dict__.items() if key not in self._LOCAL_ATTRS}

    def validate_keys(self, attribute: str, data: Union[EventTimeTyped, dict[str, Any]]) -> None:
        """Validate the keys of an :class:`EventTimeTyped` before we send it.

        Google rejects these combinations with an opaque 400, so we catch them here.

        Parameters
        -----------
        attribute: :class:`str`
            The attribute being validated; used for the error message.
        data: :class:`EventTimeTyped` | :class:`dict`
            The datastructure to validate.

        Raises
        -------
        :exc:`ValueError`
            You must have the key value of `timeZone` alongside `dateTime`.
        :exc:`ValueError`
            You must have the key value `date` or `dateTime`.
        :exc:`ValueError`
            You cannot have both `date` and `dateTime` keys.

        """
        has_date: Union[str, None] = data.get("date", None)
        has_datetime: Union[str, None] = data.get("dateTime", None)
        has_timezone: Union[LocalTimeZoneEnum, str, None] = data.get("timeZone", None)

        # A datetime with no timezone is ambiguous; the API will not guess for us.
        if has_datetime is not None and has_timezone is None:
            raise ValueError(f"You must have the key value of `timeZone` inside your {attribute}.")

        # We need something to anchor the Event to a day.
        if has_date is None and has_datetime is None:
            raise ValueError(f"You must have the key value `date` or `dateTime` inside your {attribute}.")

        # Both is contradictory — an all-day date and a specific time.
        if has_date is not None and has_datetime is not None:
            raise ValueError(f"You cannot have both `date` and `dateTime` keys inside your {attribute}.")
