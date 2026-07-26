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

from enum import IntEnum, StrEnum

__all__ = (
    "CalendarColorEnum",
    "EventTransparencyEnum",
    "EventTypeEnum",
    "LocalTimeZoneEnum",
    "MailFormatEnum",
    "MailLabelColorEnum",
    "MailLabelListVisiblityEnum",
    "MailMessageListVisibilityEnum",
    "MailTypeEnum",
)


class CalendarColorEnum(IntEnum):
    """The color swatches a Calendar Event can use.

    The Google API takes these as a stringified int via the `colorId` field.
    https://developers.google.com/calendar/api/v3/reference/colors
    """

    blue = 1
    green = 2
    purple = 3
    red = 4
    yellow = 5
    orange = 6
    turquoise = 7
    gray = 8
    bold_blue = 9
    bold_green = 10
    bold_red = 11


class EventTypeEnum(StrEnum):
    """The category of a Calendar Event.

    https://developers.google.com/calendar/api/v3/reference/events#eventType
    """

    default = "default"
    birthday = "birthday"
    focus = "focusTime"
    from_gmail = "fromGmail"
    out_of_office = "outOfOffice"
    working_location = "workingLocation"


class EventTransparencyEnum(StrEnum):
    """Whether an Event blocks time on the Calendar.

    Enums
    ------
    opaque: str
        The Event blocks time. Equivalent to "Show me as: Busy" in the Calendar UI.
    transparent: str
        The Event does not block time. Equivalent to "Show me as: Available".

    """

    opaque = "opaque"
    transparent = "transparent"


class LocalTimeZoneEnum(StrEnum):
    """The US timezones, as IANA names — which is the format the Google API expects."""

    EST = "America/New_York"
    CST = "America/Chicago"
    MTN = "America/Denver"
    PST = "America/Los_Angeles"


class MailFormatEnum(StrEnum):
    """How much of a Mail message the API should hand back.

    Enums
    ------
    minimal: str
        Metadata and labels only, no body.
    full: str
        The parsed payload including headers and body parts.
    raw: str
        The entire message base64url encoded in the `raw` field.
    metadata: str
        Headers and labels only.

    """

    minimal = "minimal"
    full = "full"
    raw = "raw"
    metadata = "metadata"


class MailMessageListVisibilityEnum(StrEnum):
    """Whether messages with this label show in the message list."""

    show = "show"
    hide = "hide"


class MailLabelListVisiblityEnum(StrEnum):
    """Whether the label itself shows in the label list."""

    label_show = "labelShow"
    label_show_if_unread = "labelShowIfUnread"
    label_hide = "labelHide"


class MailTypeEnum(StrEnum):
    """Who owns a Mail label.

    Enums
    ------
    system: str
        Labels created by Gmail.
    user: str
        Custom labels created by the user or application.

    """

    system = "system"
    user = "user"


class MailLabelColorEnum(StrEnum):
    """The subset of Gmail's allowed label colors we care about.

    Gmail only accepts colors from a fixed palette; passing anything else is a 400.
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels
    """

    black = "#000000"
    gray60 = "#999999"
    light_green = "#89d3b2"
    green = "#094228"
    white = "#ffffff"
    pumpkin_orange = "#aa8831"
    light_blue = "#6d9eeb"
