from __future__ import annotations

import base64
from email.message import EmailMessage
from enum import IntEnum, StrEnum
from pprint import pprint
from typing import TYPE_CHECKING, Any, ClassVar, Union

from googleapiclient.discovery import Resource

if TYPE_CHECKING:
    from googleapiclient.http import HttpRequest

    from _enums import (
        MailFormatEnum,
        MailLabelColorEnum,
        MailLabelListVisiblityEnum,
        MailMessageListVisibilityEnum,
        MailTypeEnum,
    )
    from _types import EventListsTyped, EventsTyped, EventTime, EventUser, MailLabelTyped


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


class MailUser(Resource):
    def getProfile(self, **kwargs: Any) -> MailUserProfile:
        return super().getProfile(**kwargs)  # type: ignore

    def users(self, **kwargs: Any) -> MailUser:
        return super().users(**kwargs)  # type: ignore

    def labels(self, **kwargs: Any) -> MailUserLabel:
        return super().users().labels(**kwargs)  # type: ignore

    def drafts(self, **kwargs: Any) -> MailDraft:
        return super().users().drafts(**kwargs)  # type: ignore


class MailUserProfile(Resource):
    emailAddress: str
    messagesTotal: int
    threadsTotal: int
    historyId: str


class MailUserLabel(Resource, dict):
    """
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels
    """

    id: str
    name: str
    messageListVisibility: MailMessageListVisibilityEnum
    labelListVisibility: MailLabelListVisiblityEnum
    type: MailTypeEnum
    messagesTotal: int
    messagesUnread: int
    threadsTotal: int
    threadsUnread: int
    color: MailLabelColorEnum

    def __init__(self, **kwargs: MailLabelTyped) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def list(self, **kwargs: Any) -> HttpRequest:
        """
        List of labels. Note that each label resource only contains an id, name, messageListVisibility, labelListVisibility, and type. The labels.get method can fetch additional label details.

        """
        return super().list(**kwargs)  # type: ignore

    def create(self, **kwargs: Any) -> HttpRequest:
        return super().create(**kwargs)  # type: ignore


class MailDraft(Resource, dict):
    id: str
    message: MailMessage

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key == "message":
                setattr(self, "message", MailMessage(draft_id=self.id, **value))
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f"Mail Draft: {self.id} | Mail Message: {self.message}"

    def create(self, **kwargs: Any) -> HttpRequest:
        return super().create(**kwargs)  # type: ignore

    def delete(self, **kwargs: Any) -> None:
        return super().delete(**kwargs)  # type: ignore

    def get(self, **kwargs: Any) -> HttpRequest:
        return super().get(**kwargs)  # type: ignore

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore

    def send(self) -> HttpRequest:
        return super().send()  # type: ignore

    def update(self, **kwargs: Any) -> HttpRequest:
        return super().update(**kwargs)  # type: ignore


class MailDraftList(Resource, dict):
    """
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/list
    """

    drafts: list[MailDraft]
    nextPageToken: str
    resultSizeEstimate: int


class MailMessage(EmailMessage, Resource, dict):
    """
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages
    """

    id: str
    draft_id: str
    threadId: str
    labelIds: list[str]
    snippet: str
    historyId: str
    internalDate: str
    payload: MailMessagePart
    sizeEstimate: int
    raw: str

    def __init__(self, draft_id: str = "", **kwargs: Any) -> None:
        setattr(self, "draft_id", draft_id)
        setattr(self, "raw", "")
        setattr(self, "payload", MailMessagePart())
        for key, value in kwargs.items():
            if key == "payload":
                setattr(self, key, MailMessagePart(**value))
            else:
                setattr(self, key, value)

    def to_email(
        self,
        to_email: str | list[str],
        from_email: str | list[str],
        subject: str = " ",
        body: str = " ",
    ) -> MailMessage:
        super().__init__()
        self.set_content(body)
        self["To"] = to_email
        self["From"] = from_email
        self["Subject"] = subject
        return self

    def to_base64(self) -> str:
        return base64.urlsafe_b64encode(self.as_bytes()).decode()

    def prepared(self) -> dict:
        """
        Returns a pre-formed dict with the passed in encoded EmailMessage.
        """
        return {"message": {"raw": self.to_base64()}}

    def update_email(self, body: str) -> MailMessage:
        subject = ""
        to_email = ""
        from_email = ""
        for e in self.payload.headers:
            if e.name == "Subject":
                subject: str = e.value
            if e.name == "To":
                to_email: str = e.value
            if e.name == "From":
                from_email: str = e.value

        return self.to_email(to_email=to_email, from_email=from_email, subject=subject, body=(self.payload.body.data + body))

    def __repr__(self) -> str:
        return f"Mail Message Details:\nID: {self.id}\nLabels: {self.labelIds}\nThread ID:{self.threadId}\nContent: {self.payload.body.data}"

    def __str__(self) -> str:
        """
        This is to overwrite :class:`EmailMessage` built-ins.
        """
        return self.__repr__()


class MailMessagePart(dict):
    partId: str
    mimeType: str
    headers: list[MailMessageHeader]
    body: MailMessageBody
    parts: list[MailMessagePart]
    filename: str

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key == "headers":
                setattr(self, key, [MailMessageHeader(**i) for i in value])
            elif key == "body":
                setattr(self, key, MailMessageBody(**value))
            else:
                setattr(self, key, value)


class MailMessageHeader(dict):
    name: str  # The name of the header before the : separator. For example, To.
    value: str  # The value of the header after the : separator. For example, someuser@example.com.

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class MailMessageBody(dict):
    attachmentId: str
    size: int
    data: str

    def __init__(self, **kwargs: Any) -> None:
        setattr(self, "data", "")
        for key, value in kwargs.items():
            if key == "data":
                setattr(self, key, base64.urlsafe_b64decode(value).decode())
            else:
                setattr(self, key, value)
