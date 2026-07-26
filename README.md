# GAP — GoogleAPI-Python

---

A typed Python wrapper around Google's API client libraries, giving you Calendar, Gmail and Keep behind a consistent, Pythonic interface instead of raw `googleapiclient` dicts.

![Version](https://img.shields.io/pypi/v/gap?label=PyPI)

### Key Features

---

- One shared OAuth2 flow (`GoogleService`) — token caching, refresh and the local-server login handshake are handled once, not per service.
- API responses are deserialized into typed model classes (`Events`, `EventsList`, `MailMessage`, `KeepNote`, ...) so you get attribute access and autocomplete instead of nested `dict` lookups.
- `Enum`-backed values for colors, event types, timezones and mail formats — no more magic strings.
- Draft classes (`EventsDraft`, `KeepNoteDraft`) validate your payload *before* it hits the API.
- Fully typed and verified with Pyright in strict mode. Ships `py.typed`.

## Table of Contents

- [Installation](#installation)
- [Services](#services)
- [Usage](#usage)
- [Credits](#credits)

# Installation

---

_Python 3.12 or higher is required_

```bash
# Linux/macOS/Windows
pip install gap
```

## Google Credentials

---

Every service needs an OAuth2 client secret from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

1. Create a project and enable the API you want (Calendar, Gmail and/or Keep).
2. Create an **OAuth client ID** of type *Desktop app* and download the JSON.
3. Save it as `client_secret.json` in a directory of your choosing — that directory is your `token_path`.

On first run the wrapper opens a browser for you to authorize, then caches the token
next to your secret (`calendar_token.json`, `mail_token.json`, `keep_token.json`).
Those token files are per-service because each one carries different scopes.

> ⚠️ Keep `client_secret.json` and every `*_token.json` out of version control.

## Configuring via `local.ini`

---

Rather than passing `token_path` at every call site, point a `[GAP]` section at the
directory your credentials live in:

```ini
[GAP]
# The directory holding client_secret.json and the cached *_token.json files.
# Relative paths are resolved against this file's directory, so `.` is next to the ini.
TOKEN_PATH = .
```

```python
from pathlib import Path

from gap import CalendarService

calendar = CalendarService.from_ini(file=Path("./local.ini"))
```

`from_ini` lives on `GoogleService`, so `MailService` and `KeepService` get it too.
A relative `TOKEN_PATH` is anchored to the ini file, never the CWD — the same config
resolves the same way no matter which directory you run from. Absolute paths (and `~`)
are honoured as written.
Note this configures *where* the credentials live — it does not replace them, since
`client_secret.json` and the token cache are Google's own formats.

### Storing your Calendar IDs

`CalendarService` also picks up a `[GAP.Calendars]` section — a plain `name = id`
mapping, so you can keep as many Calendars as you like out of your source:

```ini
[GAP.Calendars]
personal = primary
Work = c_abc123@group.calendar.google.com
Holidays = en.usa#holiday@group.v.calendar.google.com
```

Names keep the case you typed them in, and `get_calendar_list()` prints the Calendars
on your account in nearly this format already, so filling the section is copy/paste.

```python
calendar = CalendarService.from_ini(file=Path("./local.ini"))

# Every configured Calendar, no arguments needed.
events = calendar.get_all_events()

# Or grab one ID by name instead of pasting it around.
events = calendar.get_calendar_events_by_date(calendar_id=calendar.resolve_calendar("Work"))
```

`calendars` is a `list[CalendarID]` you can also set yourself; it is empty on a service
built with `CalendarService(token_path=...)`. Calling `get_all_events()` with nothing
configured raises rather than handing back an empty list. Use `ini_load_calendars()`
directly if you want the pairs without a service attached.

# Services

---

| Service | Google API | Scope |
| --- | --- | --- |
| `CalendarService` | Calendar v3 | `https://www.googleapis.com/auth/calendar` |
| `MailService` | Gmail v1 | `https://mail.google.com/` |
| `KeepService` | Keep v1 | `https://www.googleapis.com/auth/keep` |

> ⚠️ `KeepService` talks to the **official** Keep API, which is a Google Workspace
> service. It will not authorize a personal Gmail account, and `list_notes()` only
> returns notes your app created or that were explicitly shared with it. See
> `TODO.md` for notes on the unofficial personal-account route.

# Usage

---

## Calendar

```python
from datetime import datetime, timedelta
from pathlib import Path

from gap import CalendarColorEnum, CalendarService, EventsDraft, LocalTimeZoneEnum
from gap._types import EventsDraftTyped

calendar = CalendarService(token_path=Path(__file__).parent)

data: EventsDraftTyped = {
    "summary": "Google API Test Event",
    "location": "Seattle, Washington",
    "description": "The answer to everything is 42....",
    "start": {"dateTime": (datetime.now() + timedelta(hours=4)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
    "end": {"dateTime": (datetime.now() + timedelta(hours=5)).isoformat(), "timeZone": LocalTimeZoneEnum.PST},
    "reminders": {"useDefault": True},
    "colorId": CalendarColorEnum.bold_red,
}

draft = EventsDraft(calendar_id="primary", data=data)
event = calendar.create_event(event=draft)
print(event)
```

Finding the calendar you want, then pulling everything on it:

```python
# A human readable "Name | ID" listing of every calendar on the account.
print(calendar.get_calendar_list())

events = calendar.get_calendar_events_by_date(calendar_id="primary", max_results=25)
for event in events.events:
    print(event.summary, event.start)
```

## Gmail

```python
from pathlib import Path

from gap import MailMessage, MailService

mail = MailService(token_path=Path(__file__).parent)

message = MailMessage().to_email(
    to_email="someone@example.com",
    from_email="me@example.com",
    subject="Sent via GAP",
    body="Hello from the wrapper.",
)
draft = mail.create_draft(body=message)
```

## Keep

```python
from pathlib import Path

from gap import KeepNoteDraft, KeepService

keep = KeepService(token_path=Path(__file__).parent)
note = keep.create_note(draft=KeepNoteDraft(title="Groceries", list_items=[("Milk", False), ("Eggs", True)]))
print(note.text)
```

# Credits

---

Google and the related packages around their API.

[Repo]: https://github.com/k8thekat/GoogleAPI-python
[Issues]: https://github.com/k8thekat/GoogleAPI-python/issues
