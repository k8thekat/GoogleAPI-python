from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

    from ._enums import (
        CalendarColorEnum,
        EventTypeEnum,
        LocalTimeZoneEnum,
        MailFormatEnum,
        MailLabelColorEnum,
        MailLabelListVisiblityEnum,
        MailMessageListVisibilityEnum,
        MailTypeEnum,
    )


class EventTimeTyped(TypedDict, total=False):
    """
    Notes
    ------
    dateTime:
        ISO8601 format.
    date:
        UNK
    timezone:
    """

    date: str
    dateTime: str
    timeZone: LocalTimeZoneEnum


class EventUser(TypedDict, total=False):
    id: str
    email: str
    displayName: str
    self: bool
    resource: bool
    optional: bool
    responseStatus: str
    comment: str
    additionalGuests: int


class EventsDraftTyped(TypedDict, total=False):
    summary: str
    end: EventTimeTyped
    start: EventTimeTyped
    colorId: CalendarColorEnum
    description: str
    eventType: EventTypeEnum
    id: str | None
    location: str | None
    transparency: str
    reminders: dict


class CalendarID(TypedDict):
    name: str
    id: str


class EventsTyped(TypedDict, total=False):
    kind: str | None
    etag: str
    id: str
    status: str
    htmlLink: str
    created: datetime
    updated: datetime
    summary: str
    description: str
    location: str
    colorId: str
    creator: EventUser
    organizer: EventUser
    start: EventTimeTyped
    end: EventTimeTyped
    endTimeUnspecified: bool
    recurrence: list[str]
    recurringEventId: str
    originalStartTime: EventTimeTyped
    transparency: str
    visibility: str


class EventListsTyped(TypedDict, total=False):
    kind: str
    etag: str
    summary: str
    description: str
    updated: datetime
    timeZone: str
    accessRole: str
    defaultReminders: list[RemindersTyped]
    nextPageToken: str
    nextSyncToken: str
    items: list[EventsTyped]


class RemindersTyped(TypedDict, total=False):
    method: str
    minutes: int


class LabelID(TypedDict):
    name: str
    id: str


class MailLabelTyped(TypedDict, total=False):
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
