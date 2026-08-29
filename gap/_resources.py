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

# * Typing shims for `googleapiclient.discovery.Resource`.
#   Never instantiated by us; `build()` hands back real Resource objects at runtime.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from googleapiclient.discovery import Resource

if TYPE_CHECKING:
    from googleapiclient.http import HttpRequest

__all__ = (
    "CalendarListResource",
    "CalendarResource",
    "EventsResource",
    "KeepNotesResource",
    "KeepResource",
    "MailDraftsResource",
    "MailLabelsResource",
    "MailMessagesResource",
    "MailUserResource",
    "MailUsersResource",
)


class EventsResource(Resource):
    """Typing shim for the `events()` collection of the Calendar API.

    https://developers.google.com/calendar/api/v3/reference/events
    """

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore[misc]

    def insert(self, **kwargs: Any) -> HttpRequest:
        return super().insert(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:
        return super().get(**kwargs)  # type: ignore[misc]

    def update(self, **kwargs: Any) -> HttpRequest:
        return super().update(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:
        return super().delete(**kwargs)  # type: ignore[misc]


class CalendarListResource(Resource):
    """Typing shim for the `calendarList()` collection of the Calendar API.

    https://developers.google.com/calendar/api/v3/reference/calendarList
    """

    def list(self, **kwargs: Any) -> HttpRequest:
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

    def create(self, **kwargs: Any) -> HttpRequest:
        return super().create(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:
        return super().delete(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:
        return super().get(**kwargs)  # type: ignore[misc]

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore[misc]

    def send(self, **kwargs: Any) -> HttpRequest:
        return super().send(**kwargs)  # type: ignore[misc]

    def update(self, **kwargs: Any) -> HttpRequest:
        return super().update(**kwargs)  # type: ignore[misc]


class MailLabelsResource(Resource):
    """Typing shim for `users().labels()` of the Gmail API.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels
    """

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore[misc]

    def create(self, **kwargs: Any) -> HttpRequest:
        return super().create(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:
        return super().get(**kwargs)  # type: ignore[misc]


class MailMessagesResource(Resource):
    """Typing shim for `users().messages()` of the Gmail API.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages
    """

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:
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

    def create(self, **kwargs: Any) -> HttpRequest:
        return super().create(**kwargs)  # type: ignore[misc]

    def get(self, **kwargs: Any) -> HttpRequest:
        return super().get(**kwargs)  # type: ignore[misc]

    def list(self, **kwargs: Any) -> HttpRequest:
        return super().list(**kwargs)  # type: ignore[misc]

    def delete(self, **kwargs: Any) -> HttpRequest:
        return super().delete(**kwargs)  # type: ignore[misc]


class KeepResource(Resource):
    """Typing shim for the root Keep v1 service returned by `build()`."""

    def notes(self) -> KeepNotesResource:
        """The Notes collection."""
        return super().notes()  # type: ignore[misc]
