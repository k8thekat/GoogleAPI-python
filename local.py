# test_event: Events = Events(
#     calendar_id="primary",
#     **{
#         "summary": "Testing...",
#         "location": "400 Broad St, Seattle, WA 98109",
#         "description": "TICKET_ID: XXXXXXX",
#         "start": {
#             "dateTime": datetime.now().isoformat(),
#             "timeZone": "America/Los_Angeles",
#         },
#         "end": {
#             "dateTime": (datetime.now() + timedelta(hours=4)).isoformat(),
#             "timeZone": "America/Los_Angeles",
#         },
#         "reminders": {"useDefault": True},
#         # "attendees": [{"email": "cadwalladerkatelynn@gmail.com"}],  # leave this blank to auto accept the event.
#         "colorId": CalendarColor.bold_red,
#     },
# )


# test_label: MailUserLabel = MailUserLabel(
#     **{
#         "id": "123456",
#         "name": "Test Label",
#         "messageListVisilibity": MailMessageListVisibilityEnum.show,
#         "labelListVisibility": MailLabelListVisiblityEnum.label_show,
#         "type": MailTypeEnum.user,
#         "color": MailLabelColorEnum.light_blue,
#     },
# )
# test_email: EmailMessage = EmailMessage()
# test_email = MailMessage().to_email(
#     to_email="test@gmail.com",
#     from_email="the_doctor@gmail.com",
#     subject="UPDATED Second test DRAFT CREATION~",
#     body="UPDATED UNK..",
# )

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from gap._enums import CalendarColorEnum, LocalTimeZoneEnum
from gap._types import EventsDraftTyped
from gap.services import CalendarService, EventsDraft

dweeb_family_id = "8d0382910b83b346b08292060faf48d67c45a286a97f69e5b16469a8e88b27c4@group.calendar.google.com"

data: EventsDraftTyped = {
    "summary": "Kat - Google API Test Event",
    "location": "Seattle, Washington",
    "description": "The answer to everything is 42....",
    "start": {"dateTime": (datetime.now() + timedelta(hours=4)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
    "end": {"dateTime": (datetime.now() + timedelta(hours=5)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
    "reminders": {"useDefault": True},
    "colorId": CalendarColorEnum.bold_red,
}
test_event = EventsDraft(calendar_id=dweeb_family_id, data=data)


def test_func() -> None:
    calendar = CalendarService(token_path=Path(__file__).parent)
    print(calendar.create_event(event=test_event))


test_func()
# asyncio.run(test_func())
