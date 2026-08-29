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

# * Mail data models.

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, Union

from ._utils import to_snake_case

if TYPE_CHECKING:
    from ._enums import MailLabelColorEnum, MailLabelListVisibilityEnum, MailMessageListVisibilityEnum, MailTypeEnum

__all__ = (
    "MailDraft",
    "MailDraftList",
    "MailMessage",
    "MailMessageBody",
    "MailMessageHeader",
    "MailMessageList",
    "MailMessagePart",
    "MailUserLabel",
    "MailUserProfile",
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class MailMessageBody:
    """The body of one part of a Mail message.

    The API hands `data` back base64url encoded; we decode it on the way in.
    """

    attachment_id: str
    size: int
    data: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.data = ""
        for key, value in kwargs.items():
            if key == "data":
                # Senders are not obliged to give us valid UTF-8, and this runs during
                # `MailMessage(**payload)` construction — so an un-replaced byte takes down
                # the whole response, not just this part. `_raw["data"]` keeps the original
                # base64 for anyone who needs the bytes back.
                self.data = base64.urlsafe_b64decode(value).decode(errors="replace")
            else:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Body: {len(self.data)} chars"


class MailMessageHeader:
    """A single header on a Mail message part.

    Attributes
    -----------
    name: :class:`str`
        The header name before the `:` separator, e.g. "To".
    value: :class:`str`
        The header value after the `:` separator, e.g. "someuser@example.com".

    """

    name: str
    value: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'name', '<no name>')}: {getattr(self, 'value', '')}"


class MailMessagePart:
    """One MIME part of a Mail message; parts nest arbitrarily deep."""

    part_id: str
    mime_type: str
    headers: list[MailMessageHeader]
    body: MailMessageBody
    parts: list[MailMessagePart]
    filename: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.headers = []
        self.parts = []
        self.body = MailMessageBody()
        for key, value in kwargs.items():
            if key == "headers":
                self.headers = [MailMessageHeader(**header) for header in value]
            elif key == "body":
                self.body = MailMessageBody(**value)
            elif key == "parts":
                self.parts = [MailMessagePart(**part) for part in value]
            else:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Part: {getattr(self, 'mime_type', '<no mime_type>')} | Headers: {len(self.headers)}"


class MailMessage(EmailMessage):
    """A Mail message, doubling as the builder for one you are about to send.

    Subclasses :class:`EmailMessage` so we get MIME assembly for free — that is what
    :meth:`to_email` and :meth:`to_base64` lean on.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages

    Parameters
    -----------
    draft_id: :class:`str`, optional
        The ID of the Draft this message belongs to, by default "".
    **kwargs: :class:`Any`
        The JSON response for one message.

    """

    id: str
    draft_id: str
    thread_id: str
    label_ids: list[str]
    snippet: str
    history_id: str
    internal_date: str
    payload: MailMessagePart
    size_estimate: int
    raw: str

    def __init__(self, draft_id: str = "", **kwargs: Any) -> None:
        # Build the EmailMessage machinery up front so this object is always a
        # valid email, whether it came from a response or is being composed.
        super().__init__()
        self._raw_response: dict[str, Any] = kwargs
        self.draft_id = draft_id
        self.id = ""
        self.label_ids = []
        self.thread_id = ""
        self.raw = ""
        self.payload = MailMessagePart()
        for key, value in kwargs.items():
            if key == "payload":
                self.payload = MailMessagePart(**value)
            else:
                setattr(self, to_snake_case(key), value)

    def to_email(
        self,
        to_email: Union[str, list[str]],
        from_email: Union[str, list[str]],
        subject: str = " ",
        body: str = " ",
    ) -> MailMessage:
        """Compose this object into a sendable email, replacing any existing content.

        Parameters
        -----------
        to_email: :class:`str` | list[:class:`str`]
            The recipient address(es).
        from_email: :class:`str` | list[:class:`str`]
            The sender address(es).
        subject: :class:`str`, optional
            The subject line, by default " ".
        body: :class:`str`, optional
            The plain text body, by default " ".

        Returns
        --------
        :class:`MailMessage`
            Itself, so you can chain straight into :meth:`prepared`.

        """
        # Reset the EmailMessage — this wipes any headers/content already set.
        super().__init__()
        self.set_content(body)
        self["To"] = to_email
        self["From"] = from_email
        self["Subject"] = subject
        return self

    def to_base64(self) -> str:
        """Return this message base64url encoded, which is what the API expects."""
        return base64.urlsafe_b64encode(self.as_bytes()).decode()

    def prepared(self) -> dict[str, Any]:
        """Return the pre-formed request body wrapping the encoded message.

        Returns
        --------
        dict[:class:`str`, :class:`Any`]
            The body suitable for `drafts().create()` / `drafts().update()`.

        """
        return {"message": {"raw": self.to_base64()}}

    def update_email(self, body: str) -> MailMessage:
        """Append `body` to this message, preserving its To/From/Subject headers.

        Parameters
        -----------
        body: :class:`str`
            The text to append to the existing body.

        Returns
        --------
        :class:`MailMessage`
            Itself, recomposed with the combined body.

        """
        subject = ""
        to_email = ""
        from_email = ""
        for header in self.payload.headers:
            if header.name == "Subject":
                subject = header.value
            elif header.name == "To":
                to_email = header.value
            elif header.name == "From":
                from_email = header.value

        return self.to_email(
            to_email=to_email,
            from_email=from_email,
            subject=subject,
            body=(self.payload.body.data + body),
        )

    def __repr__(self) -> str:
        temp: list[str] = [
            "Mail Message Details:",
            f"ID: {self.id}",
            f"Labels: {self.label_ids}",
            f"Thread ID: {self.thread_id}",
            f"Content: {self.payload.body.data}",
        ]
        return "\n".join(temp)

    def __str__(self) -> str:
        """Overwrite the :class:`EmailMessage` built-in, which dumps the raw MIME."""
        return self.__repr__()


