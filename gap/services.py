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

import json
import logging
from configparser import ConfigParser
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from random import randrange
from typing import TYPE_CHECKING, Any, ClassVar, Self, Union

import requests

# Optional: only `KeepServicePersonal` needs it, and it is not a dependency of the
# package. Guarded so importing `gap` still works without the extra installed.
try:
    import gpsoauth  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - exercised only without the extra.
    gpsoauth = None  # type: ignore[assignment]

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as Credentials_oa
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ._enums import MailFormatEnum
from ._types import CalendarID
from .modules import (
    CalendarList,
    CalendarListEntry,
    CalendarResource,
    Events,
    EventsDraft,
    EventsList,
    KeepBasePersonal,
    KeepItemsPersonal,
    KeepNote,
    KeepNoteDraft,
    KeepNoteList,
    KeepResource,
    KeepSubItemPersonal,
    MailDraft,
    MailDraftList,
    MailMessage,
    MailMessageList,
    MailUserLabel,
    MailUserProfile,
    MailUserResource,
    keep_now,
    to_snake_case,
)

if TYPE_CHECKING:
    from google.auth.external_account_authorized_user import Credentials
    from googleapiclient.http import HttpRequest

    from ._enums import LocalTimeZoneEnum
    from ._types import EventsDraftTyped, LabelID, NotePersonalPartsTyped, NotePersonalResponse

__all__ = (
    "CalendarService",
    "GoogleService",
    "KeepService",
    "KeepServicePersonal",
    "KeepSyncError",
    "MailService",
    "ini_load",
    "ini_load_calendars",
    "resolve_ini_path",
)

LOGGER: logging.Logger = logging.getLogger(__name__)

INI_SECTION = "GAP"
INI_CALENDAR_SECTION = "GAP.Calendars"


def ini_load(file: Path, options: list[str], section: str = INI_SECTION) -> list[Union[str, None]]:
    """Load a set of options out of an ini file.

    Parameters
    -----------
    file: :class:`Path`
        The ini file to read.
    options: list[:class:`str`]
        The option names to pull, e.g. ["TOKEN_PATH"].
    section: :class:`str`, optional
        The ini section to read them from, by default "GAP".

    Returns
    --------
    list[:class:`str` | None]
        The option values in the same order they were asked for. An option that is not
        present comes back as None rather than raising, so partial configs still load.

    Raises
    -------
    :exc:`FileNotFoundError`
        If `file` does not exist.
    :exc:`ValueError`
        If `section` is not in the file.

    """
    if not file.is_file():
        raise FileNotFoundError(f"<ini_load> | Failed to load file. | Path: {file.as_posix()}")

    # The `list` converter lets a comma separated option come back as a real list via
    # `settings.getlist(...)` — handy for things like a set of calendar IDs.
    settings = ConfigParser(converters={"list": lambda setting: [value.strip() for value in setting.split(",")]})
    settings.read(filenames=file)

    if section not in settings.sections():
        raise ValueError(f"<ini_load> | Failed to find the `{section}` section. | Path: {file.as_posix()}")

    return [settings.get(section=section, option=option, fallback=None) for option in options]


def resolve_ini_path(file: Path, value: str) -> Path:
    """Turn a path read out of an ini file into an absolute one.

    A relative value is anchored to the ini file's own directory rather than the CWD.
    Anchoring to the CWD would mean the same config resolved differently depending on
    where you happened to run from, which makes a checked in ini unusable.

    Parameters
    -----------
    file: :class:`Path`
        The ini file the value came out of.
    value: :class:`str`
        The path as written in the ini, absolute or relative.

    Returns
    --------
    :class:`Path`
        The resolved absolute path. `~` is expanded first, so `~/creds` still works.

    """
    path: Path = Path(value).expanduser()
    if path.is_absolute():
        return path

    return file.expanduser().resolve().parent.joinpath(path).resolve()


def ini_load_calendars(file: Path, section: str = INI_CALENDAR_SECTION) -> list[CalendarID]:
    """Load a set of `name = id` Calendar pairs out of an ini file.

    The section is a plain name to id mapping, which lines up with what
    `CalendarService.get_calendar_list()` prints, so populating it is copy/paste:

    ```ini
    [GAP.Calendars]
    personal = primary
    work = c_abc123@group.calendar.google.com
    ```

    Parameters
    -----------
    file: :class:`Path`
        The ini file to read.
    section: :class:`str`, optional
        The ini section to read them from, by default "GAP.Calendars".

    Returns
    --------
    list[:class:`CalendarID`]
        One entry per option in the section, in file order. A missing section comes back
        empty rather than raising, so an ini without any Calendars still loads.

    Raises
    -------
    :exc:`FileNotFoundError`
        If `file` does not exist.

    """
    if not file.is_file():
        raise FileNotFoundError(f"<ini_load_calendars> | Failed to load file. | Path: {file.as_posix()}")

    # Calendar names are user facing, so keep the case they were typed in. `ConfigParser`
    # lowercases option keys by default — that is fine for `TOKEN_PATH` in `ini_load`,
    # but it would turn a `Work` Calendar into `work`.
    settings = ConfigParser()
    settings.optionxform = str  # type: ignore[method-assign, assignment]
    settings.read(filenames=file)

    if section not in settings.sections():
        LOGGER.debug("<ini_load_calendars> | No `%s` section. | Path: %s", section, file.as_posix())
        return []

    return [CalendarID(name=name, id=calendar_id) for name, calendar_id in settings.items(section=section)]


