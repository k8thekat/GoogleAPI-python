from __future__ import annotations

import configparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Union

# google-api-python-client google-auth-httplib2 google-auth-oauthlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as Credentials_oa
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from ._enums import MailFormatEnum
from .modules import (
    Calendar,
    CalendarList,
    CalendarListEntry,
    Events,
    EventsList,
    LocalTimeZone,
    MailDraft,
    MailMessage,
    MailUser,
    MailUserLabel,
)

if TYPE_CHECKING:
    from google.auth.external_account_authorized_user import Credentials
    from googleapiclient.http import HttpRequest

    from ._types import CalendarID, LabelID


class CalendarService:
    """
    Store the calendar_token.json and calendar_secret.json file in the same directory as the `services.py` file and point `token_path` to their directory.
    """

    service: Calendar
    service_name: ClassVar[str] = "calendar"
    service_version: ClassVar[str] = "v3"
    creds: Credentials_oa | Credentials | None
    SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/calendar",
    ]

    def __init__(self, token_path: Path) -> None:
        """
        Parameters:
        token_path: :class:`Path`
            Must point to the directory which contains your "calendar_secret.json" from Google API.
        """
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        self.creds = None
        if token_path.joinpath("calendar_token.json").exists():
            self.creds = Credentials_oa.from_authorized_user_file(
                filename=token_path.joinpath("calendar_token.json"), scopes=self.SCOPES
            )
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(request=Request())
            else:
                flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file=token_path.joinpath("client_secret.json"), scopes=self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with token_path.joinpath("calendar_token.json").open(mode="w") as token:
                token.write(self.creds.to_json())

        self.service = build(serviceName="calendar", version="v3", credentials=self.creds)

    # todo - Fully implement support for ini parsing instead of using json files.
    def setup(self, path: Path) -> Any:
        parser = configparser.ConfigParser()
        if isinstance(path, Path) and path.exists():
            parser.read(filenames=path)
            if "FreshDesk" in parser.sections():
                tokens: configparser.SectionProxy = parser["FreshDesk"]
                return (tokens.get("url", ""), tokens.get("token", ""))

        else:
            raise ValueError("Failed to find `FreshDesk` section in token.ini file.")

    # todo - Rebuild how or what we use as a class/object to unpack all our data.
    def create_event(
        self,
        event: Events,
    ) -> Events:
        """
        Create an event for the calendar_id passed in.

        Parameters
        -----------
        event: :class:`Events`
            A Event class to pull the proper fields from.

        Returns
        --------
        :class:`Events`
            An :class:`Events` class from the response.
        """
        temp: HttpRequest = self.service.events().insert(calendarId=event.calendar_id, body=event.__dict__)
        res = Events(calendar_id=event.calendar_id, **temp.execute())

        return res

    def delete_event(self, event: Events) -> None:
        """
        Delete the passed in :class:`Events` object.

        Parameters
        -----------
        event: :class:`Events`
            The Event to delete..

        Returns
        --------
        None
        """
        temp: HttpRequest = self.service.events().delete(calendarId=event.calendar_id, eventId=event.id)
        try:
            res: HttpRequest | str = temp.execute()
        except HttpError:
            return None
        if isinstance(res, str) and len(res) == 0:
            return None
        else:
            print(f"Error Deleting the event..{res}")
            return None

    def get_event(self, event_id: str, calendar_id: str = "primary", timezone: Union[LocalTimeZone, None] = None) -> Events:
        """
        Retrieve a specific Event

        Parameters
        -----------
        event_id: :class:`str`
            The ID of the Event. See :class:`Events.id` value.
        calendar_id: :class:`str`, optional
            The Calendar ID to be used, by default "primary".
        timezone: :class:`Union[LocalTimeZone, None]`, optional
            Time zone used in the response. Optional. The default is the time zone of the calendar.

        Returns
        --------
        :class:`Events`
            An :class:`Events` class from the response..
        """
        if timezone is None:
            temp: HttpRequest = self.service.events().get(calendarId=calendar_id, eventId=event_id)
        else:
            temp: HttpRequest = self.service.events().get(calendarId=calendar_id, eventId=event_id, timeZone=timezone)
        res = Events(**temp.execute())
        res.calendar_id = calendar_id
        return res

    def get_calendar_events_by_date(
        self,
        calendar_id: str = "primary",
        since_time: datetime = datetime.now(),
        upto_time: datetime = (datetime.now() + timedelta(days=30)),
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> EventsList:
        """
        Returns a list of Events sorted by the parameters passed in.

        Parameters
        -----------
        since_time: :class:`datetime`
            Default is `datetime.now()`
        upto_time: :class:`datetime`
            Default is 30 days in the future from now.
        max_results: :class:`int`, optional
            _description_, by default 10.
        single_events: :class:`bool`, optional
            _description_, by default True.
        order_by: :class:`str`, optional
            "startTime": Order by the start date/time (ascending). This is only available when querying single events (i.e. the parameter singleEvents is True)
            "updated": Order by last modification time (ascending).
        """
        # TODO - See about storing calendar_id to each event.
        since_time = since_time.replace(tzinfo=None)
        return EventsList(
            calendar_id=calendar_id,
            **self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=since_time.isoformat() + "Z",
                timeMax=upto_time.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=single_events,
                orderBy=order_by,
            )
            .execute(),
        )

    def get_calendar_list(self) -> str:
        """
        Returns a str of every calendar available to the User.
        """
        page_token = None
        while True:
            calendar_list = CalendarListEntry(**self.service.calendarList().list(pageToken=page_token).execute())
            temp: list[CalendarList] = []
            if len(calendar_list.events) == 0:
                print("Unable to find any 'Events' in our CalendarList")
            else:
                temp.extend(calendar_list.events)
                page_token: str | None = calendar_list.nextPageToken
                if not page_token:
                    break
        return "\n".join(f"Name: {e.summary} | ID: {e.id}" for e in temp)

    def get_all_events(self, calendar: list[CalendarID]) -> list[Events]:
        """
        Get's all events from the current time into the future for a specific set of Calendars or use `self.CALENDARIDS`.

        Parameters
        -----------
        calendar: :class:`Union[list[CalendarID], None]`, optional
            If None, uses :class:`CalendarService.CALENDARIDS` as the value to pull from. Otherwise provide a list of CalendarID dicts.

        Returns
        --------
        :class:`list[Events]`
            A list of :class:`Events` with populated fields.
        """
        temp: list[Events] = []
        for e in calendar:
            res: EventsList = self.get_calendar_events_by_date(
                calendar_id=e.get("id", "primary"),
            )
            events: list[Events] = res.events

            if len(events) == 0:
                print("No upcoming events found.")
                continue
            temp.extend(events)
        return temp

    def update_event(self, event: Events) -> Events:
        """
        Update an Event.

        Parameters
        -----------
        event: :class:`Events`
            A Event class to overwrite the fields with.
        Returns
        --------
        :class:`Events`
            An :class:`Events` class from the response.
        """
        temp: HttpRequest = self.service.events().update(calendarId=event.calendar_id, eventId=event.id, body=event.__dict__)
        return Events(calendar_id=event.calendar_id, **temp.execute())


