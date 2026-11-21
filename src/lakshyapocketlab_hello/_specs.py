"""Builders that turn method arguments into :class:`Spec` objects (shared by sync and async)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from ._core import Spec, read_file, segment, send_headers
from .types import FileInput, MediaType, MessageBody, TemplateDefinition

# --- misc -------------------------------------------------------------------------------------


def ping() -> Spec:
    return Spec("GET", "/v1/ping", idempotent=True)


def phone_numbers_list() -> Spec:
    return Spec("GET", "/v1/phone_numbers", idempotent=True)


def phone_numbers_list_for_waba(waba_id: str) -> Spec:
    return Spec("GET", f"/v1/{segment('waba_id', waba_id)}/phone_numbers", idempotent=True)


# --- messages ---------------------------------------------------------------------------------


def messages_send(
    phone_number_id: str,
    message: MessageBody,
    sync: bool,
    async_: bool,
    idempotency_key: Optional[str],
) -> Spec:
    params: Dict[str, Any] = {}
    if async_:
        params["async"] = True
    elif sync:
        params["sync"] = True
    return Spec(
        "POST",
        f"/v1/{segment('phone_number_id', phone_number_id)}/messages",
        params=params,
        json_body=dict(message),
        headers=send_headers(idempotency_key),
        idempotent=bool(idempotency_key),
    )


def text_body(to: str, body: str, preview_url: bool, reply_to: Optional[str]) -> Dict[str, Any]:
    text: Dict[str, Any] = {"body": body}
    if preview_url:
        text["preview_url"] = True
    message: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": text,
    }
    if reply_to:
        message["context"] = {"message_id": reply_to}
    return message


def template_body(
    to: str,
    name: str,
    language: str,
    components: Optional[List[Mapping[str, Any]]],
    reply_to: Optional[str],
) -> Dict[str, Any]:
    template: Dict[str, Any] = {"name": name, "language": {"code": language}}
    if components:
        template["components"] = [dict(c) for c in components]
    message: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }
    if reply_to:
        message["context"] = {"message_id": reply_to}
    return message


def media_body(
    to: str,
    media_type: MediaType,
    media_id: Optional[str],
    link: Optional[str],
    caption: Optional[str],
    filename: Optional[str],
    reply_to: Optional[str],
) -> Dict[str, Any]:
    if bool(media_id) == bool(link):
        raise ValueError("Pass exactly one of media_id or link")
    media: Dict[str, Any] = {"id": media_id} if media_id else {"link": link}
    if caption:
        media["caption"] = caption
    if filename:
        media["filename"] = filename
    message: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": media_type,
        media_type: media,
    }
    if reply_to:
        message["context"] = {"message_id": reply_to}
    return message


def mark_as_read(phone_number_id: str, message_id: str, typing_indicator: bool) -> Spec:
    body: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    if typing_indicator:
        body["typing_indicator"] = {"type": "text"}
    return Spec(
        "POST",
        f"/v1/{segment('phone_number_id', phone_number_id)}/messages",
        json_body=body,
        idempotent=True,
    )


def messages_get(message_id: str) -> Spec:
    return Spec("GET", f"/v1/messages/{segment('message_id', message_id)}", idempotent=True)


# --- media ------------------------------------------------------------------------------------


def media_upload(
    phone_number_id: str, file: FileInput, mime_type: str, filename: Optional[str]
) -> Spec:
    return Spec(
        "POST",
        f"/v1/{segment('phone_number_id', phone_number_id)}/media",
        form={"messaging_product": "whatsapp", "type": mime_type},
        file=read_file(file, mime_type, filename),
    )


def media_get(media_id: str) -> Spec:
    return Spec("GET", f"/v1/{segment('media_id', media_id)}", idempotent=True)


def media_download(media_id: str) -> Spec:
    return Spec(
        "GET", f"/v1/{segment('media_id', media_id)}/download", idempotent=True, expect_bytes=True
    )


# --- templates --------------------------------------------------------------------------------


def templates_list(waba_id: str, **filters: Any) -> Spec:
    return Spec(
        "GET",
        f"/v1/{segment('waba_id', waba_id)}/message_templates",
        params=filters,
        idempotent=True,
    )


def templates_get(template_id: str) -> Spec:
    return Spec("GET", f"/v1/templates/{segment('template_id', template_id)}", idempotent=True)


def templates_create(waba_id: str, template: TemplateDefinition) -> Spec:
    return Spec(
        "POST",
        f"/v1/{segment('waba_id', waba_id)}/message_templates",
        json_body=dict(template),
    )


def templates_create_bulk(waba_id: str, templates: List[TemplateDefinition]) -> Spec:
    return Spec(
        "POST",
        f"/v1/{segment('waba_id', waba_id)}/templates/bulk",
        json_body={"templates": [dict(t) for t in templates]},
    )


def templates_edit(template_id: str, changes: TemplateDefinition) -> Spec:
    return Spec(
        "POST", f"/v1/templates/{segment('template_id', template_id)}", json_body=dict(changes)
    )


def templates_sync(waba_id: str) -> Spec:
    return Spec("POST", f"/v1/{segment('waba_id', waba_id)}/templates/sync", idempotent=True)


def templates_delete(template_id: str) -> Spec:
    return Spec("DELETE", f"/v1/templates/{segment('template_id', template_id)}", idempotent=True)


def templates_delete_by_name(waba_id: str, name: str) -> Spec:
    return Spec(
        "DELETE",
        f"/v1/{segment('waba_id', waba_id)}/message_templates",
        params={"name": name},
        idempotent=True,
    )


# --- webhook override -------------------------------------------------------------------------


def webhook_get(phone_number_id: str, refresh: bool) -> Spec:
    return Spec(
        "GET",
        f"/v1/{segment('phone_number_id', phone_number_id)}/webhook-override",
        params={"refresh": True} if refresh else {},
        idempotent=True,
    )


def webhook_set(
    phone_number_id: str, url: str, verify_token: str, acknowledge_no_tracking: bool
) -> Spec:
    return Spec(
        "PUT",
        f"/v1/{segment('phone_number_id', phone_number_id)}/webhook-override",
        json_body={
            "url": url,
            "verify_token": verify_token,
            "acknowledge_no_tracking": acknowledge_no_tracking,
        },
        idempotent=True,
    )


def webhook_remove(phone_number_id: str) -> Spec:
    return Spec(
        "DELETE",
        f"/v1/{segment('phone_number_id', phone_number_id)}/webhook-override",
        idempotent=True,
    )


def webhook_reapply(phone_number_id: str) -> Spec:
    return Spec(
        "POST",
        f"/v1/{segment('phone_number_id', phone_number_id)}/webhook-override/reapply",
        idempotent=True,
    )