class GoogleService:
    """The shared OAuth2 handling every Google service in this package sits on.

    Subclasses declare `service_name`, `service_version`, `token_name` and `SCOPES`
    then add their own endpoint methods — they must NOT re-implement the credential
    dance below.

    The flow is: load a cached token if we have one, refresh it if it went stale,
    otherwise run the local-server login and cache whatever comes back.

    Parameters
    -----------
    token_path: :class:`Path`
        The directory holding your `client_secret.json`. The service's token file is
        written here after the first authorization.

    Raises
    -------
    :exc:`NotADirectoryError`
        If `token_path` is not an existing directory.
    :exc:`FileNotFoundError`
        If no client secret file can be found in `token_path`.

    """

    # Set by every subclass.
    service_name: ClassVar[str]
    service_version: ClassVar[str]
    token_name: ClassVar[str]
    SCOPES: ClassVar[list[str]] = []

    # Checked in order; the first one that exists wins. Lets a service keep its
    # historical, service-prefixed secret name while new setups use the shared one.
    secret_names: ClassVar[tuple[str, ...]] = ("client_secret.json",)

    token_path: Path
    creds: Union[Credentials_oa, Credentials]
    service: Any

    def __init__(self, token_path: Path) -> None:
        if not token_path.is_dir():
            raise NotADirectoryError(f"`token_path` must be an existing directory. | Value: {token_path}")

        self.token_path = token_path
        self.creds = self._authorize()
        self.service = build(
            serviceName=self.service_name,
            version=self.service_version,
            credentials=self.creds,
        )
        LOGGER.info("<%s> | Built the `%s` %s service.", type(self).__name__, self.service_name, self.service_version)

    @classmethod
    def from_ini(cls, file: Path, section: str = INI_SECTION) -> Self:
        """Build the service using the `TOKEN_PATH` from an ini file.

        Note this configures *where* the credentials live — it does not replace them.
        Google's `client_secret.json` and the cached `*_token.json` are Google's own
        formats and still have to be JSON.

        A relative `TOKEN_PATH` is resolved against the ini file's own directory, not the
        CWD — so `TOKEN_PATH = .` means "next to the ini" and a clone works unedited no
        matter where you run it from. An absolute path is used as written.

        ```ini
        [GAP]
        # The directory holding client_secret.json and the cached *_token.json files.
        # Relative to this file, so `.` is the directory the ini sits in.
        TOKEN_PATH = .
        ```

        Parameters
        -----------
        file: :class:`Path`
            The ini file to read, e.g. `Path("./local.ini")`.
        section: :class:`str`, optional
            The ini section to read from, by default "GAP".

        Returns
        --------
        :class:`Self`
            The configured service.

        Raises
        -------
        :exc:`ValueError`
            If the section has no `TOKEN_PATH` option.

        """
        token_path: Union[str, None] = ini_load(file=file, options=["TOKEN_PATH"], section=section)[0]
        if token_path is None:
            raise ValueError(f"<{cls.__name__}.from_ini> | The `{section}` section has no `TOKEN_PATH` option.")

        return cls(token_path=resolve_ini_path(file=file, value=token_path))

    def _find_secret(self) -> Path:
        """Locate the OAuth client secret inside our `token_path`.

        Returns
        --------
        :class:`Path`
            The first secret file from `secret_names` that exists.

        Raises
        -------
        :exc:`FileNotFoundError`
            If none of the candidate names exist.

        """
        for name in self.secret_names:
            secret: Path = self.token_path.joinpath(name)
            if secret.exists():
                return secret

        raise FileNotFoundError(f"Unable to find a client secret in {self.token_path}. Expected one of: {', '.join(self.secret_names)}")

    def _authorize(self) -> Union[Credentials_oa, Credentials]:
        """Load, refresh or acquire the credentials for this service.

        The token file caches the user's access and refresh tokens and is written
        automatically once the authorization flow completes the first time.

        Returns
        --------
        :class:`Credentials_oa` | :class:`Credentials`
            Valid credentials for our `SCOPES`.

        """
        token_file: Path = self.token_path.joinpath(self.token_name)
        creds: Union[Credentials_oa, Credentials, None] = None

        if token_file.exists():
            creds = Credentials_oa.from_authorized_user_file(filename=str(token_file), scopes=self.SCOPES)

        if creds is not None and creds.valid:
            return creds

        # A stale token we can renew without bothering the user.
        if creds is not None and creds.expired and creds.refresh_token:
            LOGGER.info("<%s> | Refreshing the expired token at %s.", type(self).__name__, token_file)
            try:
                creds.refresh(request=Request())
            except RefreshError as e:
                # Revoked, or cached against a different set of SCOPES than we now ask for
                # — Google rejects the renewal either way. Fall through to the browser
                # rather than making the user work out that the token file needs deleting.
                LOGGER.warning("<%s> | Could not renew %s, re-authorizing. | %s", type(self).__name__, token_file, e)
                creds = None
        else:
            creds = None

        if creds is None:
            # No usable token — send the user through the browser login.
            LOGGER.info("<%s> | No valid token found, starting the local authorization flow.", type(self).__name__)
            flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file=str(self._find_secret()),
                scopes=self.SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Cache whatever we ended up with for the next run.
        with token_file.open(mode="w") as token:
            token.write(creds.to_json())
        return creds


