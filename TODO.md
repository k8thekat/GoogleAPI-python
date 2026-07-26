# GAP TODO

A small todo list local to the project. Legend: ⭐ done | 🗨 suggestion | ⚠️ issue | ⛔ removed

---

## `gap/services.py`

- ⭐ Factored the duplicated OAuth2 flow into a `GoogleService` base class.
- ⭐ `MailService` now takes `token_path` instead of resolving token/secret files against the CWD.
- ⭐ Replaced `print()` with lazy `%s` logging on a module level `LOGGER`.
- ⭐ `get_calendar_list()` no longer spins forever on an empty CalendarList, and now accumulates every page instead of only the last.
- ⭐ Split `get_calendars()` out so callers can get typed `CalendarList` objects rather than parsing the display string.
- ⭐ `since_time` / `upto_time` defaults moved out of the signature — `datetime.now()` there was evaluated once at import.
- ⭐ Reimplemented the ini loading that `setup()` used to do, as a module level `ini_load()` plus a `GoogleService.from_ini()` classmethod. The section key is now `[GAP]`.
- ⛔ Removed `setup()`. It parsed a `[FreshDesk]` ini section, which was leftover from another project, was unreachable, and returned a `(url, token)` tuple that meant nothing here.
- ⭐ Calendar IDs now live in the ini. Added `ini_load_calendars()` reading a `[GAP.Calendars]` `name = id` section into `list[CalendarID]`, `CalendarService.from_ini()` filling a per-instance `calendars`, `resolve_calendar(name)` for name → ID lookups, and `get_all_events(calendar=None)` defaulting to the configured set.
- ⛔ Dropped the `CALENDAR_IDS = a, b, c` / `getlist()` idea in favour of the section mapping. A flat list throws away the `name` half of `CalendarID`, and a section sidesteps escaping if an ID ever contains a comma. `ini_load()` keeps its `list` converter for other options.
- 🗨 `ini_load_calendars()` builds its own parser with `optionxform = str` so a `Work` Calendar does not come back `work`. If a second case-sensitive section ever shows up, that parser setup wants factoring out of both loaders.
- 🗨 `SCOPES` for `MailService` is `https://mail.google.com/` (full mailbox access). The draft-only workflow we implement would be satisfied by `gmail.compose`. Narrowing it forces every user to re-auth, so it is worth doing deliberately in one release.
- 🗨 `create_event` / `update_event` swallow nothing — an `HttpError` propagates. `delete_event` catches and logs. Pick one policy and apply it across the board.
- 🗨 Add pagination to `get_calendar_events_by_date`; it currently ignores `nextPageToken`.

## `gap/modules.py`

- ⭐ Split the `Resource` typing shims (`*Resource`) from the data models — they were the same classes doing both jobs.
- ⭐ `EventsList.__init__` built its `events` list inside the key loop, so it was wiped unless `items` happened to be the last key in the response.
- ⭐ `to_dict()` on `Events` / `EventsDraft` no longer leaks `_raw` and `calendar_id` into the request body.
- ⭐ `MailDraft.__init__` read `self.id` before it was assigned; `id` is now pulled first.
- ⭐ `EventsDraft.transparency` was `= Literal[...]` (an assignment holding a typing object) instead of an annotation. Now typed against `EventTransparencyEnum`.
- ⭐ Dropped the `Resource, dict` dual inheritance from the data models.
- 🗨 `Events` has no `from_draft()` helper — round-tripping a draft into an Event is manual.
- 🗨 `MailMessagePart.parts` nests but nothing walks it; a `flatten()` / `get_part(mime_type=...)` helper would save callers the recursion.

## `gap/_types.py`

- ⭐ Added `RemindersTyped` / `ReminderOverridesTyped` in place of the bare `dict` on `EventsDraftTyped`.
- ⭐ Added the Keep TypedDicts (`KeepNoteTyped`, `KeepNoteBodyTyped`, `KeepNoteListTyped`).
- ⭐ Renamed `EventUser` → `EventUserTyped` for consistency with every other TypedDict here.
- 🗨 `EventsTyped.created` / `updated` are annotated `str` (they are ISO strings on the wire). If we ever parse them to `datetime` on the way in, these need to change with it.

## Google Keep

- ⭐ Folded the staged `_keep_service.py` into the package: `KeepService` → `services.py`, `KeepNote*` → `modules.py`.
- ⚠️ The official Keep API is Workspace-only and `notes.list` only sees notes this app created. See `ISSUES.md`.
- 🗨 For personal accounts the only route is the unofficial `gkeepapi` (master-token auth). It does not fit the OAuth/`googleapiclient` pattern, so it would need its own service base if we ever want it.

## Project

- ⭐ Added `README.md` — the build was broken without it, `pyproject.toml` declares it as the readme.
- ⭐ Added `py.typed`; we advertise `Typing :: Typed` and were shipping no marker.
- ⭐ Pyright moved to `strict`, ruff to `select = ["ALL"]` with the shared ignore list, line length 140.
- ⭐ Replaced the 8 line `.gitignore` with the full Python one plus explicit credential rules.
- ⭐ Added the `build` / `changelog` workflows and issue template.
- ⭐ Moved the hardcoded `DWEEB_FAMILY_ID` out of `local.py` into a gitignored `local.ini`, in the structure the package already reads — `[GAP] TOKEN_PATH` and a `[GAP.Calendars]` name = id map. `local.py` now builds with `CalendarService.from_ini()` and looks the Calendar up by name.
- ⭐ `from_ini()` now resolves a relative `TOKEN_PATH` against the ini file's own directory via a new `resolve_ini_path()`, instead of `Path(value)` against the CWD. `TOKEN_PATH = .` means "next to the ini", so a clone works unedited. Absolute paths and `~` are honoured as written.
- ⭐ Added `local_example.ini` as the committed template — it is the only one of the pair that is tracked, so it must never hold a real ID.
- 🗨 No test suite. `unit_test.py` in AMPAPI_Python is the pattern to copy; the OAuth flow needs mocking out.
- 🗨 `_google.py` in the repo root is a Kuma_Kuma cog, not wrapper code. It belongs in that repo now that `KeepService` ships here.
- 🗨 `docs/` + readthedocs are set up in AMPAPI_Python; GAP has neither.
