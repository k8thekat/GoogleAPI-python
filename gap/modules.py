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

# ---------------------------------------------------------------------------
# There are two kinds of class in this module and they must not be conflated:
#
# 1. `*Resource` shims — subclass `googleapiclient.discovery.Resource` purely so
#    the dynamically-built client typechecks. They are NEVER instantiated by us;
#    `build()` hands back real Resource objects at runtime. Their methods are
#    all `return super().<name>(**kwargs)  # type: ignore`.
#
# 2. Data models — plain classes built from a JSON response. They stash the
#    untouched payload on `_raw` and splat the rest onto attributes.
# ---------------------------------------------------------------------------

from __future__ import annotations

import base64
import re
from email.message import EmailMessage
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, Union

from googleapiclient.discovery import Resource

from ._enums import CalendarColorEnum, EventTransparencyEnum, EventTypeEnum

if TYPE_CHECKING:
    from googleapiclient.http import HttpRequest

    from ._enums import LocalTimeZoneEnum, MailLabelColorEnum, MailLabelListVisiblityEnum, MailMessageListVisibilityEnum, MailTypeEnum
    from ._types import EventsDraftTyped, EventTimeTyped, EventUserTyped, RemindersTyped

__all__ = (
    "CalendarList",
    "CalendarListEntry",
    "CalendarListResource",
    "CalendarResource",
    "Events",
    "EventsDraft",
    "EventsList",
    "EventsResource",
    "KeepNote",
    "KeepNoteDraft",
    "KeepNoteList",
    "KeepNotesResource",
    "MailDraft",
    "MailDraftList",
    "MailDraftsResource",
    "MailLabelsResource",
    "MailMessage",
    "MailMessageBody",
    "MailMessageHeader",
    "MailMessageList",
    "MailMessagePart",
    "MailMessagesResource",
    "MailUserLabel",
    "MailUserProfile",
    "MailUserResource",
    "MailUsersResource",
    "to_camel_case",
    "to_snake_case",
)


# ---------------------------------------------------------------------------
# Field name conversion.
#
# Google speaks camelCase on the wire; we expose snake_case attributes. Every data
# model converts on the way in, and the `to_dict()` / `prepared()` builders convert
# back on the way out — the API only ever sees its own spelling.
#
# The `_types.py` TypedDicts are the request bodies themselves, not our attributes,
# so they stay camelCase. The same goes for any raw dict we hold verbatim, such as
# `Events.start` or a Keep note `body`.
# ---------------------------------------------------------------------------
_CAMEL_BOUNDARY: re.Pattern[str] = re.compile(r"(?<!^)(?=[A-Z])")

# Fields we spell by hand instead of by the rule below, camelCase -> snake_case.
#
# This is about readability, not correctness: the rule round trips `iCalUID` losslessly,
# but only as `i_cal_u_i_d`, because it has no way to know `UID` is one acronym rather
# than three words. Anything that reads badly goes here. Both directions follow from the
# one entry — the reverse map is derived, not written out, so they cannot drift apart.
#
# The rule itself is its own inverse for every key shape these three APIs use, i.e.
# lowercase-first camelCase. It does NOT round trip a key that starts with a capital
# (`ABTest` -> `a_b_test` -> `aBTest`) or one that already contains an underscore
# (`some_key` -> `someKey`). Google sends neither; if that ever changes, the fix is an
# entry here rather than a new branch in the functions.
_IRREGULAR_FIELDS: dict[str, str] = {"iCalUID": "ical_uid"}
_IRREGULAR_FIELDS_INVERTED: dict[str, str] = {snake: camel for camel, snake in _IRREGULAR_FIELDS.items()}


