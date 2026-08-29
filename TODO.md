# GAP TODO

A small todo list local to the project.

Completed work is not tracked here — `CHANGELOG.md` is the record. This file is only
what is still open.

---

## `gap/services.py`

- 🗨 `ini_load_calendars()` builds its own parser with `optionxform = str` so a `Work` Calendar does not come back `work`. If a second case-sensitive section ever shows up, that parser setup wants factoring out of both loaders.
- 🗨 `search_messages()` returns one page of id/threadId stubs, so reading N results costs N+1 requests. A `walk` helper that follows `nextPageToken`, or a flag that fetches each message in full, would save callers the loop — kept out for now so the request count stays visible at the call site.
- 🗨 `create_event` / `update_event` swallow nothing — an `HttpError` propagates. `delete_event` catches and logs. Pick one policy and apply it across the board.
- 🗨 Add pagination to `get_calendar_events_by_date`; it currently ignores `nextPageToken`.

## `gap/_utils.py`

- 🗨 `_IRREGULAR_FIELDS` is a readability map, not a correctness one — the rule round trips `iCalUID` fine, just as the unreadable `i_cal_u_i_d`. Add a pair there for anything else that reads badly. The two shapes the rule genuinely cannot round trip are a key starting with a capital and a key that already contains an underscore; none of Calendar v3, Gmail v1 or Keep v1 sends either, so this is a latent edge rather than a live one.
- 🗨 The round-trip invariant (`to_camel_case(to_snake_case(key)) == key` across the whole known field set) is checked by hand right now. It wants to be the first thing in the test suite — it is the one property that, if it breaks, silently drops fields from request bodies.

## `gap/_calendar.py`

- 🗨 `Events` has no `from_draft()` helper — round-tripping a draft into an Event is manual.

## `gap/_mail.py`

- 🗨 `MailMessagePart.parts` nests but nothing walks it; a `flatten()` / `get_part(mime_type=...)` helper would save callers the recursion.

## `gap/_types.py`

- 🗨 `EventsTyped.created` / `updated` are annotated `str` (they are ISO strings on the wire). If we ever parse them to `datetime` on the way in, these need to change with it.

## Google Keep — Workspace (`KeepService`)

- ⚠️ Workspace-only, and the `notes.list` scoping claim is unverified. See `ISSUES.md`.

## Google Keep — consumer (`KeepServicePersonal`)

- ⚠️ **Never run against a live account.** Everything is verified against canned payloads; `exchange_token()` and `_refresh_access_token()` have never made a real request. This is the one thing blocking a move off `development`.
- ⚠️ The wire shapes are reconstructed rather than observed. Run `dump_state()` straight after the first cold sync and diff it against `_types.py`. See `ISSUES.md`.
- 🗨 `gpsoauth>=2.0.0` is the current release, not a tested floor. Pin to whatever version the first live run actually works against.
- 🗨 `KEEP_CLIENT_SIG` is redundant for `exchange_token()` — gpsoauth already defaults `client_sig` to the same Keep signature. Still needed for `perform_oauth()`, so it stays, but the duplication is worth a comment or a single source.
- 🗨 `_update_orphans()` is the one build path that is not parent driven; it exists for a delta carrying a lone entry whose owner is already held. Worth folding into the cascade if a neater shape presents itself.
- 🗨 Blob parts are parsed and discarded. Modelling them needs `getMediaLink`-style URL resolution, which is a separate piece of protocol.
- 🗨 The edit queue coalesces by id but nothing drives it on a timer — `queue_interval` is stored and unused until a caller schedules the flush. Either wire it to something or drop the attribute.
- 🗨 No backoff. A 429 raises `KeepSyncError` like anything else; `queue_interval` was meant to be the lever but is not yet read.

## Project

- 🗨 No test suite. `unit_test.py` in AMPAPI_Python is the pattern to copy; the OAuth flow needs mocking out, and the consumer Keep side is already exercised by canned payloads that want turning into real tests.
- ⭐ **DONE** `build.bash` now uses `uv build` instead of `python -m build` (which was shadowed by the repo's `build/` directory).
- 🗨 `docs/` + readthedocs are set up in AMPAPI_Python; GAP has neither.
- 🗨 `protobuf` moved 6.30.2 → 7.35.1 with the floors bump. Verified only to the extent that the package imports and the models work; no live API call has gone through it.
