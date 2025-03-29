from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

    from _enums import (
        MailFormatEnum,
        MailLabelColorEnum,
        MailLabelListVisiblityEnum,
        MailMessageListVisibilityEnum,
        MailTypeEnum,
    )


class EventTime(TypedDict, total=False):
    date: str
    dateTime: str
    timeZone: str


class EventUser(TypedDict, total=False):
    id: str
    email: str
    displayName: str
    self: bool
    resource: bool
    optional: bool
    reponseStatus: str
    comment: str
    additionalGuests: int


class CalendarID(TypedDict):
    name: str
    id: str


class EventsTyped(TypedDict, total=False):
    kind: str
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
    start: EventTime
    end: EventTime
    endTimeUnspecified: bool
    recurrence: list[str]
    recurringEventId: str
    originalStartTime: EventTime
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
