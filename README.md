# Hello Python SDK for the WhatsApp Business API

Official Python SDK for Hello, the WhatsApp Business API. Send messages, templates and webhooks.

[![CI](https://github.com/lakshyapocketlab/hello-python/actions/workflows/ci.yml/badge.svg)](https://github.com/lakshyapocketlab/hello-python/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/lakshyapocketlab/hello-python/badge)](https://scorecard.dev/viewer/?uri=github.com/lakshyapocketlab/hello-python)
[![PyPI version](https://img.shields.io/pypi/v/lakshyapocketlab-hello)](https://pypi.org/project/lakshyapocketlab-hello/)
[![Python versions](https://img.shields.io/pypi/pyversions/lakshyapocketlab-hello)](https://pypi.org/project/lakshyapocketlab-hello/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A typed, sync and async client for the Hello `/v1` Integration API (a drop-in for the WhatsApp
Cloud API). Python 3.9+, one dependency (`httpx`), `py.typed`, 100% test coverage.

## Install

```bash
pip install lakshyapocketlab-hello
```

The distribution is `lakshyapocketlab-hello`; the import package is `lakshyapocketlab_hello`.

## Quickstart

Create an API key (`hello_live_...`) in the Hello dashboard and pass it directly:

```python
from lakshyapocketlab_hello import Hello

with Hello(api_key="hello_live_xxxxxxxx") as client:
    number = client.phone_numbers.list()["data"][0]
    sent = client.messages.send_text(
        number["phone_number_id"], "+919999999999", "Hello from Python!"
    )
    print(sent["messages"][0]["hello_id"])
```

Or omit `api_key` and export `HELLO_API_KEY` instead (`Hello()` and `AsyncHello()` read it):

```bash
export HELLO_API_KEY=hello_live_xxxxxxxx
```

Async:

```python
import asyncio
from lakshyapocketlab_hello import AsyncHello


async def main() -> None:
    async with AsyncHello(api_key="hello_live_xxxxxxxx") as client:
        await client.ping()
        await client.messages.send_template(
            "106540352242922",
            "+919999999999",
            "order_shipped",
            "en",
            components=[{"type": "body", "parameters": [{"type": "text", "text": "Asha"}]}],
        )


asyncio.run(main())
```

## Client options

```python
Hello(api_key=None, base_url=None, timeout=30, max_retries=2, http_client=None)
```

| Option | Default | Notes |
|---|---|---|
| `api_key` | env `HELLO_API_KEY` (the argument wins) | `HelloError` is raised if neither is set |
| `base_url` | env `HELLO_BASE_URL`, else `https://helloapi.lakshyapocketlab.com` | staging / self-host; the argument wins over the env var |
| `timeout` | `30` | seconds, or an `httpx.Timeout` |
| `max_retries` | `2` | see [Retries](#retries) |
| `http_client` | none | your own `httpx.Client` / `httpx.AsyncClient` (proxies, mTLS); you close it |

Requests send `Authorization: Bearer <key>` and `User-Agent: lakshyapocketlab-hello-python/<version>`.
`AsyncHello` has the identical surface; every method is awaited.

## Methods

All methods return the decoded JSON as a `dict` (except `media.download`, which returns `bytes`).
Message and template bodies accept plain dicts or the `TypedDict`s in `lakshyapocketlab_hello.types`.

| Method | Route |
|---|---|
| `client.ping()` | `GET /v1/ping` |
| `client.phone_numbers.list()` | `GET /v1/phone_numbers` |
| `client.phone_numbers.list_for_waba(waba_id)` | `GET /v1/{waba_id}/phone_numbers` |
| `client.messages.send(phone_number_id, message, *, sync, async_, idempotency_key)` | `POST /v1/{phone_number_id}/messages` |
| `client.messages.send_text(pnid, to, body, *, preview_url, reply_to, ...)` | same |
| `client.messages.send_template(pnid, to, name, language="en_US", components=None, ...)` | same |
| `client.messages.send_media(pnid, to, "image", media_id=... or link=..., caption, filename, ...)` | same |
| `client.messages.mark_as_read(pnid, message_id, *, typing_indicator)` | same, `status: read` |
| `client.messages.get(message_id)` | `GET /v1/messages/{id}` |
| `client.media.upload(pnid, file, mime_type, filename=None)` | `POST /v1/{pnid}/media` |
| `client.media.get(media_id)` | `GET /v1/{media_id}` |
| `client.media.download(media_id)` | `GET /v1/{media_id}/download` |
| `client.templates.list(waba_id, *, name, search, status, category, language, limit, after, before, summary, sort_by, sort_order)` | `GET /v1/{waba_id}/message_templates` |
| `client.templates.get(template_id)` | `GET /v1/templates/{id}` |
| `client.templates.create(waba_id, template)` | `POST /v1/{waba_id}/message_templates` |
| `client.templates.create_bulk(waba_id, templates)` | `POST /v1/{waba_id}/templates/bulk` |
| `client.templates.edit(template_id, changes)` | `POST /v1/templates/{id}` |
| `client.templates.sync(waba_id)` | `POST /v1/{waba_id}/templates/sync` |
| `client.templates.delete(template_id)` | `DELETE /v1/templates/{id}` |
| `client.templates.delete_by_name(waba_id, name)` | `DELETE /v1/{waba_id}/message_templates?name=` |
| `client.webhook_override.get(pnid, *, refresh=False)` | `GET /v1/{pnid}/webhook-override` |
| `client.webhook_override.set(pnid, url, verify_token, *, acknowledge_no_tracking)` | `PUT /v1/{pnid}/webhook-override` |
| `client.webhook_override.remove(pnid)` | `DELETE /v1/{pnid}/webhook-override` |
| `client.webhook_override.reapply(pnid)` | `POST /v1/{pnid}/webhook-override/reapply` |

### Sending

```python
# Raw Cloud API body: any message type
client.messages.send(pnid, {"to": "+16505551234", "type": "text", "text": {"body": "Hi"}})

# Wait up to 25 s for WhatsApp to accept (messages[0].id is the wamid), or return queued:
client.messages.send_text(pnid, to, "Hi", sync=True)
client.messages.send_text(pnid, to, "Hi", async_=True)

# Safe retries: the same key returns the original message instead of sending again
client.messages.send_template(pnid, to, "promo", "en", idempotency_key="order-1042")
```

Free-form types need an open 24-hour window; otherwise send an approved template.
`to` must include the `+` and country code.

### Media

```python
media = client.media.upload(pnid, "invoice.pdf", "application/pdf")  # path
media = client.media.upload(pnid, pdf_bytes, "application/pdf", "invoice.pdf")  # bytes
with open("photo.jpg", "rb") as fh:  # file object
    media = client.media.upload(pnid, fh, "image/jpeg")
client.messages.send_media(pnid, to, "document", media_id=media["id"], filename="invoice.pdf")

data = client.media.download(inbound_media_id)  # bytes
```

### Templates and direct webhooks

```python
client.templates.list(waba_id, status="APPROVED", limit=50)
client.templates.create(
    waba_id,
    {
        "name": "order_shipped",
        "language": "en",
        "category": "UTILITY",
        "components": [{"type": "BODY", "text": "Order {{1}} shipped."}],
    },
)
client.webhook_override.set(
    pnid, "https://example.com/hooks/meta/9f2c4e1a", "my-verify-token", acknowledge_no_tracking=True
)
```

`webhook_override.set` stops Hello from showing that number's incoming messages and delivery
statuses; read the Hello docs before enabling it.

## Errors

```python
from lakshyapocketlab_hello import APIError, RateLimitError, HelloError

try:
    client.messages.send_text(pnid, to, "Hi")
except RateLimitError as e:
    print("retry in", e.retry_after)
except APIError as e:
    print(e.status, e.message, e.code, e.subcode, e.hello_code, e.fbtrace_id, e.details)
```

| Exception | When |
|---|---|
| `HelloError` | base class of everything below; also missing API key |
| `APIError` | any non-2xx: `status`, `message`, `code`, `subcode`, `hello_code`, `fbtrace_id`, `details`, `body`, `retry_after` |
| `AuthenticationError` | 401 |
| `NotFoundError` | 404 |
| `RateLimitError` | 429 |
| `APIConnectionError` | no response (DNS, TLS, reset) |
| `APITimeoutError` | timeout (subclass of `APIConnectionError`) |

Both error envelopes are parsed: Meta-style `{"error": {message, code, error_subcode,
error_data: {details, hello_code}, fbtrace_id}}` on send/media routes, and Hello's `{message, code}`
elsewhere (where `code` becomes `hello_code`).

## Retries

429, 5xx and network errors are retried `max_retries` times with exponential backoff and jitter
(0.5 s, 1 s, 2 s ... capped at 8 s), honouring `Retry-After` (a wait over 60 s raises instead).
Retried calls: GET, PUT, DELETE, `templates.sync`, `mark_as_read`, `webhook_override.reapply`, and
`messages.send*` **only when you pass `idempotency_key`**. Plain sends, template create/edit and
media upload are never retried automatically, so a billed message is never sent twice by accident.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check . && .venv/bin/mypy && .venv/bin/pytest
```

## License

MIT, Copyright (c) 2026 Lakshya Pocket Lab.
