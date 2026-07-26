# ISSUES

---

## Google Keep — Account Type

⚠️ The official Keep API (`keep.googleapis.com` v1) is a **Google Workspace** service.

- It will not authorize a personal Gmail account.
- `notes.list` only returns notes the *authenticated app* created, plus notes explicitly
  shared with it. It is NOT a mirror of a personal account's Keep.
- There is no official REST API for personal accounts. The community route is the
  unofficial `gkeepapi` (master-token auth), which does not fit GAP's OAuth /
  `googleapiclient` pattern.

## Gmail — Scope Breadth

⚠️ `MailService.SCOPES` requests `https://mail.google.com/`, which is full mailbox
access including delete. The draft-only workflow GAP currently implements would be
satisfied by `gmail.compose`. Narrowing it is tracked in `TODO.md`.
