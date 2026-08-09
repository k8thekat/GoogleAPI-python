# Changelog

## 4.0.0

> ⚠️ **Breaking release.** See "Migrating from 3.x" at the bottom.

### Breaking

- `MailService.__init__` now requires `token_path: Path`, matching `CalendarService`.
  It previously resolved `mail_token.json` and `mail_client_secret.json` against the
  current working directory, so it silently broke depending on where you launched from.
- `GoogleService` is now the base class for every service. `CalendarService`,
  `MailService` and `KeepService` inherit the OAuth2 flow and only declare
  `service_name`, `service_version`, `token_name` and `SCOPES`.
- The `Resource` typing shims were split out of the data models. `Calendar` is now
  `CalendarResource`, and `MailUser` is now `MailUserResource`. The names you actually
  consume — `Events`, `EventsList`, `CalendarList`, `CalendarListEntry`, `MailDraft`,
  `MailMessage`, `MailUserLabel` — kept their names but are plain classes now; they no
  longer inherit `Resource` or `dict`.
- `CalendarService.setup()` removed and reimplemented. It parsed a `[FreshDesk]` ini
  section, leftover from another project, and returned a `(url, token)` tuple that had
  no meaning here. Replaced by `ini_load()` + `GoogleService.from_ini()`, reading a
  `[GAP]` section.
- `_types.EventUser` renamed to `EventUserTyped`, for consistency with the rest of the module.
- **Every data model attribute is snake_case now.** They used to be whatever Google sent,
  because the models `setattr` straight off the response — so the wire's camelCase leaked
  into the Python surface. Models convert on the way in, and `to_dict()` / `prepared()`
  convert back, so the request bodies are unchanged. `event.htmlLink` → `event.html_link`,
  `message.labelIds` → `message.label_ids`, `draft_list.nextPageToken` →
  `draft_list.next_page_token`, and so on for every model in the package.
  Two things deliberately keep the API's casing: the `_types.py` TypedDicts, which *are*
  request bodies, and any raw dict we hold verbatim — `Events.start`, `reminders`, a Keep
  note `body`. `EventsDraft` accepts either spelling, as it did before.
- Services log through a module level `LOGGER` rather than a `_logger` class attribute.
- `MailService.SCOPES` narrowed from `https://mail.google.com/` — full mailbox control,
  permanent delete included — to `gmail.readonly` + `gmail.compose`, which covers every
  method on the class. **This invalidates your existing `mail_token.json`**; the next
  call re-runs the browser flow on its own (see the `_authorize` fix below) and you will
  be asked to grant the new pair.

### Fixed

- `EventsList` built its `events` list *inside* the response key loop and reset it on
  every iteration, so the list was empty unless `items` happened to be the last key
  in the JSON response. Events were silently dropped.
- `CalendarService.get_calendar_list()` had no `break` on the empty-CalendarList branch
  and would spin forever. It also rebuilt its accumulator inside the loop, so it only
  ever returned the final page.
- `Events.to_dict()` and `EventsDraft.to_dict()` returned the raw `__dict__`, sending
  our internal `_raw` and `calendar_id` attributes to Google as part of the Event body
  on every `create_event` / `update_event`.
- `MailDraft.__init__` read `self.id` while constructing its `MailMessage`, before `id`
  was guaranteed to have been set — it only worked when `id` preceded `message` in the
  response. `id` is now pulled explicitly first.
- `EventsDraft.transparency` was `= Literal["opaque", "transparent"]`, an assignment
  storing a typing object as a class attribute rather than an annotation. It is now
  typed against the new `EventTransparencyEnum`.
- `get_calendar_events_by_date` had `datetime.now()` as a parameter default, which is
  evaluated once at import — the query window was pinned to interpreter start time for
  the life of the process. Both time bounds now default to `None` and resolve per call.
- `MailUsersResource.labels()` / `.drafts()` chained through `users()` a second time in
  the shim, which mistyped the call chain.
- `raise ValueError("...%s", value)` in several spots built a two-element tuple instead
  of formatting the message. Now uses f-strings.
- `MailMessageBody` decoded its base64 `data` with a bare `.decode()`, so a body that was
  not valid UTF-8 raised `UnicodeDecodeError`. That fires while `MailMessage(**payload)`
  is being built, meaning one malformed message took down the whole response rather than
  just its own part. Now decodes with `errors="replace"`; `_raw["data"]` still holds the
  original base64 if you need the bytes.
- `MailService.get_labels()` extended the `LABELS` cache instead of replacing it, so every
  call after the first duplicated the entire label set.
- `GoogleService._authorize()` let a `RefreshError` out of `creds.refresh()`. A revoked
  token, or one cached under different `SCOPES` than the service now asks for, crashed
  every call until you worked out that the token file had to be deleted by hand. It now
  logs and falls through to the browser flow, which is what the token file being unusable
  means in the first place.

### Added

