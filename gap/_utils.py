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

# * Google speaks camelCase; our attributes are snake_case.
#   Data models convert inbound via `to_snake_case()`, outbound via `to_camel_case()`.
#   `_types.py` TypedDicts and raw dicts (eg. `Events.start`) keep the API's camelCase.

from __future__ import annotations

import re
from functools import lru_cache

__all__ = (
    "to_camel_case",
    "to_snake_case",
)

_CAMEL_BOUNDARY: re.Pattern[str] = re.compile(r"(?<!^)(?=[A-Z])")

# * Overrides for fields that convert correctly but read badly.
#   eg. `iCalUID` → `i_cal_u_i_d` without this. Both directions derive from one entry.
_IRREGULAR_FIELDS: dict[str, str] = {"iCalUID": "ical_uid"}
_IRREGULAR_FIELDS_INVERTED: dict[str, str] = {snake: camel for camel, snake in _IRREGULAR_FIELDS.items()}


# * Field names are a small fixed set per API — cache turns conversion into a dict lookup.
#   `_IRREGULAR_FIELDS` is filled at import and never mutated, so the cache stays valid.
@lru_cache(maxsize=512)
def to_snake_case(field: str) -> str:
    """Convert one of Google's camelCase JSON keys into our attribute name.

    Parameters
    -----------
    field: :class:`str`
        The JSON key as it arrived, e.g. "nextPageToken".

    Returns
    --------
    :class:`str`
        The attribute name we store it under, e.g. "next_page_token". A key that is
        already snake_case, or a single lowercase word, comes back unchanged.

    """
    if field in _IRREGULAR_FIELDS:
        return _IRREGULAR_FIELDS[field]
    return _CAMEL_BOUNDARY.sub("_", field).lower()


# * Cached on the same terms as `to_snake_case` above.
@lru_cache(maxsize=512)
def to_camel_case(field: str) -> str:
    """Convert one of our attribute names back into Google's camelCase JSON key.

    The exact inverse of :func:`to_snake_case`, so a response can be read in and
    sent back out without losing a field.

    Parameters
    -----------
    field: :class:`str`
        The attribute name, e.g. "next_page_token".

    Returns
    --------
    :class:`str`
        The JSON key Google expects, e.g. "nextPageToken".

    """
    if field in _IRREGULAR_FIELDS_INVERTED:
        return _IRREGULAR_FIELDS_INVERTED[field]
    head, *tail = field.split("_")
    return head + "".join(part.title() for part in tail)
