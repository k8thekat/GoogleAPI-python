from __future__ import annotations

import base64
from email.message import EmailMessage
from enum import IntEnum, StrEnum
from pprint import pprint
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Union

from googleapiclient.discovery import Resource

from ._enums import CalendarColorEnum, EventTypeEnum

if TYPE_CHECKING:
    from googleapiclient.http import HttpRequest

    from ._enums import (
        LocalTimeZoneEnum,
        MailLabelColorEnum,
        MailLabelListVisiblityEnum,
        MailMessageListVisibilityEnum,
        MailTypeEnum,
    )
    from ._types import EventListsTyped, EventsDraftTyped, EventsTyped, EventTimeTyped, EventUser, MailLabelTyped


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


class Events(Resource):
    """
    Events _summary_

    Parameters
    -----------
    Resource: :class:`_type_`
        _description_.
    dict: :class:`_type_`
        _description_.

    Returns
    --------
    :class:`_type_`
        _description_.
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
    start: EventTimeTyped  # = field(default=None) # TODO - Need to validate this cannot ever be "None".
    end: EventTimeTyped  # = field(default=None) # TODO - Need to validate this cannot ever be "None".
    recurringEventId: str
    originalStartTime: EventTimeTyped | None  # = field(default=None)
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
    colorId: Union[CalendarColorEnum, None] = None

    def __init__(self, calendar_id: str, **kwargs: EventsTyped) -> None:
        setattr(self, "_raw", kwargs)
        setattr(self, "calendar_id", calendar_id)

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __lt__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id < other.id

    def __repr__(self) -> str:
        temp = []
        temp.append(f"Title: {self.summary} | ID: {self.id}")
        temp.append(f"Start: {self.start.get('date', self.start.get('dateTime'))}")
        temp.append(f"End: {self.end.get('date', self.end.get('dateTime'))}")
        temp.append(f"Description: {self.description}")
        temp.append(f"Location: {self.location}")
        temp.append(f"CalendarID: {self.calendar_id}")
        return "\n".join(temp)

    def to_dict(self) -> dict:
        """
        Returns the dunder attribute `__dict__`.
        """

        return self.__dict__

    def list(self, **kwargs: Any) -> HttpRequest:
        """
        Sorts the current Events and returns itself.\n
        `from googleapiclient.http import HttpRequest`
        """
        return super().list(**kwargs)  # type: ignore

    def update(self, calendar_id: str | None = None, event_id: str | None = None, **kwargs: Any) -> HttpRequest:
        """
        https://developers.google.com/calendar/api/v3/reference/events/update
        """
        if calendar_id is None:
            calendar_id = self.calendar_id
        if event_id is None:
            event_id = self.id
        return super().update(calendarId=calendar_id, eventId=event_id, body=kwargs)  # type: ignore

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


class EventsList(Resource, dict):
    """
    https://developers.google.com/calendar/api/v3/reference/events/list#python

    Parameters
    -----------
    calendar_id: str
        The ID of the calendar with these events.

    **kwargs: EventListsTyped
        The JSON response.

    Attributes
    -----------
    events: list[Events]
        A list of Calendar Events.
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
        setattr(self, "_raw", kwargs)
        for key, value in kwargs.items():
            # items is a list of dictionaries
            temp = []
            if key == "items" and len(value) > 0:
                temp: list[Events] = [Events(calendar_id=calendar_id, **e) for e in value]  # type: ignore
            setattr(self, "events", temp)
            setattr(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "\n\n".join(event.__repr__() for event in self.events).strip(",")


class EventsDraft:
    """
    To be used to create a Google Calendar event via `CalendarService.create_event()`.

    Parameters
    -----------
    sumary: :class:`str`
        The Title for the Event.
    description: class:`str`
        The Description for the Event.
    color_id: :class:`CalendarColorEnum`, Optional
        The color for the calendar Event, defaults to :class:`CalendarColorEnum.bold_red`.
    event_type: :class:`EventTypeEnum`, Optional
        The Type of event this is, defaults to :class:`EventTypeEnum.default`.
    id: :class:`str` | None, Optional
        By default this is generated by the Google API when the Event is inserted.
    location: :class:`str` | None, Optional
        The location the Event is taking place. Google Maps type address.
    transparency: :class:`str`
        Whether the event blocks time on the calendar. Optional. Possible values are:
        - "opaque" - Default value. The event does block time on the calendar. This is equivalent to setting Show me as to Busy in the Calendar UI.
        - "transparent" - The event does not block time on the calendar. This is equivalent to setting Show me as to Available in the Calendar UI.
    reminders: :class:`dict`, Optional
        If the event doesn't use the default reminders, this lists the reminders specific to the event, or, if not set, indicates that no reminders are set for this event. The maximum number of override reminders is 5.
        - `useDefault`: Whether the default reminders of the calendar apply to the event.
    end: :class:`EventTime`
        You MUST have either a `date` or `dateTime`, the `timeZone` key must be included with `dateTime`.
    start: :class:`EventTime`
        You MUST have either a `date` or `dateTime` the `timeZone` key must be included with `dateTime`.
    """

    calendar_id: str
    summary: str
    end: EventTimeTyped
    start: EventTimeTyped
    color_id: CalendarColorEnum = CalendarColorEnum.bold_red
    description: str
    event_type: EventTypeEnum = EventTypeEnum.default
    id: str | None
    location: str | None
    transparency = Literal["opaque", "transparent"]
    reminders: ClassVar[dict] = {"useDefault": True}

    def __init__(self, calendar_id: str, data: EventsDraftTyped) -> None:
        self.calendar_id = calendar_id
        for key, value in data.items():
            if key == "color_id":
                setattr(self, "colorId", value)

            elif key == "event_type":
                setattr(self, "eventType", value)

            elif (key == "end" or key == "start") and isinstance(value, dict):
                self.validate_keys(attribute=key, data=value)
                setattr(self, key, value)

            else:
                setattr(self, key, value)

    def to_dict(self) -> EventsDraftTyped:
        """
        Returns the dunder attribute `__dict__`.
        """

        return self.__dict__  # type: ignore

    def validate_keys(self, attribute: str, data: EventTimeTyped | dict) -> None:
        """
        Validate's the keys of the data depending on the "key" parameter.

        - Currently supports :class:`EventTime`.

        Parameters
        -----------
        attribute: :class:`str`
            The attribute we are validating has the proper dict keys.
        data: :class:`EventTimeTyped | dict`
            The datastructure to validate.

        Raises
        -------
        :exc:`ValueError`
            You must have the key value of `timeZone` inside your attribute.
        :exc:`ValueError`
            You must have the key value `date` or `dateTime` inside your attribute.
        :exc:`ValueError`
            You cannot have both `date` and `dateTime` keys inside your attribute.
        """
        if attribute == "end" or (attribute == "start" and isinstance(data, dict)):
            has_date: str | None = data.get("date", None)
            has_datetime: str | None = data.get("dateTime", None)
            has_timezone: LocalTimeZoneEnum | str | None = data.get("timeZone", None)

            # If we have a datetime object and no timezone. So we can set the event to a proper timezone.
            if has_datetime is not None and has_timezone is None:
                raise ValueError("You must have the key value of `timeZone` inside your %s", attribute)

            # If we have no date or datetime. We need something to pick a day.
            if has_date is None and has_datetime is None:
                raise ValueError("You must have the key value `date` or `dateTime` inside your %s", attribute)

            # If we have a date and datetime, which is an error. We can't have both.
            elif has_date is not None and has_datetime is not None:
                raise ValueError("You cannot have both `date` and `dateTime` keys inside your %s", attribute)


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


class MailMessageHeader(dict):
    name: str  # The name of the header before the : separator. For example, To.
    value: str  # The value of the header after the : separator. For example, someuser@example.com.

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


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


class MailUser(Resource):
    def getProfile(self, **kwargs: Any) -> MailUserProfile:
        return super().getProfile(**kwargs)  # type: ignore

    def users(self, **kwargs: Any) -> MailUser:
        return super().users(**kwargs)  # type: ignore

    def labels(self, **kwargs: Any) -> MailUserLabel:
        return super().users().labels(**kwargs)  # type: ignore

    def drafts(self, **kwargs: Any) -> MailDraft:
        return super().users().drafts(**kwargs)  # type: ignore


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


class MailUserProfile(Resource):
    emailAddress: str
    messagesTotal: int
    threadsTotal: int
    historyId: str