- `KeepService`, `KeepNote`, `KeepNoteDraft` and `KeepNoteList` folded into the package
  from the staged `_keep_service.py`. Note the Workspace-account caveat in `ISSUES.md`.
- `ini_load()` and `GoogleService.from_ini()` — configure `TOKEN_PATH` from a `[GAP]`
  section of a `local.ini` instead of hardcoding the path at every call site. Available
  on all three services since it lives on the base.
- `ini_load_calendars()` and `CalendarService.calendars` — keep your Calendar IDs in a
  `[GAP.Calendars]` `name = id` section instead of pasting them at call sites.
  `CalendarService.from_ini()` populates `calendars` from it; `resolve_calendar(name)`
  looks a single ID up by name. Names keep their case, unlike the rest of the ini.
- `CalendarService.get_all_events()` — `calendar` is now optional and defaults to the
  Calendars loaded from the ini. It raises `ValueError` when there are none either way,
  rather than returning an empty list that looks like "no upcoming Events".
- `CalendarService.get_calendars()` — the typed `list[CalendarList]` behind
  `get_calendar_list()`, so callers stop parsing the display string.
- `MailService.get_profile()` and `MailService.get_drafts()`.
- `MailService.search_messages()` — search the mailbox with the same query syntax as the
  Gmail search bar, optionally filtered by Label ID and scoped past SPAM/TRASH. Returns a
  page of results plus the `nextPageToken` to ask for the next one.
- `MailService.get_message()` — fetch one message by ID. Mirrors `get_draft`: logs and
  returns None on `HttpError` rather than raising.
- `MailMessageList`, the response model for the above, and `MailMessagesResource`, the
  typing shim for `users().messages()`. `MailUsersResource` grew a `messages()` accessor;
  the mail side previously had no typed entry point to the messages endpoints at all.
- `MailUsersResource` is now exported from `gap.modules`; it was reachable off
  `MailUserResource.users()` but was missing from `__all__`.
- `to_snake_case()` / `to_camel_case()` — the field name conversion the models run on,
  exported because `update_event` needs it to apply a camelCase change set onto a model,
  and because anything building request bodies by hand will want the same mapping.
- `EventTransparencyEnum`.
- `RemindersTyped` / `ReminderOverridesTyped`, replacing the bare `dict` annotation.
- `Keep` TypedDicts: `KeepNoteTyped`, `KeepNoteBodyTyped`, `KeepNoteListTyped`.
- `__len__` / `__iter__` on `EventsList`, `KeepNoteList` and `MailDraftList`.
- `__hash__` on `Events` — it defined `__eq__` without one, making it unhashable.
- `py.typed`, so the type information we advertise actually reaches consumers.
- `README.md`, `TODO.md`, `NOTES.md`, `ISSUES.md`, `CLAUDE.md`, `MANIFEST.in`.
- `build` and `changelog` GitHub workflows, and an issue template.

### Changed

- Every module carries the GPL header and `from __future__ import annotations`.
- All autoDocstring `_description_` / `_type_` placeholders filled in.
- Pyright moved from `standard` to `strict`; ruff to `select = ["ALL"]` with the shared
  ignore list; line length 125 → 140.
- `.gitignore` replaced with the full Python one plus explicit credential rules.
- `local.py` is now an argparse dev driver instead of a script that created a real
  calendar event as an import side effect.

### Migrating from 3.x

```python
# 3.x
mail = MailService()

# 4.0.0
mail = MailService(token_path=Path(__file__).parent)
```

If you referenced the shim classes directly, `Calendar` → `CalendarResource` and
`MailUser` → `MailUserResource`. If you relied on the data models being `dict`
subclasses (`event["summary"]`), use attribute access or `to_dict()` instead.

Model attributes are snake_case, so any multi-word field you read needs renaming:

```python
# 3.x
link, labels, token = event.htmlLink, message.labelIds, drafts.nextPageToken

# 4.0.0
link, labels, token = event.html_link, message.label_ids, drafts.next_page_token
```

Request bodies are unaffected — `to_dict()` and `prepared()` still emit Google's keys, and
anything you pass *in* as a `TypedDict` is still the API's camelCase shape.

`MailService` asks for narrower `SCOPES` than 3.x did, so your cached `mail_token.json`
cannot be renewed against them. Nothing to do by hand — the first call after upgrading
logs a warning and reopens the browser consent screen, then caches the new token.

`MailService` still looks for `mail_client_secret.json` before falling back to the
shared `client_secret.json`, so existing credential layouts keep working — you only
need to point `token_path` at the directory they already live in.

---

## 3.0.1

- Version bump to force client update.

## 3.0.0

- Updated the `__repr__` format for `Events` and `EventsList`.
- Fixed logic inside `update_event`.
- Fixed `EventsDraft.__init__` not setting the `start` and `end` attributes.
- Fixed typos in `_types.py`, `modules.py` and `services.py`.
- Started implementing logging in the `services.py` classes.
- Refactored `create_event` with Enums and Types for better data validation.