# Field names are a small fixed set — a few dozen per API — so caching turns the whole
# conversion into a dict lookup after each one is first seen. The bound is there because
# the input is whatever keys a response arrived with, not something we control.
#
# What that costs: a cache is only correct while the function is pure. Both of these read
# `_IRREGULAR_FIELDS`, which is filled at import and never touched again — add an entry at
# runtime and anything already converted keeps its old answer until `cache_clear()`. It is
# also only free because these are module level functions; on a method `self` lands in the
# key and the cache pins every instance it ever saw, for the life of the process.
@lru_cache(maxsize=512)
def to_snake_case(field: str) -> str:
    """Convert one of Google's camelCase JSON keys into our attribute name.

    Parameters
    -----------
    field: :class:`str`
        The JSON key as it arrived, e.g. "nextPageToken".

    Returns
    --------
    :class:`str`
        The attribute name we store it under, e.g. "next_page_token". A key that is
        already snake_case, or a single lowercase word, comes back unchanged.

    """
    if field in _IRREGULAR_FIELDS:
        return _IRREGULAR_FIELDS[field]
    return _CAMEL_BOUNDARY.sub("_", field).lower()


# Cached on the same terms as `to_snake_case` above.
@lru_cache(maxsize=512)
def to_camel_case(field: str) -> str:
    """Convert one of our attribute names back into Google's camelCase JSON key.

    The exact inverse of :func:`to_snake_case`, so a response can be read in and
    sent back out without losing a field.

    Parameters
    -----------
    field: :class:`str`
        The attribute name, e.g. "next_page_token".

    Returns
    --------
    :class:`str`
        The JSON key Google expects, e.g. "nextPageToken".

    """
    if field in _IRREGULAR_FIELDS_INVERTED:
        return _IRREGULAR_FIELDS_INVERTED[field]
    head, *tail = field.split("_")
    return head + "".join(part.title() for part in tail)