class CalendarService(GoogleService):
    """The Google Calendar v3 API.

    Store your `client_secret.json` in `token_path`; `calendar_token.json` is written
    beside it after the first authorization.

    Parameters
    -----------
    token_path: :class:`Path`
        The directory holding your `client_secret.json`.

    Attributes
    -----------
    calendars: list[:class:`CalendarID`]
        The Calendars this service knows about. Empty unless the service was built with
        `from_ini()`; see `resolve_calendar()` and `get_all_events()`.

    """

    service: CalendarResource
    service_name: ClassVar[str] = "calendar"
    service_version: ClassVar[str] = "v3"
    token_name: ClassVar[str] = "calendar_token.json"
    SCOPES: ClassVar[list[str]] = ["https://www.googleapis.com/auth/calendar"]

    # Per instance, not a ClassVar — two services pointed at different accounts must not
    # share a Calendar list.
    calendars: list[CalendarID]

    def __init__(self, token_path: Path) -> None:
        super().__init__(token_path=token_path)
        self.calendars = []

    @classmethod
    def from_ini(cls, file: Path, section: str = INI_SECTION) -> Self:
        """Build the service from an ini file, picking up any configured Calendars.

        Handles `TOKEN_PATH` exactly as `GoogleService.from_ini()` does, then fills
        `calendars` from the `[GAP.Calendars]` section if the file has one.

        ```ini
        [GAP]
        TOKEN_PATH = /home/kat/gitHub/GoogleAPI-python

        [GAP.Calendars]
        personal = primary
        work = c_abc123@group.calendar.google.com
        ```

        Parameters
        -----------
        file: :class:`Path`
            The ini file to read, e.g. `Path("./local.ini")`.
        section: :class:`str`, optional
            The ini section to read `TOKEN_PATH` from, by default "GAP".

        Returns
        --------
        :class:`Self`
            The configured service.

        Raises
        -------
        :exc:`ValueError`
            If the section has no `TOKEN_PATH` option.

        """
        self: Self = super().from_ini(file=file, section=section)
        self.calendars = ini_load_calendars(file=file)
        LOGGER.info("<%s.from_ini> | Loaded %s Calendar(s) from %s.", cls.__name__, len(self.calendars), file.as_posix())
        return self

    def resolve_calendar(self, name: str) -> str:
        """Look up a configured Calendar's ID by its name.

        Saves pasting a raw `c_abc123@group.calendar.google.com` around your call sites.

        Parameters
        -----------
        name: :class:`str`
            The Calendar name as written in the ini, matched case insensitively.

        Returns
        --------
        :class:`str`
            The matching Calendar ID.

        Raises
        -------
        :exc:`ValueError`
            If no configured Calendar goes by that name.

        """
        for entry in self.calendars:
            if entry["name"].lower() == name.lower():
                return entry["id"]

        known: str = ", ".join(entry["name"] for entry in self.calendars) or "<none configured>"
        raise ValueError(f"<{type(self).__name__}.resolve_calendar> | No Calendar named `{name}`. | Known: {known}")

    def create_event(self, event: EventsDraft) -> Events:
        """Create an Event on the Calendar the draft points at.

        Parameters
        -----------
        event: :class:`EventsDraft`
            The draft to pull the fields from.

        Returns
        --------
        :class:`Events`
            The created Event as returned by the API.

        """
        request: HttpRequest = self.service.events().insert(calendarId=event.calendar_id, body=event.to_dict())
        return Events(calendar_id=event.calendar_id, **request.execute())

    def delete_event(self, event: Events) -> None:
        """Delete the passed in Event.

        Parameters
        -----------
        event: :class:`Events`
            The Event to delete.

        Raises
        -------
        :exc:`ValueError`
            If the API response is not the expected empty body.

        """
        request: HttpRequest = self.service.events().delete(calendarId=event.calendar_id, eventId=event.id)
        try:
            result: Any = request.execute()
        except HttpError as e:
            LOGGER.warning("<%s.delete_event> | We encountered an error. | %s", type(self).__name__, e)
            return

        # A successful delete comes back as an empty body.
        if not result:
            return
        raise ValueError(f"Unexpected response when calling CalendarService.delete_event. | Value: {result}")

    def get_event(self, event_id: str, calendar_id: str = "primary", timezone: Union[LocalTimeZoneEnum, None] = None) -> Events:
        """Retrieve a specific Event.

        Parameters
        -----------
        event_id: :class:`str`
            The ID of the Event. See the :attr:`Events.id` value.
        calendar_id: :class:`str`, optional
            The Calendar ID to look under, by default "primary".
        timezone: :class:`LocalTimeZoneEnum` | None, optional
            Time zone used in the response, by default None — which uses the Calendar's own.

        Returns
        --------
        :class:`Events`
            The requested Event.

        """
        if timezone is None:
            request: HttpRequest = self.service.events().get(calendarId=calendar_id, eventId=event_id)
        else:
            request = self.service.events().get(calendarId=calendar_id, eventId=event_id, timeZone=timezone)
        return Events(calendar_id=calendar_id, **request.execute())

    def get_calendar_events_by_date(
        self,
        calendar_id: str = "primary",
        since_time: Union[datetime, None] = None,
        upto_time: Union[datetime, None] = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> EventsList:
        """Return the Events on a Calendar inside a time window.

        Parameters
        -----------
        calendar_id: :class:`str`, optional
            The Calendar ID to pull from, by default "primary".
        since_time: :class:`datetime` | None, optional
            The start of the window, by default None — which is `datetime.now()`.
        upto_time: :class:`datetime` | None, optional
            The end of the window, by default None — which is 30 days out from now.
        max_results: :class:`int`, optional
            How many Events to return at most, by default 10.
        single_events: :class:`bool`, optional
            Expand recurring Events into individual instances, by default True.
        order_by: :class:`str`, optional
            "startTime" orders by start date/time ascending and requires `single_events`.
            "updated" orders by last modification time ascending. By default "startTime".

        Returns
        --------
        :class:`EventsList`
            The matching Events.

        """
        # Resolved here rather than in the signature — a `datetime.now()` default is
        # evaluated once at import and would pin the window to interpreter start.
        if since_time is None:
            since_time = datetime.now(tz=UTC)
        if upto_time is None:
            upto_time = datetime.now(tz=UTC) + timedelta(days=30)

        request: HttpRequest = self.service.events().list(
            calendarId=calendar_id,
            timeMin=self._to_rfc3339(value=since_time),
            timeMax=self._to_rfc3339(value=upto_time),
            maxResults=max_results,
            singleEvents=single_events,
            orderBy=order_by,
        )
        return EventsList(calendar_id=calendar_id, **request.execute())

    @staticmethod
    def _to_rfc3339(value: datetime) -> str:
        """Render a datetime as the RFC3339 UTC string `timeMin` / `timeMax` expect.

        We previously stripped the tzinfo and stapled a "Z" on the end, which labelled
        *local* time as UTC and shifted the whole query window by our UTC offset.

        Parameters
        -----------
        value: :class:`datetime`
            The boundary to render. A naive value is read as local time.

        Returns
        --------
        :class:`str`
            The value in UTC, e.g. "2026-07-24T18:30:00Z".

        """
        # `astimezone()` on a naive value attaches the system's local offset, so we
        # convert rather than mislabel it.
        if value.tzinfo is None:
            value = value.astimezone()
        return value.astimezone(tz=UTC).isoformat().replace("+00:00", "Z")

    def get_calendars(self) -> list[CalendarList]:
        """Return every Calendar available to the account, walking all pages.

        Returns
        --------
        list[:class:`CalendarList`]
            Every Calendar entry across every page of the response.

        """
        calendars: list[CalendarList] = []
        page_token: Union[str, None] = None
        while True:
            page = CalendarListEntry(**self.service.calendarList().list(pageToken=page_token).execute())
            if len(page.events) == 0:
                LOGGER.info("<%s.get_calendars> | Unable to find any Calendars in our CalendarList.", type(self).__name__)
            calendars.extend(page.events)

            # No token means that was the last page — break regardless of what we got.
            page_token = page.next_page_token
            if not page_token:
                break
        return calendars

    def get_calendar_list(self) -> str:
        """Return a human readable listing of every Calendar available to the account.

        Returns
        --------
        :class:`str`
            One "Name: ... | ID: ..." line per Calendar.

        """
        return "\n".join(f"Name: {entry.summary} | ID: {entry.id}" for entry in self.get_calendars())

    def get_all_events(self, calendar: Union[list[CalendarID], None] = None) -> list[Events]:
        """Get every upcoming Event across a set of Calendars.

        Parameters
        -----------
        calendar: list[:class:`CalendarID`] | None, optional
            The Calendars to pull from, by default None. When omitted we use the
            Calendars from the ini (see `from_ini()`).

        Returns
        --------
        list[:class:`Events`]
            The Events from every Calendar, flattened into one list.

        Raises
        -------
        :exc:`ValueError`
            If no Calendars were passed and none are configured — otherwise this would
            quietly hand back an empty list.

        """
        if calendar is None:
            calendar = self.calendars
        if len(calendar) == 0:
            raise ValueError(
                f"<{type(self).__name__}.get_all_events> | No Calendars to pull from. Pass `calendar` or "
                f"add a `[{INI_CALENDAR_SECTION}]` section to your ini and build with `from_ini()`."
            )

        all_events: list[Events] = []
        for entry in calendar:
            event_list: EventsList = self.get_calendar_events_by_date(calendar_id=entry["id"])
            if len(event_list.events) == 0:
                LOGGER.info("<%s.get_all_events> | No upcoming Events on %s.", type(self).__name__, entry["id"])
                continue
            all_events.extend(event_list.events)
        return all_events

    def update_event(self, old_event: Events, event_draft: Union[EventsDraft, EventsDraftTyped]) -> Events:
        """Update an existing Event with the fields from a draft.

        Re-fetches the Event first so we send back a complete body — the API's update
        is a replace, not a merge.

        Parameters
        -----------
        old_event: :class:`Events`
            The Event to update; only its `id` and `calendar_id` are used.
        event_draft: :class:`EventsDraft` | :class:`EventsDraftTyped`
            The fields to overwrite on the Event.

        Returns
        --------
        :class:`Events`
            The updated Event as returned by the API.

        """
        event: Events = self.get_event(event_id=old_event.id, calendar_id=old_event.calendar_id)
        # `changes` is the API's camelCase shape either way — `to_dict()` builds a request
        # body, and `EventsDraftTyped` mirrors one. Our attributes are snake_case, so
        # convert before applying or we set a shadow field the update body then dupes.
        changes: dict[str, Any] = event_draft.to_dict() if isinstance(event_draft, EventsDraft) else dict(event_draft)
        for key, value in changes.items():
            setattr(event, to_snake_case(key), value)

        request: HttpRequest = self.service.events().update(
            calendarId=event.calendar_id,
            eventId=event.id,
            body=event.to_dict(),
        )
        return Events(calendar_id=event.calendar_id, **request.execute())


class MailService(GoogleService):
    """The Gmail v1 API.

    Store your `client_secret.json` in `token_path`; `mail_token.json` is written
    beside it after the first authorization.

    https://developers.google.com/workspace/gmail/api/quickstart/python

    Parameters
    -----------
    token_path: :class:`Path`
        The directory holding your `client_secret.json`.

    """

    service: MailUserResource
    service_name: ClassVar[str] = "gmail"
    service_version: ClassVar[str] = "v1"
    token_name: ClassVar[str] = "mail_token.json"
    # Read plus draft/send, which is everything the methods below touch. This used to be
    # `https://mail.google.com/` — full mailbox control, delete included — which is far
    # more than we need to hand an application.
    SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]
    # `mail_client_secret.json` is the name older setups used; still honored first.
    secret_names: ClassVar[tuple[str, ...]] = ("mail_client_secret.json", "client_secret.json")
    # The `maxResults` ceiling the messages/drafts list endpoints enforce.
    MAX_RESULTS: ClassVar[int] = 500

    LABELS: list[LabelID]

    def get_profile(self, user_id: str = "me") -> MailUserProfile:
        """Get the profile of the authenticated account.

        Parameters
        -----------
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailUserProfile`
            The account profile.

        """
        request: HttpRequest = self.service.users().getProfile(userId=user_id)
        return MailUserProfile(**request.execute())

    def get_labels(self, user_id: str = "me") -> list[MailUserLabel]:
        """Get all the labels on the Mail account, also updating our `LABELS` attribute.

        Parameters
        -----------
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        list[:class:`MailUserLabel`]
            Every label on the account.

        """
        response: dict[str, Any] = self.service.users().labels().list(userId=user_id).execute()
        labels: list[MailUserLabel] = [MailUserLabel(**label) for label in response.get("labels", [])]

        # Replace rather than extend — this mirrors the last response, and appending to it
        # gave us every label twice on the second call.
        # Uppercase because it is part of our public surface, but it is a per-instance
        # cache rather than a constant — pyright reads the casing as the latter.
        self.LABELS = [{"name": label.name, "id": label.id} for label in labels]  # pyright: ignore[reportConstantRedefinition]
        return labels

    def search_messages(
        self,
        query: str = "",
        label_ids: Union[list[str], None] = None,
        max_results: int = 100,
        page_token: Union[str, None] = None,
        include_spam_trash: bool = False,
        user_id: str = "me",
    ) -> MailMessageList:
        """Search the mailbox, using the same query syntax as the Gmail search bar.

        This is one page of results. The response only carries `id`/`threadId` stubs, so
        pass each `id` to :meth:`get_message` for the message itself. To walk the whole
        result set, feed the returned `nextPageToken` back in as `page_token` until it
        comes back None.

        https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list

        Parameters
        -----------
        query: :class:`str`, optional
            A Gmail search query, e.g. "from:billing@example.com has:attachment",
            by default "" — every message.
        label_ids: list[:class:`str`] | None, optional
            Only match messages carrying all of these Label IDs, by default None.
            IDs, not names — see :meth:`get_labels` or the `LABELS` cache.
        max_results: :class:`int`, optional
            How many results to return on this page, by default 100.
        page_token: :class:`str` | None, optional
            The `nextPageToken` of a previous call, by default None — the first page.
        include_spam_trash: :class:`bool`, optional
            Whether to search SPAM and TRASH as well, by default False.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailMessageList`
            The matching message stubs plus any continuation token.

        Raises
        -------
        :exc:`ValueError`
            If `max_results` is outside the range the API accepts.

        """
        if not 1 <= max_results <= self.MAX_RESULTS:
            raise ValueError(f"Your max_results must be between 1 and {self.MAX_RESULTS}. | Value: {max_results}")

        # Only send the optional filters we were actually given; an empty `labelIds` is
        # not the same request as no `labelIds` at all.
        params: dict[str, Any] = {
            "userId": user_id,
            "q": query,
            "maxResults": max_results,
            "includeSpamTrash": include_spam_trash,
        }
        if label_ids:
            params["labelIds"] = label_ids
        if page_token is not None:
            params["pageToken"] = page_token

        request: HttpRequest = self.service.users().messages().list(**params)
        return MailMessageList(**request.execute())

    def get_message(
        self,
        message_id: str,
        message_format: Union[MailFormatEnum, str, None] = None,
        user_id: str = "me",
    ) -> Union[MailMessage, None]:
        """Get a single message from the mailbox.

        https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get

        Parameters
        -----------
        message_id: :class:`str`
            The ID of the message to fetch; this is the :attr:`MailMessage.id` attribute
            off a :meth:`search_messages` result.
        message_format: :class:`MailFormatEnum` | :class:`str` | None, optional
            How much of the message to return, by default None — the API's own default.
            Use `MailFormatEnum.full` if you want the parsed headers and body parts.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailMessage` | None
            The message, or None if the request failed.

        """
        try:
            if message_format is None:
                request: HttpRequest = self.service.users().messages().get(userId=user_id, id=message_id)
            else:
                request = self.service.users().messages().get(userId=user_id, id=message_id, format=message_format)
            message = MailMessage(**request.execute())
        except HttpError as e:
            LOGGER.warning("<%s.get_message> | Failed to get the message %s. | %s", type(self).__name__, message_id, e)
            return None
        return message

    def create_draft(self, body: MailMessage, user_id: str = "me") -> MailDraft:
        """Create a Draft from a composed message.

        Parameters
        -----------
        body: :class:`MailMessage`
            The message to save as a Draft.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailDraft`
            The created Draft.

        """
        request: HttpRequest = self.service.users().drafts().create(userId=user_id, body=body.prepared())
        return MailDraft(**request.execute())

    def get_drafts(self, user_id: str = "me", max_results: int = 100) -> MailDraftList:
        """List the Drafts in the mailbox.

        Parameters
        -----------
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".
        max_results: :class:`int`, optional
            How many Drafts to return at most, by default 100.

        Returns
        --------
        :class:`MailDraftList`
            The Drafts plus any continuation token.

        """
        request: HttpRequest = self.service.users().drafts().list(userId=user_id, maxResults=max_results)
        return MailDraftList(**request.execute())

    def get_draft(
        self,
        message_id: str,
        message_format: Union[MailFormatEnum, str, None] = None,
        user_id: str = "me",
    ) -> Union[MailMessage, None]:
        """Get an existing Draft from the mailbox.

        Parameters
        -----------
        message_id: :class:`str`
            The ID of the Draft to fetch; this is the :attr:`MailDraft.id` attribute.
        message_format: :class:`MailFormatEnum` | :class:`str` | None, optional
            How much of the message to return, by default None — the API's own default.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailMessage` | None
            The Draft's message, or None if the request failed.

        Raises
        -------
        :exc:`ValueError`
            If `message_id` is not a Draft ID.

        """
        # Draft IDs are prefixed with "r"; a message ID here would 404 confusingly.
        if not message_id.startswith("r"):
            raise ValueError(f"Your message_id is not of the right type, it will start with an 'r'. | Value: {message_id}")

        try:
            if message_format is None:
                request: HttpRequest = self.service.users().drafts().get(userId=user_id, id=message_id)
            else:
                request = self.service.users().drafts().get(userId=user_id, id=message_id, format=message_format)
            draft = MailDraft(**request.execute())
        except HttpError as e:
            LOGGER.warning("<%s.get_draft> | Failed to get the Draft %s. | %s", type(self).__name__, message_id, e)
            return None
        return draft.message

    def update_draft(self, message_id: str, body: MailMessage, user_id: str = "me") -> MailMessage:
        """Overwrite an existing Draft with a new message.

        Parameters
        -----------
        message_id: :class:`str`
            The ID of the Draft to overwrite.
        body: :class:`MailMessage`
            The replacement message.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailMessage`
            The updated Draft's message.

        """
        request: HttpRequest = self.service.users().drafts().update(userId=user_id, id=message_id, body=body.prepared())
        draft = MailDraft(**request.execute())
        return draft.message

    def append_draft(self, message_id: str, body: str, user_id: str = "me") -> Union[MailMessage, None]:
        """Append text to the end of an existing Draft, preserving its headers.

        Parameters
        -----------
        message_id: :class:`str`
            The ID of the Draft to append to.
        body: :class:`str`
            The text to append.
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`MailMessage` | None
            The updated message, or None if the Draft could not be found.

        """
        # `full` so we get the parsed headers/body back to rebuild the email from.
        existing: Union[MailMessage, None] = self.get_draft(
            message_id=message_id,
            message_format=MailFormatEnum.full,
            user_id=user_id,
        )
        if existing is None:
            LOGGER.warning("<%s.append_draft> | Failed to find the Draft %s.", type(self).__name__, message_id)
            return None

        return self.update_draft(message_id=message_id, body=existing.update_email(body=body), user_id=user_id)


