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

# ---------------------------------------------------------------------------
# Re-export hub.
#
# The models, Resource shims and utility functions used to live here. They are now
# split across `_utils.py`, `_resources.py`, `_calendar.py`, `_mail.py` and `_keep.py`.
# This file re-exports every public name so existing code that imports from
# `gap.modules` continues to work unchanged.
# ---------------------------------------------------------------------------
# ruff: noqa

from __future__ import annotations

from ._calendar import *
from ._keep import *
from ._mail import *
from ._resources import *
from ._utils import *

__all__ = (
    # _utils
    "to_camel_case",
    "to_snake_case",
    # _resources
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
    # _calendar
    "CalendarList",
    "CalendarListEntry",
    "Events",
    "EventsDraft",
    "EventsList",
    # _mail
    "MailDraft",
    "MailDraftList",
    "MailMessage",
    "MailMessageBody",
    "MailMessageHeader",
    "MailMessageList",
    "MailMessagePart",
    "MailUserLabel",
    "MailUserProfile",
    # _keep
    "KeepBasePersonal",
    "KeepChecklistPersonal",
    "KeepItemPersonal",
    "KeepItemsPersonal",
    "KeepNote",
    "KeepNoteDraft",
    "KeepNoteList",
    "KeepNotePersonal",
    "KeepSubItemPersonal",
    "NotesPartTypes",
    "keep_now",
)
