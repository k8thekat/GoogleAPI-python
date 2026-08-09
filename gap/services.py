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

import logging
from configparser import ConfigParser
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self, Union

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
    KeepNote,
    KeepNoteDraft,
    KeepNoteList,
    KeepResource,
    MailDraft,
    MailDraftList,
    MailMessage,
    MailMessageList,
    MailUserLabel,
    MailUserProfile,
    MailUserResource,
    to_snake_case,
)

if TYPE_CHECKING:
    from google.auth.external_account_authorized_user import Credentials
    from googleapiclient.http import HttpRequest

    from ._enums import LocalTimeZoneEnum
    from ._types import EventsDraftTyped, LabelID

__all__ = (
    "CalendarService",
    "GoogleService",
    "KeepService",
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
        temp: HttpRequest = self.service.events().insert(calendarId=event.calendar_id, body=event.to_dict())
        return Events(calendar_id=event.calendar_id, **temp.execute())

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
        temp: HttpRequest = self.service.events().delete(calendarId=event.calendar_id, eventId=event.id)
        try:
            res: Any = temp.execute()
        except HttpError as e:
            LOGGER.warning("<%s.delete_event> | We encountered an error. | %s", type(self).__name__, e)
            return

        # A successful delete comes back as an empty body.
        if not res:
            return
        raise ValueError(f"Unexpected response when calling CalendarService.delete_event. | Value: {res}")

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
            temp: HttpRequest = self.service.events().get(calendarId=calendar_id, eventId=event_id)
        else:
            temp = self.service.events().get(calendarId=calendar_id, eventId=event_id, timeZone=timezone)
        return Events(calendar_id=calendar_id, **temp.execute())

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

        temp: HttpRequest = self.service.events().list(
            calendarId=calendar_id,
            timeMin=self._to_rfc3339(value=since_time),
            timeMax=self._to_rfc3339(value=upto_time),
            maxResults=max_results,
            singleEvents=single_events,
            orderBy=order_by,
        )
        return EventsList(calendar_id=calendar_id, **temp.execute())

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
        temp: list[CalendarList] = []
        page_token: Union[str, None] = None
        while True:
            res = CalendarListEntry(**self.service.calendarList().list(pageToken=page_token).execute())
            if len(res.events) == 0:
                LOGGER.info("<%s.get_calendars> | Unable to find any Calendars in our CalendarList.", type(self).__name__)
            temp.extend(res.events)

            # No token means that was the last page — break regardless of what we got.
            page_token = res.next_page_token
            if not page_token:
                break
        return temp

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

        temp: list[Events] = []
        for entry in calendar:
            res: EventsList = self.get_calendar_events_by_date(calendar_id=entry.get("id", "primary"))
            if len(res.events) == 0:
                LOGGER.info("<%s.get_all_events> | No upcoming Events on %s.", type(self).__name__, entry.get("id"))
                continue
            temp.extend(res.events)
        return temp

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

        temp: HttpRequest = self.service.events().update(
            calendarId=event.calendar_id,
            eventId=event.id,
            body=event.to_dict(),
        )
        return Events(calendar_id=event.calendar_id, **temp.execute())


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
        temp: HttpRequest = self.service.users().getProfile(userId=user_id)
        return MailUserProfile(**temp.execute())

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
        temp: dict[str, Any] = self.service.users().labels().list(userId=user_id).execute()
        res: list[MailUserLabel] = [MailUserLabel(**label) for label in temp.get("labels", [])]

        # Replace rather than extend — this mirrors the last response, and appending to it
        # gave us every label twice on the second call.
        # Uppercase because it is part of our public surface, but it is a per-instance
        # cache rather than a constant — pyright reads the casing as the latter.
        self.LABELS = [{"name": label.name, "id": label.id} for label in res]  # pyright: ignore[reportConstantRedefinition]
        return res

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

        temp: HttpRequest = self.service.users().messages().list(**params)
        return MailMessageList(**temp.execute())

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
                temp: HttpRequest = self.service.users().messages().get(userId=user_id, id=message_id)
            else:
                temp = self.service.users().messages().get(userId=user_id, id=message_id, format=message_format)
            res = MailMessage(**temp.execute())
        except HttpError as e:
            LOGGER.warning("<%s.get_message> | Failed to get the message %s. | %s", type(self).__name__, message_id, e)
            return None
        return res

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
        temp: HttpRequest = self.service.users().drafts().create(userId=user_id, body=body.prepared())
        return MailDraft(**temp.execute())

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
        temp: HttpRequest = self.service.users().drafts().list(userId=user_id, maxResults=max_results)
        return MailDraftList(**temp.execute())

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
                temp: HttpRequest = self.service.users().drafts().get(userId=user_id, id=message_id)
            else:
                temp = self.service.users().drafts().get(userId=user_id, id=message_id, format=message_format)
            res = MailDraft(**temp.execute())
        except HttpError as e:
            LOGGER.warning("<%s.get_draft> | Failed to get the Draft %s. | %s", type(self).__name__, message_id, e)
            return None
        return res.message

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
        temp: HttpRequest = self.service.users().drafts().update(userId=user_id, id=message_id, body=body.prepared())
        res = MailDraft(**temp.execute())
        return res.message

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
        temp: Union[MailMessage, None] = self.get_draft(
            message_id=message_id,
            message_format=MailFormatEnum.full,
            user_id=user_id,
        )
        if temp is None:
            LOGGER.warning("<%s.append_draft> | Failed to find the Draft %s.", type(self).__name__, message_id)
            return None

        return self.update_draft(message_id=message_id, body=temp.update_email(body=body), user_id=user_id)


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
        temp: HttpRequest = self.service.notes().create(body=draft.to_dict())
        return KeepNote(**temp.execute())

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
        temp: HttpRequest = self.service.notes().get(name=self._as_resource_name(name=name))
        return KeepNote(**temp.execute())

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
        temp: HttpRequest = self.service.notes().list(pageSize=page_size, filter=note_filter, pageToken=page_token)
        return KeepNoteList(**temp.execute())

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
        temp: HttpRequest = self.service.notes().delete(name=self._as_resource_name(name=name))
        try:
            res: Any = temp.execute()
        except HttpError as e:
            LOGGER.warning("<%s.delete_note> | We encountered an error. | %s", type(self).__name__, e)
            return

        # A successful delete comes back as an empty body.
        if not res:
            return
        raise ValueError(f"Unexpected response when calling KeepService.delete_note. | Value: {res}")

    @staticmethod
    def _as_resource_name(name: str) -> str:
        """Normalize a bare note ID into the "notes/xxxx" resource name the API wants."""
        return name if name.startswith("notes/") else f"notes/{name}"