class KeepService(GoogleService):
    """The Google Keep v1 API.

    Store your `client_secret.json` in `token_path`; `keep_token.json` is written
    beside it after the first authorization.

    https://developers.google.com/workspace/keep/api/reference/rest

    Parameters
    -----------
    token_path: :class:`Path`
        The directory holding your `client_secret.json`.

    Notes
    ------
    The official Keep API is a **Google Workspace** service. It will not authorize a
    personal Gmail account, and :meth:`list_notes` only returns notes this app created
    plus notes explicitly shared with it — it is NOT a mirror of an account's Keep.
    See `ISSUES.md` for the details.

    """

    service: KeepResource
    service_name: ClassVar[str] = "keep"
    service_version: ClassVar[str] = "v1"
    token_name: ClassVar[str] = "keep_token.json"
    SCOPES: ClassVar[list[str]] = ["https://www.googleapis.com/auth/keep"]

    def create_note(self, draft: KeepNoteDraft) -> KeepNote:
        """Create a note from a draft.

        Parameters
        -----------
        draft: :class:`KeepNoteDraft`
            The note contents to create.

        Returns
        --------
        :class:`KeepNote`
            The created note as returned by the API.

        """
        request: HttpRequest = self.service.notes().create(body=draft.to_dict())
        return KeepNote(**request.execute())

    def get_note(self, name: str) -> KeepNote:
        """Fetch a single note by resource name.

        Parameters
        -----------
        name: :class:`str`
            The note resource name ("notes/xxxx") or the bare ID.

        Returns
        --------
        :class:`KeepNote`
            The requested note.

        """
        request: HttpRequest = self.service.notes().get(name=self._as_resource_name(name=name))
        return KeepNote(**request.execute())

    def list_notes(
        self,
        page_size: int = 20,
        note_filter: str = "trashed=false",
        page_token: Union[str, None] = None,
    ) -> KeepNoteList:
        """List the notes accessible to the authenticated app.

        Parameters
        -----------
        page_size: :class:`int`, optional
            How many notes to return per page, by default 20.
        note_filter: :class:`str`, optional
            A Keep API filter expression, by default "trashed=false".
        page_token: :class:`str` | None, optional
            A continuation token from a previous :attr:`KeepNoteList.next_page_token`, by default None.

        Returns
        --------
        :class:`KeepNoteList`
            The page of notes plus any continuation token.

        """
        request: HttpRequest = self.service.notes().list(pageSize=page_size, filter=note_filter, pageToken=page_token)
        return KeepNoteList(**request.execute())

    def delete_note(self, note: Union[KeepNote, str]) -> None:
        """Delete a note by object, resource name or bare ID.

        Parameters
        -----------
        note: :class:`KeepNote` | :class:`str`
            The note to delete.

        Raises
        -------
        :exc:`ValueError`
            If the API response is not the expected empty body.

        """
        name: str = note.name if isinstance(note, KeepNote) else note
        request: HttpRequest = self.service.notes().delete(name=self._as_resource_name(name=name))
        try:
            result: Any = request.execute()
        except HttpError as e:
            LOGGER.warning("<%s.delete_note> | We encountered an error. | %s", type(self).__name__, e)
            return

        # A successful delete comes back as an empty body.
        if not result:
            return
        raise ValueError(f"Unexpected response when calling KeepService.delete_note. | Value: {result}")

    @staticmethod
    def _as_resource_name(name: str) -> str:
        """Normalize a bare note ID into the "notes/xxxx" resource name the API wants."""
        return name if name.startswith("notes/") else f"notes/{name}"


