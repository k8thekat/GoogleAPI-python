# ISSUES

Known limitations and unresolved unknowns. Anything actionable lives in `TODO.md`;
this file is for things we cannot fix from here, or have not yet confirmed.

---

## Google Keep — Workspace API, account type

.. warning::
    The official Keep API (`keep.googleapis.com` v1) is a **Google Workspace** service.
    It will not authorize a personal Gmail account, and there is no official REST API
    that will. `KeepService` is unusable on a consumer account; use
    `KeepServicePersonal` instead.

.. note::
    `notes.list` is widely reported to return only the notes the *authenticated app*
    created, plus notes explicitly shared with it — i.e. not a mirror of the account's
    Keep. This is **unverified**: it appears in neither the API overview nor the
    `notes.list` reference, both of which read as though the user's notes are returned.
    Treat it as a caveat to confirm before paying for a Workspace seat on the strength
    of it.

## Google Keep — consumer API, no specification

.. warning::
    `KeepServicePersonal` speaks `notes/v1/changes`, a private endpoint Google has never
    documented. The only sources for its behaviour are one reverse engineered client and
    captured traffic. Nothing here is guaranteed, and Google is under no obligation to
    keep any of it working.

.. note::
    The wire shapes in `_types.py` are reconstructed from a known field set, not from an
    observed response. Key names, types and enum values are read off the serialisation;
    id formats, `serverId` and `sortValue` magnitudes are representative rather than
    confirmed. `KeepServicePersonal.dump_state()` after a first cold sync is the intended
    way to check them against reality.

.. note::
    The `capabilities` array in the request header is a set of opaque two letter feature
    gates. They change what the server sends back. Send the set verbatim; pruning ones
    that look unnecessary is how you get responses missing fields.

## Google Keep — consumer API, structural constraints

.. warning::
    A `LIST` node carries no array of its children. The relationship exists only
    child to parent via `parentId`, so **a checklist payload cannot express "I no longer
    have this entry"**. Removal has to be written on the entry itself — `KeepItemsPersonal`
    sets the `deleted` timestamp on `__delitem__` for exactly this reason. A removal the
    server is never told about simply returns on the next sync.

.. note::
    A nested entry's `parentId` names the **checklist**, not the entry it sits under;
    `superListItemId` carries the nesting on its own. Whether the server treats `parentId`
    as authoritative for a nested entry, or derives it by following `superListItemId`, is
    unconfirmed. We write both consistently so it holds either way.

.. note::
    Blob parts (image, drawing, audio) arrive in the `nodes` array and are parsed but not
    modelled. `KeepBasePersonal.from_raw()` returns `None` for them.

## Google Keep — consumer API, credentials

.. warning::
    A master token is an **account** credential, not a scoped one. Unlike the per service
    OAuth tokens the rest of the package uses, it is exchangeable for tokens to any Google
    service on the account. Keep it in a secrets store — never beside `client_secret.json`,
    and never in the repo. Revoke it from the account's device list if the host is ever
    compromised.

.. note::
    The auth path has never made a live request. `exchange_token()` and
    `_refresh_access_token()` are the only code in the package that has not been executed,
    even against canned data.
