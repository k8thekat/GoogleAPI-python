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

# * Keep data models — Workspace AND consumer.
#   Workspace models speak `keep.googleapis.com` via `KeepService`.
#   Consumer models speak `notes/v1/changes` via `KeepServicePersonal` — different API entirely.

from __future__ import annotations

import logging
from collections.abc import Callable, MutableSequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, Union

from ._enums import KeepTypeEnum
from ._utils import to_snake_case

if TYPE_CHECKING:
    from ._types import NotePersonalPartsTyped
    from .services import KeepServicePersonal

__all__ = (
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

LOGGER: logging.Logger = logging.getLogger(__name__)


# * Workspace Keep models.
class KeepNoteDraft:
    """A note to be created via :meth:`gap.services.KeepService.create_note`.

    Mirrors the style of :class:`EventsDraft`; call :meth:`to_dict` to produce the
    request body the Keep API expects.

    Parameters
    -----------
    title: :class:`str`
        The note title.
    text: :class:`str` | None, optional
        Plain text body for the note. Mutually exclusive with `list_items`, by default None.
    list_items: list[tuple[:class:`str`, :class:`bool`]] | None, optional
        Checklist items as `(text, checked)` tuples. Mutually exclusive with `text`, by default None.

    Raises
    -------
    :exc:`ValueError`
        If both `text` and `list_items` are provided.

    """

    title: str
    text: Union[str, None]
    list_items: Union[list[tuple[str, bool]], None]

    def __init__(
        self,
        title: str,
        text: Union[str, None] = None,
        list_items: Union[list[tuple[str, bool]], None] = None,
    ) -> None:
        # A Keep note body is one or the other; the API has no "both" shape.
        if text is not None and list_items is not None:
            raise ValueError("A KeepNoteDraft may have `text` or `list_items`, not both.")
        self.title = title
        self.text = text
        self.list_items = list_items

    def __repr__(self) -> str:
        return f"Note Draft: {self.title}"

    def to_dict(self) -> dict[str, Any]:
        """Build the Keep API request body for this draft.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The body suitable for `notes().create()`.

        """
        body: dict[str, Any]
        if self.list_items is not None:
            body = {"list": {"listItems": [{"text": {"text": text}, "checked": checked} for text, checked in self.list_items]}}
        else:
            body = {"text": {"text": self.text or ""}}
        return {"title": self.title, "body": body}


class KeepNote:
    """A single Keep note returned by the API.

    https://developers.google.com/workspace/keep/api/reference/rest/v1/notes

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one note.

    """

    name: str  # Resource name, e.g. "notes/xxxxxxxxxxxx".
    title: str
    body: dict[str, Any]
    create_time: str
    update_time: str
    trashed: bool

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.name = ""
        self.title = ""
        self.body = {}
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    @property
    def id(self) -> str:
        """The bare note ID — the segment after `notes/` in :attr:`name`."""
        return self.name.rsplit("/", maxsplit=1)[-1]

    @property
    def text(self) -> str:
        """A best-effort plain text rendering of the note body, text or checklist."""
        if "text" in self.body:
            return self.body["text"].get("text", "")
        if "list" in self.body:
            items: list[dict[str, Any]] = self.body["list"].get("listItems", [])
            return "\n".join(f"[{'x' if item.get('checked') else ' '}] {item.get('text', {}).get('text', '')}" for item in items)
        return ""

    def __repr__(self) -> str:
        return f"{self.title or '<untitled>'} | {self.name or '<no name>'}"


class KeepNoteList:
    """The paginated response of :meth:`gap.services.KeepService.list_notes`.

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response of a `notes().list()` call.

    """

    notes: list[KeepNote]
    next_page_token: Union[str, None]

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.notes = [KeepNote(**note) for note in kwargs.get("notes", [])]
        self.next_page_token = kwargs.get("nextPageToken")

    def __len__(self) -> int:
        return len(self.notes)

    def __iter__(self) -> Any:
        return iter(self.notes)

    def __repr__(self) -> str:
        return f"Notes: {len(self.notes)} | Next Page Token: {self.next_page_token}"


# * Consumer Keep models — belong to `KeepServicePersonal`, NOT `KeepService`.
#   Wire sends a flat array related by `parentId`; checklists and entries arrive as siblings.
# ! Internal wire fields are underscored: `_kind`, `_parent_id`, `_sort_value`, etc.

# ! The wire's "this never happened" timestamp. `trashed` and `deleted` are set to this
#   when false — read as a comparison, not a null check.
KEEP_EPOCH: str = "1970-01-01T00:00:00.000Z"

_KeepChildT = TypeVar("_KeepChildT", bound="KeepBasePersonal")


class _KeepPartMeta(type):
    """Makes construction an identity map — a known id never re-enters `__init__`.

    This has to live on the metaclass rather than in `__new__`. `type.__call__` runs
    `__init__` on whatever `__new__` returns whenever it is an instance of the class, and
    for a dataclass the generated `__init__` reassigns *every* field before
    `__post_init__` can object — so returning a cached instance from `__new__` silently
    blanks it. Intercepting `__call__` is the only point at which `__init__` can be
    skipped entirely.
    """

    def __call__(cls, **kwargs: Any) -> Any:
        """Return the part already registered under this id, or build a new one.

        Raises
        -------
        :exc:`TypeError`
            If no service was supplied. Nothing outside a service constructs these.

        """
        service: Any = kwargs.get("_service")
        if service is None:
            raise TypeError(f"{cls.__name__} is not constructed directly — use the service.")

        existing: Any = service.get_part(part_id=kwargs["id"])
        if existing is not None:
            return existing
        return super().__call__(**kwargs)


def keep_now() -> str:
    """The current UTC time, in the format the consumer Keep wire uses."""
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


class KeepItemsPersonal(MutableSequence[_KeepChildT]):
    """The owning collection for a Keep object's children.

    Uses :class:`MutableSequence` instead of subclassing `list` — this guarantees
    every write path (insert, set, delete) validates and registers with the service.

    Parameters
    -----------
    owner: :class:`KeepBasePersonal`
        The object these children hang from.
    expects: type[:class:`KeepBasePersonal`]
        The only type this collection will accept.
    on_attach: Callable[[:class:`KeepBasePersonal`], None]
        Invoked as a child enters. Registers it with the service.
    on_detach: Callable[[:class:`KeepBasePersonal`], None]
        Invoked as a child leaves. Deregisters it.

    """

    def __init__(
        self,
        owner: KeepBasePersonal,
        expects: type[_KeepChildT],
        on_attach: Callable[[_KeepChildT], None],
        on_detach: Callable[[_KeepChildT], None],
    ) -> None:
        self._owner: KeepBasePersonal = owner
        self._expects: type[_KeepChildT] = expects
        self._on_attach: Callable[[_KeepChildT], None] = on_attach
        self._on_detach: Callable[[_KeepChildT], None] = on_detach
        self._children: list[_KeepChildT] = []

    def insert(self, index: int, value: _KeepChildT) -> None:
        """The single entry point for every attachment — `append` and `extend` land here."""
        self._validate(value=value)
        self._children.insert(index, value)
        self._wire_parentage(value=value)
        self._on_attach(value)

    def __getitem__(self, index: Any) -> Any:
        return self._children[index]

    def __setitem__(self, index: Any, value: Any) -> None:
        self._validate(value=value)
        self._on_detach(self._children[index])
        self._children[index] = value
        self._on_attach(value)

    def __delitem__(self, index: Any) -> None:
        """Remove an entry and mark it deleted on the wire.

        The server must be told — otherwise the entry returns on the next sync.
        """
        outgoing: _KeepChildT = self._children[index]
        del self._children[index]
        outgoing.delete()
        self._on_detach(outgoing)

    def _wire_parentage(self, value: _KeepChildT) -> None:
        """Point a child's wire id keys at this collection's owner.

        Sub entries use `superListItemId` for nesting — `parentId` always points at the checklist.
        """
        if self._expects is KeepSubItemPersonal:
            object.__setattr__(value, "_parent_id", self._owner._parent_id)  # pyright: ignore[reportPrivateUsage]
            object.__setattr__(value, "_super_list_item_id", self._owner.id)
        else:
            object.__setattr__(value, "_parent_id", self._owner.id)
            if isinstance(value, KeepItemPersonal):
                object.__setattr__(value, "_super_list_item_id", None)

        # Anything nested under the entry moves with it. Its `parentId` names the
        # checklist, so a move that only re-pointed the entry would leave its own children
        # claiming the note they came from. Delegating to their collection keeps the two
        # cases in one place and would carry through deeper nesting if Keep ever allows it.
        nested: Union[KeepItemsPersonal[KeepSubItemPersonal], None] = getattr(value, "sub_items", None)
        if nested is None:
            return
        for child in nested:
            nested._wire_parentage(value=child)

    def __len__(self) -> int:
        return len(self._children)

    def __repr__(self) -> str:
        return f"{self._expects.__name__} x{len(self._children)} | Owner: {self._owner.id}"

    def _validate(self, value: _KeepChildT) -> None:
        """Reject the wrong type, and anything already in this collection.

        Parameters
        -----------
        value: :class:`KeepBasePersonal`
            The child being attached.

        Raises
        -------
        :exc:`TypeError`
            If `value` is not an instance of the expected type.
        :exc:`ValueError`
            If `value` is already in this collection.

        """
        if isinstance(value, self._expects) is False:
            raise TypeError(f"{type(self._owner).__name__} accepts {self._expects.__name__}, got {type(value).__name__}.")
        if any(child is value for child in self._children):
            raise ValueError(f"{value.id} is already in {self._owner.id}.")


@dataclass(kw_only=True)
class KeepBasePersonal(metaclass=_KeepPartMeta):
    """What every consumer Keep object has, whatever its :class:`KeepTypeEnum`.

    Not constructed directly — :class:`_KeepPartMeta` refuses it without a service, and
    returns the already registered part when the id is known.

    Parameters
    -----------
    id: :class:`str`
        The client generated identifier. Stable for the part's whole life.
    type: :class:`KeepTypeEnum`
        Which kind of part this is.
    _service: :class:`KeepServicePersonal`
        The service this part belongs to. Required — it is how the part registers itself
        and how it queues its own edits.
    _parent_id: :class:`str`
        The owning part's id, or "root" for a top level note.
    text: :class:`str`, optional
        The body, by default "". It lives at this level because an item has text too.
    timestamps: dict[:class:`str`, :class:`str`], optional
        The wire's timestamp block, kept as sent. See :meth:`trash` and :meth:`delete`.

    """

    # ! Any field that reaches the wire must be in this set, or edits to it won't be sent.
    _TRACKED: ClassVar[frozenset[str]] = frozenset({"text", "title", "color", "pinned", "archived", "checked"})

    id: str
    type: KeepTypeEnum
    _service: KeepServicePersonal = field(repr=False, compare=False)
    # * Nullable — a detached part has no parent until re-attached.
    _parent_id: Union[str, None] = field(repr=False)
    text: str = ""
    timestamps: dict[str, str] = field(default_factory=dict)

    _kind: str = field(default="notes#node", repr=False)
    _sort_value: Union[str, None] = field(default=None, repr=False)
    _base_version: Union[str, None] = field(default=None, repr=False)
    _raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    _registered: bool = field(default=False, repr=False, compare=False)
    # * Set when any tracked attribute changes. `to_dict()` sends the whole part.
    _dirty: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Register with the service, then start tracking edits."""
        # ! `_registered` set last — prevents the generated `__init__` assignments from
        #   being mistaken for user edits and queued.
        self._service.register_part(part=self)
        self._registered = True

    @classmethod
    def from_raw(cls, raw: NotePersonalPartsTyped, service: KeepServicePersonal) -> Union[KeepBasePersonal, None]:
        """Build the right part for one payload entry, children and all.

        Parameters
        -----------
        raw: :class:`NotePersonalPartsTyped`
            One entry of the `nodes` array.
        service: :class:`KeepServicePersonal`
            The owning service. Children are found through its pending payload.

        Returns
        --------
        :class:`KeepBasePersonal` | None
            The part, or None for an attachment — we do not model blobs.

        """
        part_type: KeepTypeEnum = KeepTypeEnum(raw["type"])
        if part_type is KeepTypeEnum.blob:
            return None

        common: dict[str, Any] = {
            "id": raw["id"],
            "type": part_type,
            "_service": service,
            "_parent_id": raw.get("parentId"),
            "text": raw.get("text", ""),
            "timestamps": dict(raw.get("timestamps", {})),
            "_kind": raw.get("kind", "notes#node"),
            "_sort_value": raw.get("sortValue"),
            "_base_version": raw.get("baseVersion"),
            "_raw": dict(raw),
        }

        if part_type is KeepTypeEnum.item:
            nested: type[KeepItemPersonal] = KeepSubItemPersonal if raw.get("superListItemId") is not None else KeepItemPersonal
            return nested(
                checked=raw.get("checked", False),
                _parent_server_id=raw.get("parentServerId"),
                _super_list_item_id=raw.get("superListItemId"),
                **common,
            )

        note: type[KeepNotePersonal] = KeepChecklistPersonal if part_type is KeepTypeEnum.checklist else KeepNotePersonal
        return note(
            title=raw.get("title", ""),
            color=raw.get("color", "DEFAULT"),
            pinned=raw.get("isPinned", False),
            archived=raw.get("isArchived", False),
            label_ids=list(raw.get("labelIds", [])),
            **common,
        )

    def _new_collection(self, expects: type[_KeepChildT]) -> KeepItemsPersonal[_KeepChildT]:
        """Build a child collection wired back to this part's service."""
        return KeepItemsPersonal(
            owner=self,
            expects=expects,
            on_attach=self._service.queue_part,
            on_detach=self._service.queue_part,
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """Bump the edit timestamps and queue the part when a wire backed field changes."""
        object.__setattr__(self, name, value)
        if name in self._TRACKED and self._registered is True:
            stamped: str = keep_now()
            self.timestamps["updated"] = stamped
            self.timestamps["userEdited"] = stamped
            object.__setattr__(self, "_dirty", True)
            self._service.queue_part(part=self)

    def update(self, raw: NotePersonalPartsTyped) -> None:
        """Refresh this part's attributes from a server payload.

        Uses `object.__setattr__` — server changes are not local edits.

        Parameters
        -----------
        raw: :class:`NotePersonalPartsTyped`
            One entry of the `nodes` array.

        """
        object.__setattr__(self, "_raw", dict(raw))
        object.__setattr__(self, "_dirty", False)
        object.__setattr__(self, "text", raw.get("text", self.text))
        object.__setattr__(self, "timestamps", dict(raw.get("timestamps", self.timestamps)))
        for attribute, wire_key in (("_sort_value", "sortValue"), ("_base_version", "baseVersion"), ("_parent_id", "parentId")):
            wire_value: Any = raw.get(wire_key)
            if wire_value is not None:
                object.__setattr__(self, attribute, wire_value)

    @property
    def raw(self) -> dict[str, Any]:
        """The payload this part was last built from. Read only — returns a copy."""
        return dict(self._raw)

    @property
    def trashed(self) -> bool:
        """Whether this is in the bin. Keep purges the bin after 7 days."""
        return self.timestamps.get("trashed", KEEP_EPOCH) > KEEP_EPOCH

    @property
    def deleted(self) -> bool:
        """Whether this is marked for permanent removal."""
        return self.timestamps.get("deleted", KEEP_EPOCH) > KEEP_EPOCH

    def trash(self) -> None:
        """Send to the bin — recoverable, and what the Keep app's Delete button does."""
        self._touch(key="trashed", value=keep_now())

    def untrash(self) -> None:
        """Restore from the bin."""
        self._touch(key="trashed", value=KEEP_EPOCH)

    def delete(self) -> None:
        """Mark for permanent removal. Not the same as :meth:`trash`."""
        self._touch(key="deleted", value=keep_now())

    def undelete(self) -> None:
        """Clear the permanent removal mark."""
        self._touch(key="deleted", value=KEEP_EPOCH)

    def _touch(self, key: str, value: str) -> None:
        """Write a timestamp, bump the edit markers and queue the part.

        Bypasses `__setattr__` because it writes INTO `timestamps` rather than replacing it.
        """
        stamped: str = keep_now()
        self.timestamps[key] = value
        self.timestamps["updated"] = stamped
        self.timestamps["userEdited"] = stamped
        if self._registered is True:
            self._service.queue_part(part=self)

    def to_dict(self) -> dict[str, Any]:
        """Build the wire payload, overlaying our fields onto the payload as received.

        Overlays onto the stored payload to preserve keys we do not model.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The entry, ready to go in the `nodes` array of a `changes` request.

        """
        payload: dict[str, Any] = dict(self._raw)
        payload.update({
            "id": self.id,
            "kind": self._kind,
            "type": self.type.value,
            "parentId": self._parent_id,
            "text": self.text,
            "timestamps": self.timestamps,
        })
        # ! Omit rather than null — absence is how the server recognises an insert.
        optional: tuple[tuple[str, Union[str, None]], ...] = (
            ("sortValue", self._sort_value),
            ("baseVersion", self._base_version),
        )
        payload.update({wire_key: value for wire_key, value in optional if value is not None})
        return payload


@dataclass(kw_only=True)
class KeepNotePersonal(KeepBasePersonal):
    """A top level Keep note — an entry whose `parentId` is "root".

    Parameters
    -----------
    title: :class:`str`, optional
        The note's heading, by default "".
    color: :class:`str`, optional
        The swatch name, by default "DEFAULT".
    pinned: :class:`bool`, optional
        Whether the note sits pinned above the rest, by default False.
    archived: :class:`bool`, optional
        Whether the note is archived out of the main view, by default False.
    label_ids: list[dict[:class:`str`, :class:`str`]], optional
        The attached labels as `{"labelId": ..., "deleted": ...}` pairs.
        Removed labels keep a `deleted` timestamp tombstone — never rebuild this wholesale.

    """

    title: str = ""
    color: str = "DEFAULT"
    pinned: bool = False
    archived: bool = False
    label_ids: list[dict[str, str]] = field(default_factory=list)

    def update(self, raw: NotePersonalPartsTyped) -> None:
        """Refresh the note fields as well as the shared ones."""
        super().update(raw=raw)
        # * Cast to plain dict — pyright refuses dynamic subscript against the TypedDict union.
        data: dict[str, Any] = dict(raw)
        for attribute, wire_key in (("title", "title"), ("color", "color"), ("pinned", "isPinned"), ("archived", "isArchived")):
            if wire_key in data:
                object.__setattr__(self, attribute, data[wire_key])
        if "labelIds" in data:
            object.__setattr__(self, "label_ids", list(data["labelIds"]))

    def to_dict(self) -> dict[str, Any]:
        """Build the wire payload, adding the fields only a top level entry carries.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The entry, ready to go in the `nodes` array of a `changes` request.

        """
        payload: dict[str, Any] = super().to_dict()
        payload.update({
            "title": self.title,
            "color": self.color,
            "isPinned": self.pinned,
            "isArchived": self.archived,
            "labelIds": self.label_ids,
        })
        return payload


@dataclass(kw_only=True)
class KeepItemPersonal(KeepBasePersonal):
    """An entry belonging to a :class:`KeepChecklistPersonal`.

    Parameters
    -----------
    checked: :class:`bool`, optional
        Whether the entry is ticked, by default False.
    sub_items: :class:`KeepItemsPersonal`, optional
        Entries nested beneath this one, wired by the service. Keep supports a single
        level of nesting, so this stays empty on a :class:`KeepSubItemPersonal`.

    """

    checked: bool = False
    sub_items: KeepItemsPersonal[KeepSubItemPersonal] = field(default=None, repr=False)  # type: ignore[assignment] - wired in __post_init__.

    _parent_server_id: Union[str, None] = field(default=None, repr=False)
    _super_list_item_id: Union[str, None] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Register, wire the nested collection, then build anything nested under us.

        A nested entry's `parentId` is the *checklist*, not this item — `superListItemId`
        is the only thing that expresses the nesting.
        """
        super().__post_init__()
        self.sub_items = self._new_collection(expects=KeepSubItemPersonal)
        for raw in self._service.pending_sub_items(item_id=self.id):
            child: Union[KeepBasePersonal, None] = KeepBasePersonal.from_raw(raw=raw, service=self._service)
            if isinstance(child, KeepSubItemPersonal):
                self.sub_items.append(child)

    def update(self, raw: NotePersonalPartsTyped) -> None:
        """Refresh the entry fields as well as the shared ones."""
        super().update(raw=raw)
        data: dict[str, Any] = dict(raw)
        fields: tuple[tuple[str, str], ...] = (
            ("checked", "checked"),
            ("_parent_server_id", "parentServerId"),
            ("_super_list_item_id", "superListItemId"),
        )
        for attribute, wire_key in fields:
            if wire_key in data:
                object.__setattr__(self, attribute, data[wire_key])
        self.update_children()

    def update_children(self) -> None:
        """Cascade into anything nested under this entry, from the pending payload."""
        for child_raw in self._service.pending_sub_items(item_id=self.id):
            child: Union[KeepBasePersonal, None] = self._service.get_part(part_id=child_raw["id"])
            if child is not None:
                child.update(raw=child_raw)
                continue
            fresh: Union[KeepBasePersonal, None] = KeepBasePersonal.from_raw(raw=child_raw, service=self._service)
            if isinstance(fresh, KeepSubItemPersonal):
                self.sub_items.append(fresh)

    def to_dict(self) -> dict[str, Any]:
        """Build the wire payload, adding the fields only an entry carries.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The entry, ready to go in the `nodes` array of a `changes` request.

        """
        payload: dict[str, Any] = super().to_dict()
        payload["checked"] = self.checked
        # `superListItemId` is absent rather than null on a top level entry — its presence
        # is what marks this as nested.
        optional: tuple[tuple[str, Union[str, None]], ...] = (
            ("parentServerId", self._parent_server_id),
            ("superListItemId", self._super_list_item_id),
        )
        payload.update({wire_key: value for wire_key, value in optional if value is not None})
        return payload


@dataclass(kw_only=True)
class KeepSubItemPersonal(KeepItemPersonal):
    """An entry nested beneath a :class:`KeepItemPersonal`.

    Identical to its parent type on the wire — the only difference is that
    `superListItemId` is populated. It is its own class so the nesting is visible in the
    type rather than implied by a field being non-None.
    """


@dataclass(kw_only=True)
class KeepChecklistPersonal(KeepNotePersonal):
    """A top level note that owns entries — a `LIST` on the wire.

    A checklist is a note that owns items, so this extends :class:`KeepNotePersonal`
    rather than sitting beside it.

    Parameters
    -----------
    items: :class:`KeepItemsPersonal`, optional
        The entries, ordered by `_sort_value` and wired by the service. Attach through
        this collection, never by mutating an underlying list.

    """

    items: KeepItemsPersonal[KeepItemPersonal] = field(default=None, repr=False)  # type: ignore[assignment] - wired in __post_init__.

    def update(self, raw: NotePersonalPartsTyped) -> None:
        """Refresh this checklist, then cascade into every entry the payload carries.

        The parent already has its children, so an incoming change only has to find the
        root — each entry it owns is updated in place, and anything new is appended
        through the collection so it registers on the way in.
        """
        super().update(raw=raw)
        for child_raw in self._service.pending_children(parent_id=self.id):
            child: Union[KeepBasePersonal, None] = self._service.get_part(part_id=child_raw["id"])
            if child is not None:
                child.update(raw=child_raw)
                continue
            fresh: Union[KeepBasePersonal, None] = KeepBasePersonal.from_raw(raw=child_raw, service=self._service)
            if isinstance(fresh, KeepItemPersonal):
                self.items.append(fresh)

    def __post_init__(self) -> None:
        """Register, wire the entry collection, then build the entries that belong to us.

        Children are found by id in the service's pending payload — `parentId` says which
        checklist an entry belongs to, and that is all the wire needs to tell us. Appending
        goes through :class:`KeepItemsPersonal`, so registration and validation happen on
        the way in with nothing extra to remember.
        """
        super().__post_init__()
        self.items = self._new_collection(expects=KeepItemPersonal)
        for raw in self._service.pending_children(parent_id=self.id):
            child: Union[KeepBasePersonal, None] = KeepBasePersonal.from_raw(raw=raw, service=self._service)
            if isinstance(child, KeepItemPersonal):
                self.items.append(child)


#: Any one of the four consumer Keep parts, for callers that want to narrow on the
#: concrete type. The service's own plumbing is typed against `KeepBasePersonal` — a
#: union cannot accept `Self` from inside the base class, which is where registration
#: happens.
NotesPartTypes = Union[KeepNotePersonal, KeepChecklistPersonal, KeepItemPersonal, KeepSubItemPersonal]
