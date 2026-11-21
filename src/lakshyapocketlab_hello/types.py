"""Request typing helpers.

Every method that takes a message or template body also accepts a plain ``dict``: the API
forwards the WhatsApp Cloud API body as-is, so new Cloud API fields work without an SDK update.
These ``TypedDict`` definitions describe the common shapes for editor completion and mypy.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, BinaryIO, Dict, List, Literal, TypedDict, Union

JSON = Dict[str, Any]
"""A decoded JSON object."""

MediaType = Literal["image", "video", "audio", "document", "sticker"]

FileInput = Union[bytes, str, "os.PathLike[str]", BinaryIO]
"""Upload source: raw bytes, a path, or a binary file object."""


class _MessageBase(TypedDict):
    to: str
    type: str


class _MessageOptional(TypedDict, total=False):
    messaging_product: str
    recipient_type: str
    context: Dict[str, str]
    biz_opaque_callback_data: str


class TextBody(TypedDict, total=False):
    body: str
    preview_url: bool


class _TextMessageRequired(_MessageBase):
    text: TextBody


class TextMessage(_TextMessageRequired, _MessageOptional):
    """``{"to": "+16505551234", "type": "text", "text": {"body": "Hi"}}``"""


class TemplateLanguage(TypedDict):
    code: str


class TemplateBody(TypedDict, total=False):
    name: str
    language: TemplateLanguage
    components: List[Dict[str, Any]]


class _TemplateMessageRequired(_MessageBase):
    template: TemplateBody


class TemplateMessage(_TemplateMessageRequired, _MessageOptional):
    """A template send."""


class MediaObject(TypedDict, total=False):
    id: str
    link: str
    caption: str
    filename: str


class _MediaMessageRequired(_MessageBase):
    pass


class MediaMessage(_MediaMessageRequired, _MessageOptional, total=False):
    """An image/video/audio/document/sticker send; the media object sits under its type key."""

    image: MediaObject
    video: MediaObject
    audio: MediaObject
    document: MediaObject
    sticker: MediaObject


class InteractiveMessage(_MessageBase, total=False):
    """Interactive (buttons, list, cta_url, flow, ...) send."""

    interactive: Dict[str, Any]


class LocationMessage(_MessageBase, total=False):
    """Location send."""

    location: Dict[str, Any]


class ReactionMessage(_MessageBase, total=False):
    """Reaction send."""

    reaction: Dict[str, Any]


MessageBody = Union[
    TextMessage,
    TemplateMessage,
    MediaMessage,
    InteractiveMessage,
    LocationMessage,
    ReactionMessage,
    Mapping[str, Any],
]
"""Any WhatsApp Cloud API message body."""

TemplateDefinition = Mapping[str, Any]
"""A Meta template create/edit body (``name``, ``language``, ``category``, ``components``)."""