class MailService:
    service: MailUser
    service_name: ClassVar[str] = "gmail"
    service_version: ClassVar[str] = "v1"
    creds: Credentials_oa | Credentials | None
    SCOPES: ClassVar[list[str]] = [
        "https://mail.google.com/",
    ]
    # https://developers.google.com/workspace/gmail/api/quickstart/python
    LABELS: list[LabelID]

    def __init__(self) -> None:
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        self.creds = None
        if Path("mail_token.json").exists():
            self.creds = Credentials_oa.from_authorized_user_file(filename="mail_token.json", scopes=self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(request=Request())
            else:
                flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file="mail_client_secret.json", scopes=self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with Path("mail_token.json").open(mode="w") as token:
                token.write(self.creds.to_json())

        self.service = build(serviceName=self.service_name, version=self.service_version, credentials=self.creds)

    def get_labels(self, user_id: str = "me") -> list[MailUserLabel]:
        """
        Gets all the labels related to the Google Mail Account.

        Will also update our "LABELS" attribute.

        Parameters
        -----------
        user_id: :class:`str`, optional
            The ID of the Google Account, by default "me".

        Returns
        --------
        :class:`list[MailUserLabel]`
            A list of MailUserLabel objects.
        """

        temp = self.service.users().labels().list(userId=user_id).execute()
        res: list[MailUserLabel] = [MailUserLabel(**i) for i in temp.get("labels")]
        labels: list[LabelID] = getattr(self, "LABELS", [])
        labels.extend({"name": label.name, "id": label.id} for label in res)
        setattr(self, "LABELS", labels)
        return res

    def create_draft(self, body: MailMessage, user_id: str = "me") -> MailDraft:
        temp = self.service.users().drafts().create(userId=user_id, body=body.prepared()).execute()
        return MailDraft(**temp)

    def get_draft(
        self, message_id: str, message_format: MailFormatEnum | str | None = None, user_id: str = "me"
    ) -> MailMessage | None:
        """
        Get an existing Draft from our Mailbox.

        Parameters
        -----------
        message_id: :class:`str`
            The ID of the message to search for, this is the :class:`MailDraft.id` attribute.
        message_format: :class:`MailFormatEnum`, optional
            The Type of format to return the message in, by default MailFormatEnum.raw.
        user_id: :class:`str`, optional
            The Google User ID to search under, by default "me".

        Returns
        --------
        :class:`MailMessage`
            _description_.
        """
        if not message_id.startswith("r"):
            raise ValueError("Your message_id is not of the right type. It will start with an 'r'")
        try:
            if message_format is None:
                temp: HttpRequest = self.service.users().drafts().get(userId=user_id, id=message_id)
            else:
                temp: HttpRequest = self.service.users().drafts().get(userId=user_id, id=message_id, format=message_format)
        except HttpError as e:
            print(e)
            return None
        res = MailDraft(**temp.execute())
        return res.message

    def update_draft(self, message_id: str, body: MailMessage, user_id: str = "me") -> MailMessage:
        temp: HttpRequest = self.service.users().drafts().update(userId=user_id, id=message_id, body=body.prepared())
        res = MailDraft(**temp.execute())
        return res.message

    def append_draft(self, message_id: str, body: str, user_id: str = "me") -> MailMessage | None:
        temp: MailMessage | None = self.get_draft(message_id=message_id, message_format=MailFormatEnum.full, user_id=user_id)
        if temp is None:
            print(f"Failed to find the Draft Message ID provided. | {message_id}")
            return None
        res: MailMessage = self.update_draft(message_id=message_id, body=temp.update_email(body=body))
        return res


# if __name__ == "__main__":
#     main()
