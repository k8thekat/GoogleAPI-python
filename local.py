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
