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
- Services log through a module level `LOGGER` rather than a `_logger` class attribute.

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
