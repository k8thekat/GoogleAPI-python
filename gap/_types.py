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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Required, TypedDict

if TYPE_CHECKING:
    from ._enums import (
        CalendarColorEnum,
        EventTransparencyEnum,
        EventTypeEnum,
        LocalTimeZoneEnum,
        MailLabelColorEnum,
        MailLabelListVisiblityEnum,
        MailMessageListVisibilityEnum,
        MailTypeEnum,
    )

__all__ = (
    "CalendarID",
    "EventListsTyped",
    "EventTimeTyped",
    "EventUserTyped",
    "EventsDraftTyped",
    "EventsTyped",
    "KeepNoteBodyTyped",
    "KeepNoteListTyped",
    "KeepNoteTyped",
    "LabelID",
    "MailLabelTyped",
    "ReminderOverridesTyped",
    "RemindersTyped",
)


class EventTimeTyped(TypedDict, total=False):
    """The start/end boundary of a Calendar Event.

    You must supply either `date` OR `dateTime`, never both. `timeZone` is required
    alongside `dateTime` so the API knows how to anchor it.

    Notes
    ------
    date:
        An all-day date in "YYYY-MM-DD" format.
    dateTime:
        A specific point in time, ISO8601 format.
    timeZone:
        An IANA timezone name, e.g. "America/Los_Angeles".

    """

    date: str
    dateTime: str
    timeZone: LocalTimeZoneEnum


class EventUserTyped(TypedDict, total=False):
    """A creator, organizer or attendee attached to a Calendar Event."""

    id: str
    email: str
    displayName: str
    self: bool
    resource: bool
    optional: bool
    responseStatus: str
    comment: str
    additionalGuests: int


class ReminderOverridesTyped(TypedDict, total=False):
    """A single reminder override on an Event."""

    method: str
    minutes: int


class RemindersTyped(TypedDict, total=False):
    """The reminder block on an Event.

    Notes
    ------
    useDefault:
        Whether the Calendar's default reminders apply to this Event.
    overrides:
        Event specific reminders. Maximum of 5, and only read when `useDefault` is False.

    """

    useDefault: bool
    overrides: list[ReminderOverridesTyped]


class EventsDraftTyped(TypedDict, total=False):
    """The payload accepted by :class:`gap.modules.EventsDraft`."""

    summary: str
    end: Required[EventTimeTyped]
    start: Required[EventTimeTyped]
    colorId: CalendarColorEnum
    color_id: CalendarColorEnum
    description: str
    eventType: EventTypeEnum
    event_type: EventTypeEnum
    id: str | None
    location: str | None
    transparency: EventTransparencyEnum
    reminders: RemindersTyped


class CalendarID(TypedDict):
    """A name/id pair identifying one Calendar on the account."""

    name: str
    id: str


class EventsTyped(TypedDict, total=False):
    """A Calendar Event as returned by the API.

    https://developers.google.com/calendar/api/v3/reference/events
    """

    kind: str | None
    etag: str
    id: str
    status: str
    htmlLink: str
    created: str
    updated: str
    summary: str
    description: str
    location: str
    colorId: str
    creator: EventUserTyped
    organizer: EventUserTyped
    start: EventTimeTyped
    end: EventTimeTyped
    endTimeUnspecified: bool
    recurrence: list[str]
    recurringEventId: str
    originalStartTime: EventTimeTyped
    transparency: str
    visibility: str
    iCalUID: str
    sequence: int
    attendees: list[EventUserTyped]
    attendeesOmitted: bool
    extendedProperties: dict[str, dict[str, str]]
    reminders: RemindersTyped


class EventListsTyped(TypedDict, total=False):
    """The response body of an `events.list` call.

    https://developers.google.com/calendar/api/v3/reference/events/list
    """

    kind: str
    etag: str
    summary: str
    description: str
    updated: str
    timeZone: str
    accessRole: str
    defaultReminders: list[ReminderOverridesTyped]
    nextPageToken: str
    nextSyncToken: str
    items: list[EventsTyped]


class LabelID(TypedDict):
    """A name/id pair identifying one Mail label."""

    name: str
    id: str


class MailLabelTyped(TypedDict, total=False):
    """A Mail label as returned by the API.

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


class KeepNoteBodyTyped(TypedDict, total=False):
    """The body of a Keep note — either a `text` block or a `list` of checklist items."""

    text: dict[str, str]
    list: dict[str, list[dict[str, Any]]]


class KeepNoteTyped(TypedDict, total=False):
    """A Keep note as returned by the API.

    https://developers.google.com/workspace/keep/api/reference/rest/v1/notes
    """

    name: str
    title: str
    body: KeepNoteBodyTyped
    createTime: str
    updateTime: str
    trashed: bool
    trashTime: str
    permissions: list[dict[str, Any]]


class KeepNoteListTyped(TypedDict, total=False):
    """The response body of a `notes.list` call."""

    notes: list[KeepNoteTyped]
    nextPageToken: str
