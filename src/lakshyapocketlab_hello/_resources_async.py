"""Async resources, mirroring ``_resources_sync.py`` method for method."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import _specs as specs
from .types import FileInput, MediaType, MessageBody, TemplateDefinition

if TYPE_CHECKING:
    from ._client import AsyncHello


class _Resource:
    def __init__(self, client: AsyncHello) -> None:
        self._c = client


class PhoneNumbers(_Resource):
    async def list(self) -> Dict[str, Any]:
        """List the organization's sending numbers (``GET /v1/phone_numbers``)."""
        result: Dict[str, Any] = await self._c._request(specs.phone_numbers_list())
        return result

    async def list_for_waba(self, waba_id: str) -> Dict[str, Any]:
        """List the numbers of one WhatsApp Business Account."""
        result: Dict[str, Any] = await self._c._request(specs.phone_numbers_list_for_waba(waba_id))
        return result


class Messages(_Resource):
    async def send(
        self,
        phone_number_id: str,
        message: MessageBody,
        *,
        sync: bool = False,
        async_: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send any WhatsApp Cloud API message body.

        ``sync=True`` waits up to 25 s for WhatsApp to accept the message; ``async_=True``
        returns at once (queued). Without either, the API key's default applies. Pass an
        ``idempotency_key`` to make the call safely retryable (the SDK then retries on
        429/5xx/network errors).
        """
        spec = specs.messages_send(phone_number_id, message, sync, async_, idempotency_key)
        result: Dict[str, Any] = await self._c._request(spec)
        return result

    async def send_text(
        self,
        phone_number_id: str,
        to: str,
        body: str,
        *,
        preview_url: bool = False,
        reply_to: Optional[str] = None,
        sync: bool = False,
        async_: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a text message (needs an open 24-hour window)."""
        message = specs.text_body(to, body, preview_url, reply_to)
        return await self.send(
            phone_number_id, message, sync=sync, async_=async_, idempotency_key=idempotency_key
        )

    async def send_template(
        self,
        phone_number_id: str,
        to: str,
        name: str,
        language: str = "en_US",
        components: Optional[List[Mapping[str, Any]]] = None,
        *,
        reply_to: Optional[str] = None,
        sync: bool = False,
        async_: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an approved template."""
        message = specs.template_body(to, name, language, components, reply_to)
        return await self.send(
            phone_number_id, message, sync=sync, async_=async_, idempotency_key=idempotency_key
        )

    async def send_media(
        self,
        phone_number_id: str,
        to: str,
        media_type: MediaType,
        *,
        media_id: Optional[str] = None,
        link: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        reply_to: Optional[str] = None,
        sync: bool = False,
        async_: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an image, video, audio, document or sticker by ``media_id`` or public ``link``."""
        message = specs.media_body(to, media_type, media_id, link, caption, filename, reply_to)
        return await self.send(
            phone_number_id, message, sync=sync, async_=async_, idempotency_key=idempotency_key
        )

    async def mark_as_read(
        self, phone_number_id: str, message_id: str, *, typing_indicator: bool = False
    ) -> Dict[str, Any]:
        """Mark a received message (its ``wamid``) as read."""
        result: Dict[str, Any] = await self._c._request(
            specs.mark_as_read(phone_number_id, message_id, typing_indicator)
        )
        return result

    async def get(self, message_id: str) -> Dict[str, Any]:
        """Get a sent message's status by ``hello_id`` or ``wamid`` (``GET /v1/messages/{id}``)."""
        result: Dict[str, Any] = await self._c._request(specs.messages_get(message_id))
        return result


class Media(_Resource):
    async def upload(
        self,
        phone_number_id: str,
        file: FileInput,
        mime_type: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload bytes, a file path or a binary file object. Returns ``{"id": "<media_id>"}``."""
        result: Dict[str, Any] = await self._c._request(
            specs.media_upload(phone_number_id, file, mime_type, filename)
        )
        return result

    async def get(self, media_id: str) -> Dict[str, Any]:
        """Look up a media object (``url``, ``mime_type``, ``file_size``, ...)."""
        result: Dict[str, Any] = await self._c._request(specs.media_get(media_id))
        return result

    async def download(self, media_id: str) -> bytes:
        """Download the media file's bytes."""
        result: bytes = await self._c._request(specs.media_download(media_id))
        return result


class Templates(_Resource):
    async def list(
        self,
        waba_id: str,
        *,
        name: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        summary: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List a WABA's templates, newest first. Page with ``paging.cursors.after``."""
        spec = specs.templates_list(
            waba_id,
            name=name,
            search=search,
            status=status,
            category=category,
            language=language,
            limit=limit,
            after=after,
            before=before,
            summary=summary,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result: Dict[str, Any] = await self._c._request(spec)
        return result

    async def get(self, template_id: str) -> Dict[str, Any]:
        """Get one template."""
        result: Dict[str, Any] = await self._c._request(specs.templates_get(template_id))
        return result

    async def create(self, waba_id: str, template: TemplateDefinition) -> Dict[str, Any]:
        """Submit a new template to Meta (starts PENDING)."""
        result: Dict[str, Any] = await self._c._request(specs.templates_create(waba_id, template))
        return result

    async def create_bulk(
        self, waba_id: str, templates: List[TemplateDefinition]
    ) -> Dict[str, Any]:
        """Create or edit up to 100 templates; results are per row in input order."""
        result: Dict[str, Any] = await self._c._request(
            specs.templates_create_bulk(waba_id, templates)
        )
        return result

    async def edit(self, template_id: str, changes: TemplateDefinition) -> Dict[str, Any]:
        """Edit a template (status resets to PENDING)."""
        result: Dict[str, Any] = await self._c._request(specs.templates_edit(template_id, changes))
        return result

    async def sync(self, waba_id: str) -> Dict[str, Any]:
        """Re-read every template of the WABA from Meta."""
        result: Dict[str, Any] = await self._c._request(specs.templates_sync(waba_id))
        return result

    async def delete(self, template_id: str) -> Dict[str, Any]:
        """Permanently delete one language of a template."""
        result: Dict[str, Any] = await self._c._request(specs.templates_delete(template_id))
        return result

    async def delete_by_name(self, waba_id: str, name: str) -> Dict[str, Any]:
        """Permanently delete every language of a template name."""
        result: Dict[str, Any] = await self._c._request(
            specs.templates_delete_by_name(waba_id, name)
        )
        return result


class WebhookOverride(_Resource):
    async def get(self, phone_number_id: str, *, refresh: bool = False) -> Dict[str, Any]:
        """Show a number's direct-webhook state; ``refresh=True`` checks Meta's live setting."""
        result: Dict[str, Any] = await self._c._request(specs.webhook_get(phone_number_id, refresh))
        return result

    async def set(
        self,
        phone_number_id: str,
        url: str,
        verify_token: str,
        *,
        acknowledge_no_tracking: bool,
    ) -> Dict[str, Any]:
        """Point a number's webhook at your own https URL.

        Hello then stops showing that number's incoming messages and delivery statuses, so
        ``acknowledge_no_tracking`` must be ``True`` (the API rejects it otherwise).
        """
        spec = specs.webhook_set(phone_number_id, url, verify_token, acknowledge_no_tracking)
        result: Dict[str, Any] = await self._c._request(spec)
        return result

    async def remove(self, phone_number_id: str) -> Dict[str, Any]:
        """Remove the override so Meta delivers to Hello again."""
        result: Dict[str, Any] = await self._c._request(specs.webhook_remove(phone_number_id))
        return result

    async def reapply(self, phone_number_id: str) -> Dict[str, Any]:
        """Re-apply the stored override on Meta (after status ``draft``)."""
        result: Dict[str, Any] = await self._c._request(specs.webhook_reapply(phone_number_id))
        return result