# * Consumer Keep — NOT a `GoogleService`.
#   Uses Android master token auth against the consumer backend, not OAuth2.
#   One endpoint, delta sync rather than REST resources.

# * The only endpoint. Every operation is a delta exchange against it.
KEEP_CHANGES_URL: str = "https://www.googleapis.com/notes/v1/changes"

#: The `parentId` a top level note carries.
KEEP_ROOT: str = "root"

# * What the Android Keep client identifies itself as when minting an access token.
KEEP_OAUTH_SCOPES: str = "oauth2:https://www.googleapis.com/auth/memento https://www.googleapis.com/auth/reminders"
KEEP_ANDROID_APP: str = "com.google.android.keep"
KEEP_CLIENT_SIG: str = "38918a453d07199354f8b19af05ec6562ced5788"

# ! Must stay constant — the master token is bound to it; a new value registers a new device.
ANDROID_ID: str = "0123456789abcdef"

# ! Opaque server feature gates. Send verbatim; pruning them changes what comes back.
CAPABILITIES: tuple[str, ...] = ("NC", "PI", "LB", "AN", "SH", "DR", "TR", "IN", "SNB", "MI", "CO")

# * Default timeout — neither `requests` nor `httplib2` sets one by default.
REQUEST_TIMEOUT: float = 30.0


