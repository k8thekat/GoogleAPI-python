# Notes

---

- Use UV to handle packages.
- Build via `build.bash` — it checks you are in the VENV and confirms the `__init__.py` version before tagging.

### Commit Message Structure

```
# "Overall Summary of changes" (DONT INCLUDE VERSION)
- change 1 (a filename or class or key topic; etc..)
-- sub change 1

## "ISSUES?"
- change 2
-- sub change 2

## "New?"
- new change 1
-- sub new change 1
-- sub new change 2
- change 2
-- sub new ...

```

### Google Credentials

---

- `client_secret.json` is the OAuth client you download from the Google Cloud Console. One per project.
- Each service caches its own token beside that secret (`calendar_token.json`, `mail_token.json`, `keep_token.json`)
  because the scopes differ per service — they are NOT interchangeable.
- Deleting a `*_token.json` forces the browser authorization flow again. Do that whenever you change `SCOPES`,
  otherwise the cached token keeps the old (insufficient) scopes and calls fail with a 403.