class MailDraft:
    """A Draft in the mailbox.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one Draft.

    """

    id: str
    message: MailMessage

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        # Pull `id` first — `message` needs it, and dict ordering is not a contract.
        self.id = kwargs.get("id", "")
        self.message = MailMessage(draft_id=self.id, **kwargs.get("message", {}))
        for key, value in kwargs.items():
            if key not in {"id", "message"}:
                setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"Mail Draft: {self.id} | Mail Message: {self.message}"


class MailDraftList:
    """The response of a `drafts().list()` call.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/list
    """

    drafts: list[MailDraft]
    next_page_token: Union[str, None]
    result_size_estimate: int

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.drafts = [MailDraft(**draft) for draft in kwargs.get("drafts", [])]
        self.next_page_token = kwargs.get("nextPageToken")
        self.result_size_estimate = kwargs.get("resultSizeEstimate", 0)

    def __len__(self) -> int:
        return len(self.drafts)

    def __repr__(self) -> str:
        return f"Drafts: {len(self.drafts)} | Next Page Token: {self.next_page_token}"


class MailMessageList:
    """The response of a `messages().list()` call.

    Gmail returns `id`/`threadId` stubs here, never the message itself — every other
    attribute of these :class:`MailMessage` objects is absent. Feed each `id` to
    :meth:`MailService.get_message` to fetch one in full.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
    """

    messages: list[MailMessage]
    next_page_token: Union[str, None]
    result_size_estimate: int

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        self.messages = [MailMessage(**message) for message in kwargs.get("messages", [])]
        self.next_page_token = kwargs.get("nextPageToken")
        self.result_size_estimate = kwargs.get("resultSizeEstimate", 0)

    def __len__(self) -> int:
        return len(self.messages)

    def __iter__(self) -> Any:
        return iter(self.messages)

    def __repr__(self) -> str:
        return f"Messages: {len(self.messages)} | Next Page Token: {self.next_page_token}"


class MailUserLabel:
    """A label on the Mail account.

    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels

    Parameters
    -----------
    **kwargs: :class:`Any`
        The JSON response for one label.

    """

    id: str
    name: str
    message_list_visibility: MailMessageListVisibilityEnum
    label_list_visibility: MailLabelListVisibilityEnum
    type: MailTypeEnum
    messages_total: int
    messages_unread: int
    threads_total: int
    threads_unread: int
    color: MailLabelColorEnum

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'name', '<no name>')} | {getattr(self, 'id', '<no id>')}"


class MailUserProfile:
    """The profile of the authenticated Mail account."""

    email_address: str
    messages_total: int
    threads_total: int
    history_id: str

    def __init__(self, **kwargs: Any) -> None:
        self._raw: dict[str, Any] = kwargs
        for key, value in kwargs.items():
            setattr(self, to_snake_case(key), value)

    def __repr__(self) -> str:
        return f"{getattr(self, 'email_address', '<no address>')} | Messages: {getattr(self, 'messages_total', 0)}"