class KeepSyncError(Exception):
    """Raised when a `changes` exchange fails. The graph is left untouched."""


class KeepServicePersonal:
    """Google Keep for a consumer `@gmail.com` account.

    NOT a :class:`GoogleService` subclass — uses Android master token auth.
    See :class:`KeepService` for the Workspace API.

    Parameters
    -----------
    email: :class:`str`
        The account address.
    master_token: :class:`str`
        From :meth:`exchange_token`. See the warning below.
    queue_interval: :class:`float` | None, optional
        Seconds between flushes of the edit queue, by default `QUEUE_INTERVAL`.

    Warnings
    ---------
    A master token is an *account* credential, not a scoped one — it is exchangeable for
    tokens to any Google service on the account. Keep it in a secrets store, never beside
    `client_secret.json`.

    """

    #: Seconds between edit queue flushes. Mutable per instance.
    QUEUE_INTERVAL: ClassVar[float] = 1.0

    def __init__(self, email: str, master_token: str, queue_interval: Union[float, None] = None) -> None:
        # ! Fail early — missing dependency is a packaging problem.
        if gpsoauth is None:
            raise KeepSyncError(f"{type(self).__name__} needs the `personal` extra: pip install gap[personal]")

        self.email: str = email
        self.queue_interval: float = self.QUEUE_INTERVAL if queue_interval is None else queue_interval

        self._master_token: str = master_token
        self._access_token: Union[str, None] = None
        self._version: Union[str, None] = None
        # * Client session identifier — not a secret, never used for auth.
        session_suffix: int = randrange(1000000000, 9999999999)  # noqa: S311
        self._session_id: str = f"s--{int(datetime.now(tz=UTC).timestamp() * 1000)}--{session_suffix}"

        # * Every part that exists, keyed by id.
        self._parts: dict[str, KeepBasePersonal] = {}
        # * Parts with unsent edits — keyed by id so repeated edits coalesce.
        self._queued: dict[str, KeepBasePersonal] = {}
        # * Current fold's entries by id. Empty outside of `_build_parts()`.
        self._pending: dict[str, NotePersonalPartsTyped] = {}
        # * True while folding a server response — suppresses queueing server changes back.
        self._applying: bool = False

    @classmethod
    def exchange_token(cls, email: str, oauth_token: str, android_id: str = ANDROID_ID) -> dict[str, str]:
        """Exchange a browser `oauth_token` cookie for a long lived master token.

        Sign in at https://accounts.google.com/EmbeddedSetup, click "I agree" — the page
        then hangs, which is expected — and read the `oauth_token` cookie. It starts with
        `oauth2_4/` and is single use.

        Parameters
        -----------
        email: :class:`str`
            The account address the token is minted for.
        oauth_token: :class:`str`
            The single use `oauth_token` cookie from the EmbeddedSetup flow.
        android_id: :class:`str`, optional
            The device identifier bound to the resulting token, by default ANDROID_ID.

        Returns
        --------
        dict[:class:`str`, :class:`str`]
            The raw gpsoauth response. The master token is under `"Token"`; on failure the
            dict carries Google's diagnostics in its place.

        """
        if gpsoauth is None:
            raise KeepSyncError(f"{cls.__name__}.exchange_token needs the `personal` extra: pip install gap[personal]")

        response: dict[str, str] = gpsoauth.exchange_token(email, oauth_token, android_id)
        # Only logged on the failure branch — a successful response holds the token.
        if "Token" not in response:
            LOGGER.warning("<%s.exchange_token> | No master token in response. | %s", cls.__name__, response)
        return response

    @property
    def version(self) -> Union[str, None]:
        """The sync cursor. `None` is a cold start — the key is omitted, not nulled."""
        return self._version

    @version.setter
    def version(self, value: Union[str, None]) -> None:
        # * Collapse "" to None — single "I know nothing" value for the payload builder.
        self._version = value or None

    def __enter__(self) -> Self:
        self.sync()
        return self

    def __exit__(self, *_: object) -> None:
        """Flush on the way out. Errors propagate — a failed sync must not look clean."""
        self.sync()

    # * Part bookkeeping — called by models, not by callers.
    def get_part(self, part_id: str) -> Union[KeepBasePersonal, None]:
        """Look a part up by id. Local only — never a request."""
        return self._parts.get(part_id)

    def register_part(self, part: KeepBasePersonal) -> None:
        """Put a part in the id map so an incoming change can find it.

        Raises
        -------
        :exc:`ValueError`
            If a different object is already registered under that id — always a bug, and
            overwriting would orphan whatever was there.

        """
        existing: Union[KeepBasePersonal, None] = self._parts.get(part.id)
        if existing is not None and existing is not part:
            raise ValueError(f"{part.id} is already registered to a different {type(existing).__name__}.")
        self._parts[part.id] = part

    def queue_part(self, part: KeepBasePersonal) -> None:
        """Mark a part as having unsent edits. Keyed by id, so repeats coalesce.

        Ignored while a server response is being folded in — see `_applying`.
        """
        if self._applying is True:
            return
        self._queued[part.id] = part

    def dump_state(self, path: Path) -> None:
        """Write every part's raw payload and the cursor to disk.

        For recovery, and for checking the shapes this module assumes against a real
        response — dump after a cold start and you have ground truth.

        Parameters
        -----------
        path: :class:`Path`
            The file to write. Overwritten if it exists.

        """
        state: dict[str, Any] = {
            "email": self.email,
            "version": self._version,
            "parts": {part_id: part.raw for part_id, part in self._parts.items()},
        }
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        LOGGER.info("<%s.dump_state> | Wrote %s parts. | %s", type(self).__name__, len(self._parts), path)

    # * Sync.
    def sync(self, **params: Any) -> None:
        """Exchange queued edits with the server and fold the response into the graph.

        Failure leaves the graph and queue untouched — the next call retries.

        Parameters
        -----------
        **params: :class:`Any`
            Forwarded to :meth:`_post`, and from there to `requests.post` — `timeout`,
            `proxies`, and so on. `timeout` defaults to `REQUEST_TIMEOUT`.

        Raises
        -------
        :exc:`KeepSyncError`
            If any request in the exchange fails. The graph is untouched and the queued
            edits are still queued.

        """
        # * Edits ride the first request only; later pages are pure reads.
        outbound: list[dict[str, Any]] = [part.to_dict() for part in self._queued.values()]
        pages: list[NotePersonalPartsTyped] = []
        # * Local cursor until the whole exchange succeeds.
        version: Union[str, None] = self._version

        while True:
            try:
                response: NotePersonalResponse = self._post(nodes=outbound, version=version, **params)
            except Exception as e:
                LOGGER.exception("<%s.sync> | Exchange failed; graph and queue untouched. | %s", type(self).__name__, self.email)
                raise KeepSyncError(f"Sync failed for {self.email}.") from e

            outbound = []

            if response.get("forceFullResync") is True:
                # ! Cursor unusable — restart cold. Pending edits go out on the retry.
                LOGGER.warning("<%s.sync> | Full resync demanded; restarting cold. | %s", type(self).__name__, self.email)
                self.version = None
                self.sync(**params)
                return

            pages.extend(response.get("nodes", []))
            version = response.get("toVersion", version)

            if response.get("truncated") is not True:
                break

        # Commit — graph, then cursor, then queue. Only reached on a clean exchange.
        self._build_parts(raws=pages)
        self.version = version
        self._queued.clear()

    def _post(self, nodes: list[dict[str, Any]], version: Union[str, None], **params: Any) -> NotePersonalResponse:
        """Send one `changes` request, refreshing the access token if it has expired.

        Parameters
        -----------
        nodes: list[dict[:class:`str`, :class:`Any`]]
            The parts being sent. Empty for a read.
        version: :class:`str` | None
            The cursor. `None` omits `targetVersion` entirely, which is a cold start.
        **params: :class:`Any`
            Passed through to `requests.post`.

        Returns
        --------
        :class:`NotePersonalResponse`
            The decoded response body.

        """
        params.setdefault("timeout", REQUEST_TIMEOUT)
        if self._access_token is None:
            self._refresh_access_token()

        payload: dict[str, Any] = self._build_payload(nodes=nodes, version=version)
        response: requests.Response = requests.post(KEEP_CHANGES_URL, json=payload, headers=self._headers(), **params)  # noqa: S113

        # * One retry for an expired token only.
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            LOGGER.info("<%s._post> | Access token expired; refreshing. | %s", type(self).__name__, self.email)
            self._refresh_access_token()
            response = requests.post(KEEP_CHANGES_URL, json=payload, headers=self._headers(), **params)  # noqa: S113

        response.raise_for_status()
        return response.json()

    def _headers(self) -> dict[str, str]:
        """The auth header. Note the scheme is "OAuth", not "Bearer"."""
        return {"Authorization": f"OAuth {self._access_token}"}

    def _refresh_access_token(self) -> None:
        """Mint a short lived access token from the master token.

        Raises
        -------
        :exc:`KeepSyncError`
            If Google returns no `Auth` value.

        """
        # * Narrowing guard — `__init__` already refused, but pyright can't see across methods.
        if gpsoauth is None:  # pragma: no cover - unreachable via __init__.
            raise KeepSyncError(f"{type(self).__name__} needs the `personal` extra: pip install gap[personal]")

        response: dict[str, str] = gpsoauth.perform_oauth(
            self.email,
            self._master_token,
            ANDROID_ID,
            service=KEEP_OAUTH_SCOPES,
            app=KEEP_ANDROID_APP,
            client_sig=KEEP_CLIENT_SIG,
        )
        token: Union[str, None] = response.get("Auth")
        if token is None:
            raise KeepSyncError(f"No access token in the auth response for {self.email}. | {response}")
        self._access_token = token

    def _build_payload(self, nodes: list[dict[str, Any]], version: Union[str, None]) -> dict[str, Any]:
        """Build the `changes` request envelope."""
        payload: dict[str, Any] = {
            "nodes": nodes,
            "clientTimestamp": keep_now(),
            "requestHeader": {
                "clientSessionId": self._session_id,
                "clientPlatform": "ANDROID",
                "clientVersion": {"major": "9", "minor": "9", "build": "9", "revision": "9"},
                "capabilities": [{"type": capability} for capability in CAPABILITIES],
            },
        }
        # Omitted entirely on a cold start. An absent key is not the same as a null one.
        if version is not None:
            payload["targetVersion"] = version
        return payload

    # * Building.
    def pending_children(self, parent_id: str) -> list[NotePersonalPartsTyped]:
        """Entries in the current fold belonging to `parent_id` and not nested under another."""
        return [raw for raw in self._pending.values() if raw.get("parentId") == parent_id and raw.get("superListItemId") is None]

    def pending_sub_items(self, item_id: str) -> list[NotePersonalPartsTyped]:
        """Entries in the current fold nested under `item_id`."""
        return [raw for raw in self._pending.values() if raw.get("superListItemId") == item_id]

    def _build_parts(self, raws: list[NotePersonalPartsTyped]) -> None:
        """Fold a whole exchange's worth of entries into the graph.

        Pages are collapsed by id first so ordering does not matter. Only root entries
        are constructed here — each one builds its own children from `_pending`.
        """
        self._pending = {raw["id"]: raw for raw in raws}
        self._applying = True
        try:
            for raw in list(self._pending.values()):
                if raw.get("parentId") != KEEP_ROOT:
                    continue
                existing: Union[KeepBasePersonal, None] = self._parts.get(raw["id"])
                if existing is not None:
                    existing.update(raw=raw)
                    continue
                KeepBasePersonal.from_raw(raw=raw, service=self)
            self._update_orphans()
        finally:
            self._applying = False
            self._pending = {}

    def _update_orphans(self) -> None:
        """Apply entries whose owner was not a root in this payload.

        Entries with no discoverable owner are discarded.
        """
        for raw in self._pending.values():
            if raw.get("parentId") == KEEP_ROOT:
                continue
            existing: Union[KeepBasePersonal, None] = self._parts.get(raw["id"])
            if existing is not None:
                existing.update(raw=raw)
                continue
            owner: Union[KeepBasePersonal, None] = self._parts.get(raw.get("superListItemId") or raw.get("parentId", ""))
            if owner is None:
                LOGGER.debug("<%s._update_orphans> | Discarding %s; no owner found.", type(self).__name__, raw["id"])
                self._parts.pop(raw["id"], None)
                continue
            child: Union[KeepBasePersonal, None] = KeepBasePersonal.from_raw(raw=raw, service=self)
            if child is None:
                continue
            collection: Union[KeepItemsPersonal[Any], None] = getattr(
                owner,
                "sub_items" if isinstance(child, KeepSubItemPersonal) else "items",
                None,
            )
            if collection is not None and child not in collection:
                collection.append(child)
