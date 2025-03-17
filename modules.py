from __future__ import annotations

from enum import IntEnum, StrEnum
from pprint import pprint
from typing import TYPE_CHECKING, Any, Union

from googleapiclient.discovery import Resource

if TYPE_CHECKING:
    from googleapiclient.http import HttpRequest

    from _types import EventListsTyped, EventsTyped, EventTime, EventUser


class LocalTimeZone(StrEnum):
    EST = "America/New_York"
    CST = "America/Chicago"
    MTN = "America/Denver"
    PST = "America/Los_Angeles"


class Events(Resource, dict):
    """
    https://developers.google.com/calendar/api/v3/reference/events
    """

    kind: str
    etag: str
    id: str
    calendar_id: str
    status: str
    htmlLink: str
    created: str  # ISO format
    updated: str  # ISO format
    summary: str
    creator: EventUser | dict  # = field(default_factory=dict[str, Any])
    organizer: EventUser | dict  # = field(default_factory=dict[str, Any])
    # start: Required[EventTime]  # = field(default=None)
    start: EventTime  # = field(default=None)
    end: EventTime | None  # = field(default=None)
    recurringEventId: str
    originalStartTime: EventTime | None  # = field(default=None)
    transparency: str
    visiblity: str
    iCalUID: str
    sequence: int
    attendees: list[EventUser]  # = field(default_factory=list)
    attendeesOmitted: bool
    extendedProperties: dict[str, dict[str, str]]
    description: Union[str, None] = None
    location: Union[str, None] = None
    reminders: dict[str, Union[str, bool, dict]]
    colorId: Union[CalendarColor, None] = None

    def __init__(self, calendar_id: str, **kwargs: EventsTyped) -> None:
        setattr(self, "calendar_id", calendar_id)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __lt__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id < other.id

    def __repr__(self) -> str:
        return f"Title: {self.summary}\nStart: {self.start.get('date', self.start.get('dateTime'))}\nDescription: {self.description}\nLocation: {self.location}\nCalendarID: {self.calendar_id}\n"

    def list(self, **kwargs: Any) -> HttpRequest:
        """
        Sorts the current Events and returns itself.\n
        `from googleapiclient.http import HttpRequest`
        """
        return super().list(**kwargs)  # type: ignore

    def update(self, **kwargs: Any) -> HttpRequest:
        """
        https://developers.google.com/calendar/api/v3/reference/events/update
        """
        return super().update(**kwargs)  # type: ignore

    def delete(self, **kwargs: Any) -> HttpRequest:
        """
        https://developers.google.com/calendar/api/v3/reference/events/delete
        """
        return super().delete(**kwargs)  # type: ignore

    def insert(self, **kwargs: Any) -> HttpRequest:
        """
        https://developers.google.com/calendar/api/v3/reference/events/insert

        Parameters
        -----------
        calendarId: :class:`str`
            The Google Calendar ID to Insert the event to.
        body: :class:`dict`
            The :class:`Events` passed in as a :class:`dict`. (Simply call `Events.__dict__`)


        Returns
        --------
        :class:`HttpRequest`
            _description_.
        """
        return super().insert(**kwargs)  # type: ignore

    def get(self, **kwargs: Any) -> HttpRequest:
        """
        https://developers.google.com/calendar/api/v3/reference/events/get
        """

        return super().get(**kwargs)  # type: ignore


# class EventsList(TypedDict, total=False):
class EventsList(Resource, dict):
    """
    https://developers.google.com/calendar/api/v3/reference/events/list#python
    """

    kind: str
    etag: str
    summary: str
    description: str
    updated: str  # ISO format
    timeZone: str
    accessRole: str
    defaultReminders: list[dict[str, Union[str, int]]]  # = field(default_factory=list)
    nextPageToken: str
    nextSyncToken: str
    now: str  # ISO format
    events: list[Events]
    calendar_id: str

    def __init__(self, calendar_id: str, **kwargs: EventListsTyped) -> None:
        setattr(self, "calendar_id", calendar_id)
        for key, value in kwargs.items():
            # items is a list of dictionaries
            temp = []
            if key == "items" and len(value) > 0:
                temp: list[Events] = [Events(calendar_id=calendar_id, **e) for e in value]  # type: ignore
            setattr(self, "events", temp)
            setattr(self, key, value)


# @dataclass(init=False, repr=False, match_args=False)
class Calendar(Resource):
    """
    https://developers.google.com/calendar/api/v3/reference/calendars
    """

    kind: str
    etag: str
    id: str
    summary: str
    description: str
    location: str
    timeZone: str  # ISO format
    conferenceProperties: dict[str, list[str]]

    def events(self) -> Events:
        """Returns a list of Google Calendar Events"""
        return super().events()  # type: ignore

    def calendarList(self) -> CalendarList:
        return super().calendarList()  # type: ignore


class CalendarList(Resource, dict):
    # class CalendarList(TypedDict, total=False):
    """
    The collection of calendars in the user's calendar list.\n
    https://developers.google.com/calendar/api/v3/reference/calendarList
    """

    # id: Required[str]
    # summary: Required[str]
    id: str  # unique Calendar ID for interaction.
    summary: str  # aka calendar Title or Name
    summaryOverride: str
    colorId: str
    hidden: bool
    selected: bool
    primary: bool
    deleted: bool
    defaultReminders: list[dict[str, Union[str, int]]]
    notificationSettings: dict[str, list[dict[str, str]]]

    def __init__(self, **kwargs: Any) -> None:
        # print("Building a CALENDAR LIST OBJECT...")
        # pprint(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore

    def __repr__(self) -> str:
        return f"{self.summary} | {self.id} | {self.colorId}"


# class CalendarListEntry(TypedDict, total=False):
class CalendarListEntry(Resource, dict):
    """
    aka The List of Calendars available to the Google Acocunt. (Shared, Owned, etc) tied to `CalendarList.list()`
    https://developers.google.com/calendar/api/v3/reference/calendarList/list
    """

    kind: str
    etag: str
    nextPageToken: Union[str, None] = None
    nextSyncToken: Union[str, None] = None
    # items: Required[list[CalendarList]]
    # items: list[CalendarList]
    events: list[CalendarList]

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            # items is a list of dictionaries
            if key == "items":
                # temp =
                setattr(self, "events", [CalendarList(**e) for e in value])
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"{self.kind} | Events: {self.events}\n"


class CalendarColor(IntEnum):
    blue = 1
    green = 2
    purple = 3
    red = 4
    yellow = 5
    orange = 6
    turquoise = 7
    gray = 8
    bold_blue = 9
    bold_green = 10
    bold_red = 11
