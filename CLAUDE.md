# CLAUDE.md

Guidance for Claude Code when working in the GoogleAPI-Python (`gap`) repository.

## Purpose

`gap` is a typed Python wrapper around Google's API client libraries — Calendar v3,
Gmail v1 and Keep v1. It is **synchronous**; the underlying `googleapiclient` is
blocking. Callers who need async should wrap calls in `asyncio.to_thread`.

## Tooling

- **Package manager:** `uv`. Use `uv sync` / `uv pip install -r requirements.txt`.
- **Build backend:** `setuptools>=61`, dynamic version pulled from `gap.__version__`.
  Run `build.bash` — it verifies the VENV and the `__init__.py` version before tagging.
- **Type checking:** Pyright **strict**, Python 3.12, venv pinned to `./.venv`.
- **Linting:** Ruff, line length **140**. Respect the configured ignore list in
  `pyproject.toml` rather than "fixing" suppressed rules.

## Architecture

- **`gap/services.py`** — the callable surface. `GoogleService` is the base class that
  owns the OAuth2 flow (token load → refresh → local-server login → cache). Subclasses
  (`CalendarService`, `MailService`, `KeepService`) declare `service_name`,
  `service_version`, `token_name` and `SCOPES` as `ClassVar`s and add endpoint methods.
  **Never re-implement the credential dance in a subclass.**
- **`gap/modules.py`** — two distinct kinds of class, do not conflate them:
  1. **Resource shims** (`*Resource`, subclass `googleapiclient.discovery.Resource`) exist
     purely so the dynamically-built client typechecks. They have no state and their
     methods are `return super().<name>(**kwargs)  # type: ignore`.
  2. **Data models** (`Events`, `EventsList`, `MailMessage`, `KeepNote`, ...) are plain
     classes built from a JSON response. They hold the raw payload in `_raw` and expose
     attributes.
- **`gap/_types.py`** — `TypedDict` definitions mirroring the API's JSON shapes. Field
  names match Google's camelCase exactly; do not snake_case them.
- **`gap/_enums.py`** — `StrEnum`/`IntEnum` for API constant values.
- **`local.py`** — developer driver, gitignored, not shipped.

## Docstring Format

Always use NumPy-style docstrings as defined by `gap/numpy_templates/numpy_overwrite.mustache`.

- Parameters use `name: :class:`Type`` on one line, description indented below.
- Optional/keyword params append `, optional` and include `by default {{value}}`.
- Return type uses `:class:`Type`` followed by an indented description.
- Underline lengths follow the template (one character longer than the heading).

```python
def example(path: Path, value: str | None = None) -> dict[str, str]:
    """Short one-line description.

    Parameters
    -----------
    path: :class:`Path`
        Description of path.
    value: :class:`str | None`, optional
        Description of value, by default None.

    Returns
    --------
    dict[:class:`str`, :class:`str`]
        Description of return value.

    """
```

Never leave the autoDocstring `_description_` / `_type_` placeholders in committed code.

## Conventions

- Every module carries the GPL header block (see `gap/__init__.py`).
- `from __future__ import annotations` at the top of every module.
- Logging via a module-level `LOGGER: logging.Logger = logging.getLogger(__name__)`.
  **No `print()` in the package** — `local.py` is the only place that is acceptable.
- Log with `%s` lazy formatting, not f-strings.
- Raise with real formatted messages: `raise ValueError(f"...{value}")`, never
  `raise ValueError("...%s", value)` — the second form silently stores a tuple.
- `TODO.md` uses ⭐ done, 🗨 suggestion, ⚠️ issue, ⛔ deprecated/removed.