# ---------------------------------------------------------------------------
# Resource shims — typing only.
# ---------------------------------------------------------------------------
class EventsResource(Resource):
    """Typing shim for the `events()` collection of the Calendar API.

    https://developers.google.com/calendar/api/v3/reference/events
    """

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]

    def insert(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().insert(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().get(**kwargs)  # type: ignore[misc]

    def update(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().update(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().delete(**kwargs)  # type: ignore[misc]


class CalendarListResource(Resource):
    """Typing shim for the `calendarList()` collection of the Calendar API.

    https://developers.google.com/calendar/api/v3/reference/calendarList
    """

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]


class CalendarResource(Resource):
    """Typing shim for the root Calendar v3 service returned by `build()`.

    https://developers.google.com/calendar/api/v3/reference/calendars
    """

    def events(self) -> EventsResource:
        """The Events collection."""
        return super().events()  # type: ignore[misc]

    def calendarList(self) -> CalendarListResource:
        """The CalendarList collection."""
        return super().calendarList()  # type: ignore[misc]


class MailDraftsResource(Resource):
    """Typing shim for `users().drafts()` of the Gmail API.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts
    """

    def create(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().create(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().delete(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().get(**kwargs)  # type: ignore[misc]

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]

    def send(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().send(**kwargs)  # type: ignore[misc]

    def update(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().update(**kwargs)  # type: ignore[misc]


class MailLabelsResource(Resource):
    """Typing shim for `users().labels()` of the Gmail API.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels
    """

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]

    def create(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().create(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().get(**kwargs)  # type: ignore[misc]


class MailMessagesResource(Resource):
    """Typing shim for `users().messages()` of the Gmail API.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages
    """

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().get(**kwargs)  # type: ignore[misc]


class MailUsersResource(Resource):
    """Typing shim for the `users()` collection of the Gmail API."""

    def getProfile(self, **kwargs: Any) -> HttpRequest:
        """The profile of this user."""
        return super().getProfile(**kwargs)  # type: ignore[misc]

    def labels(self, **kwargs: Any) -> MailLabelsResource:
        """The Labels collection for this user."""
        return super().labels(**kwargs)  # type: ignore[misc]

    def messages(self, **kwargs: Any) -> MailMessagesResource:
        """The Messages collection for this user."""
        return super().messages(**kwargs)  # type: ignore[misc]

    def drafts(self, **kwargs: Any) -> MailDraftsResource:
        """The Drafts collection for this user."""
        return super().drafts(**kwargs)  # type: ignore[misc]


class MailUserResource(Resource):
    """Typing shim for the root Gmail v1 service returned by `build()`."""

    def users(self, **kwargs: Any) -> MailUsersResource:
        """The Users collection."""
        return super().users(**kwargs)  # type: ignore[misc]


class KeepNotesResource(Resource):
    """Typing shim for the `notes()` collection of the Keep API.

    https://developers.google.com/workspace/keep/api/reference/rest/v1/notes
    """

    def create(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().create(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().get(**kwargs)  # type: ignore[misc]

    def list(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().list(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:  # noqa: D102
        return super().delete(**kwargs)  # type: ignore[misc]


class KeepResource(Resource):
    """Typing shim for the root Keep v1 service returned by `build()`."""

    def notes(self) -> KeepNotesResource:
        """The Notes collection."""
        return super().notes()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Calendar data models.
# ---------------------------------------------------------------------------
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

    # Attributes we track for our own use that must NOT be sent back to the API.
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

    # `calendar_id` is ours, not the API's — keep it out of the request body.
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


# ---------------------------------------------------------------------------
# Mail data models.
# ---------------------------------------------------------------------------
class MailMessageBody:
    """The body of one part of a Mail message.

    The API hands `data` back base64url encoded; we decode it on the way in.
    """

    attachment_id: str
    size: int
    data: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.data = ""
        for key, value in kwargs.items():
            if key == "data":
                # Senders are not obliged to give us valid UTF-8, and this runs during
                # `MailMessage(**payload)` construction — so an un-replaced byte takes down
                # the whole response, not just this part. `_raw["data"]` keeps the original
                # base64 for anyone who needs the bytes back.
                self.data = base64.urlsafe_b64decode(value).decode(errors="replace")
            else:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Body: {len(self.data)} chars"


class MailMessageHeader:
    """A single header on a Mail message part.

    Attributes
    -----------
    name: :class:`str`
        The header name before the `:` separator, e.g. "To".
    value: :class:`str`
        The header value after the `:` separator, e.g. "someuser@example.com".

    """

    name: str
    value: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'name', '<no name>')}: {getattr(self, 'value', '')}"


class MailMessagePart:
    """One MIME part of a Mail message; parts nest arbitrarily deep."""

    part_id: str
    mime_type: str
    headers: list[MailMessageHeader]
    body: MailMessageBody
    parts: list[MailMessagePart]
    filename: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.headers = []
        self.parts = []
        self.body = MailMessageBody()
        for key, value in kwargs.items():
            if key == "headers":
                self.headers = [MailMessageHeader(**header) for header in value]
            elif key == "body":
                self.body = MailMessageBody(**value)
            elif key == "parts":
                self.parts = [MailMessagePart(**part) for part in value]
            else:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Part: {getattr(self, 'mime_type', '<no mime_type>')} | Headers: {len(self.headers)}"


class MailMessage(EmailMessage):
    """A Mail message, doubling as the builder for one you are about to send.

    Subclasses :class:`EmailMessage` so we get MIME assembly for free — that is what
    :meth:`to_email` and :meth:`to_base64` lean on.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages

    Parameters
    -----------
    draft_id: :class:`str`, optional
        The ID of the Draft this message belongs to, by default "".
    **kwargs: :class:`Any`
        The JSON response for one message.

    """

    id: str
    draft_id: str
    thread_id: str
    label_ids: list[str]
    snippet: str
    history_id: str
    internal_date: str
    payload: MailMessagePart
    size_estimate: int
    raw: str

    def __init__(self, draft_id: str = "", **kwargs: Any) -> None:
        # Build the EmailMessage machinery up front so this object is always a
        # valid email, whether it came from a response or is being composed.
        super().__init__()
        self._raw_response: dict[str, Any] = kwargs
        self.draft_id = draft_id
        self.id = ""
        self.label_ids = []
        self.thread_id = ""
        self.raw = ""
        self.payload = MailMessagePart()
        for key, value in kwargs.items():
            if key == "payload":
                self.payload = MailMessagePart(**value)
            else:
                setattr(self, to_snake_case(key), value)

    def to_email(
        self,
        to_email: Union[str, list[str]],
        from_email: Union[str, list[str]],
        subject: str = " ",
        body: str = " ",
    ) -> MailMessage:
        """Compose this object into a sendable email, replacing any existing content.

        Parameters
        -----------
        to_email: :class:`str` | list[:class:`str`]
            The recipient address(es).
        from_email: :class:`str` | list[:class:`str`]
            The sender address(es).
        subject: :class:`str`, optional
            The subject line, by default " ".
        body: :class:`str`, optional
            The plain text body, by default " ".

        Returns
        --------
        :class:`MailMessage`
            Itself, so you can chain straight into :meth:`prepared`.

        """
        # Reset the EmailMessage — this wipes any headers/content already set.
        super().__init__()
        self.set_content(body)
        self["To"] = to_email
        self["From"] = from_email
        self["Subject"] = subject
        return self

    def to_base64(self) -> str:
        """Return this message base64url encoded, which is what the API expects."""
        return base64.urlsafe_b64encode(self.as_bytes()).decode()

    def prepared(self) -> dict[str, Any]:
        """Return the pre-formed request body wrapping the encoded message.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The body suitable for `drafts().create()` / `drafts().update()`.

        """
        return {"message": {"raw": self.to_base64()}}

    def update_email(self, body: str) -> MailMessage:
        """Append `body` to this message, preserving its To/From/Subject headers.

        Parameters
        -----------
        body: :class:`str`
            The text to append to the existing body.

        Returns
        --------
        :class:`MailMessage`
            Itself, recomposed with the combined body.

        """
        subject = ""
        to_email = ""
        from_email = ""
        for header in self.payload.headers:
            if header.name == "Subject":
                subject = header.value
            elif header.name == "To":
                to_email = header.value
            elif header.name == "From":
                from_email = header.value

        return self.to_email(
            to_email=to_email,
            from_email=from_email,
            subject=subject,
            body=(self.payload.body.data + body),
        )

    def __repr__(self) -> str:
        temp: list[str] = [
            "Mail Message Details:",
            f"ID: {self.id}",
            f"Labels: {self.label_ids}",
            f"Thread ID: {self.thread_id}",
            f"Content: {self.payload.body.data}",
        ]
        return "\n".join(temp)

    def __str__(self) -> str:
        """Overwrite the :class:`EmailMessage` built-in, which dumps the raw MIME."""
        return self.__repr__()


class MailDraft:
    """A Draft in the mailbox.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one Draft.

    """

    id: str
    message: MailMessage

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        # Pull `id` first — `message` needs it, and dict ordering is not a contract.
        self.id = kwargs.get("id", "")
        self.message = MailMessage(draft_id=self.id, **kwargs.get("message", {}))
        for key, value in kwargs.items():
            if key not in {"id", "message"}:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Mail Draft: {self.id} | Mail Message: {self.message}"


class MailDraftList:
    """The response of a `drafts().list()` call.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/list
    """

    drafts: list[MailDraft]
    next_page_token: Union[str, None]
    result_size_estimate: int

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.drafts = [MailDraft(**draft) for draft in kwargs.get("drafts", [])]
        self.next_page_token = kwargs.get("nextPageToken")
        self.result_size_estimate = kwargs.get("resultSizeEstimate", 0)

    def __len__(self) -> int:
        return len(self.drafts)

    def __repr__(self) -> str:
        return f"Drafts: {len(self.drafts)} | Next Page Token: {self.next_page_token}"


class MailMessageList:
    """The response of a `messages().list()` call.

    Gmail returns `id`/`threadId` stubs here, never the message itself — every other
    attribute of these :class:`MailMessage` objects is absent. Feed each `id` to
    :meth:`MailService.get_message` to fetch one in full.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
    """

    messages: list[MailMessage]
    next_page_token: Union[str, None]
    result_size_estimate: int

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.messages = [MailMessage(**message) for message in kwargs.get("messages", [])]
        self.next_page_token = kwargs.get("nextPageToken")
        self.result_size_estimate = kwargs.get("resultSizeEstimate", 0)

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self) -> Any:
        return iter(self.messages)

    def __repr__(self) -> str:
        return f"Messages: {len(self.messages)} | Next Page Token: {self.next_page_token}"


class MailUserLabel:
    """A label on the Mail account.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one label.

    """

    id: str
    name: str
    message_list_visibility: MailMessageListVisibilityEnum
    label_list_visibility: MailLabelListVisiblityEnum
    type: MailTypeEnum
    messages_total: int
    messages_unread: int
    threads_total: int
    threads_unread: int
    color: MailLabelColorEnum

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'name', '<no name>')} | {getattr(self, 'id', '<no id>')}"


class MailUserProfile:
    """The profile of the authenticated Mail account."""

    email_address: str
    messages_total: int
    threads_total: int
    history_id: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'email_address', '<no address>')} | Messages: {getattr(self, 'messages_total', 0)}"


# ---------------------------------------------------------------------------
# Keep data models.
# ---------------------------------------------------------------------------
class KeepNoteDraft:
    """A note to be created via :meth:`gap.services.KeepService.create_note`.

    Mirrors the style of :class:`EventsDraft`; call :meth:`to_dict` to produce the
    request body the Keep API expects.

    Parameters
    -----------
    title: :class:`str`
        The note title.
    text: :class:`str` | None, optional
        Plain text body for the note. Mutually exclusive with `list_items`, by default None.
    list_items: list[tuple[:class:`str`, :class:`bool`]] | None, optional
        Checklist items as `(text, checked)` tuples. Mutually exclusive with `text`, by default None.

    Raises
    -------
    :exc:`ValueError`
        If both `text` and `list_items` are provided.

    """

    title: str
    text: Union[str, None]
    list_items: Union[list[tuple[str, bool]], None]

    def __init__(
        self,
        title: str,
        text: Union[str, None] = None,
        list_items: Union[list[tuple[str, bool]], None] = None,
    ) -> None:
        # A Keep note body is one or the other; the API has no "both" shape.
        if text is not None and list_items is not None:
            raise ValueError("A KeepNoteDraft may have `text` or `list_items`, not both.")
        self.title = title
        self.text = text
        self.list_items = list_items

    def __repr__(self) -> str:
        return f"Note Draft: {self.title}"

    def to_dict(self) -> dict[str, Any]:
        """Build the Keep API request body for this draft.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The body suitable for `notes().create()`.

        """
        body: dict[str, Any]
        if self.list_items is not None:
            body = {"list": {"listItems": [{"text": {"text": text}, "checked": checked} for text, checked in self.list_items]}}
        else:
            body = {"text": {"text": self.text or ""}}
        return {"title": self.title, "body": body}


class KeepNote:
    """A single Keep note returned by the API.

    https://developers.google.com/workspace/keep/api/reference/rest/v1/notes

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one note.

    """

    name: str  # Resource name, e.g. "notes/xxxxxxxxxxxx".
    title: str
    body: dict[str, Any]
    create_time: str
    update_time: str
    trashed: bool

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.name = ""
        self.title = ""
        self.body = {}
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    @property
    def id(self) -> str:
        """The bare note ID — the segment after `notes/` in :attr:`name`."""
        return self.name.rsplit("/", maxsplit=1)[-1]

    @property
    def text(self) -> str:
        """A best-effort plain text rendering of the note body, text or checklist."""
        if "text" in self.body:
            return self.body["text"].get("text", "")
        if "list" in self.body:
            items: list[dict[str, Any]] = self.body["list"].get("listItems", [])
            return "\n".join(f"[{'x' if item.get('checked') else ' '}] {item.get('text', {}).get('text', '')}" for item in items)
        return ""

    def __repr__(self) -> str:
        return f"{self.title or '<untitled>'} | {self.name or '<no name>'}"


class KeepNoteList:
    """The paginated response of :meth:`gap.services.KeepService.list_notes`.

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response of a `notes().list()` call.

    """

    notes: list[KeepNote]
    next_page_token: Union[str, None]

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.notes = [KeepNote(**note) for note in kwargs.get("notes", [])]
        self.next_page_token = kwargs.get("nextPageToken")

    def __len__(self) -> int:
        return len(self.notes)

    def __iter__(self) -> Any:
        return iter(self.notes)

    def __repr__(self) -> str:
        return f"Notes: {len(self.notes)} | Next Page Token: {self.next_page_token}"
