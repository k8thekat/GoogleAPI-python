from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Union

# google-api-python-client google-auth-httplib2 google-auth-oauthlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as Credentials_oa
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from calendar_ids import ids as Calendar_IDS
from modules import Calendar, CalendarColor, CalendarList, CalendarListEntry, Events, EventsList, LocalTimeZone

if TYPE_CHECKING:
    from google.auth.external_account_authorized_user import Credentials
    from googleapiclient.http import HttpRequest

    from _types import CalendarID


test_event: Events = Events(
    calendar_id="primary",
    **{
        "summary": "Testing...",
        "location": "400 Broad St, Seattle, WA 98109",
        "description": "TICKET_ID: XXXXXXX",
        "start": {
            "dateTime": datetime.now().isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": (datetime.now() + timedelta(hours=4)).isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "reminders": {"useDefault": True},
        # "attendees": [{"email": "cadwalladerkatelynn@gmail.com"}],  # leave this blank to auto accept the event.
        "colorId": CalendarColor.bold_red,
    },
)


def main() -> None:
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    c_id = "cadwalladerkatelynn@gmail.com"
    try:
        temp: Events = CalendarService().create_event(event=test_event, calendar_id=c_id)
        temp.summary = "Edited Event via API..."
        input("Event Created..continue?")
        e_temp: Events = CalendarService().update_event(temp)
        input("Event Updated... continue?")
        CalendarService().delete_event(e_temp)

    except HttpError as error:
        print(f"An error occurred: {error}")


class CalendarService:
    service: Calendar
    creds: Credentials_oa | Credentials | None
    SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/calendar",
    ]

    CALENDARIDS: ClassVar[list[CalendarID]] = Calendar_IDS

    def __init__(self) -> None:
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        self.creds = None
        if Path("token.json").exists():
            self.creds = Credentials_oa.from_authorized_user_file(filename="token.json", scopes=self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(request=Request())
            else:
                flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file="client_secret.json", scopes=self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with Path("token.json").open(mode="w") as token:
                token.write(self.creds.to_json())

        self.service = build(serviceName="calendar", version="v3", credentials=self.creds)

    def create_event(
        self,
        event: Events,
        calendar_id: str = "primary",
    ) -> Events:
        """
        Create an event for the calendar_id passed in.

        Parameters
        -----------
        event: :class:`Events`
            A Event class to pull the proper fields from.
        calendar_id: :class:`str`, optional
            The Calendar ID to be used, by default "primary".

        Returns
        --------
        :class:`Events`
            An :class:`Events` class from the response.
        """
        temp: HttpRequest = self.service.events().insert(calendarId=calendar_id, body=event.__dict__)
        res = Events(calendar_id=calendar_id, **temp.execute())

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

    def get_all_events(self, calendar: Union[list[CalendarID], None] = None) -> list[Events]:
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
        if calendar is None:
            calendar = self.CALENDARIDS
        temp: list[Events] = []
        for e in calendar:
            res: EventsList = CalendarService().get_calendar_events_by_date(
                since_time=datetime.now(),
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


if __name__ == "__main__":
    main()
