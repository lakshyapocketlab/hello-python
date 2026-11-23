<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/lakshyapocketlab/.github/main/assets/hello-logo-on-dark.svg">
    <img alt="Hello" src="https://raw.githubusercontent.com/lakshyapocketlab/.github/main/assets/hello-logo.svg" height="56">
  </picture>
</p>

# Hello Python SDK for the WhatsApp Business API

Official Python SDK for Hello, the WhatsApp Business API. Send messages, templates and webhooks.

[![CI](https://github.com/lakshyapocketlab/hello-python/actions/workflows/ci.yml/badge.svg)](https://github.com/lakshyapocketlab/hello-python/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/lakshyapocketlab/hello-python/badge)](https://scorecard.dev/viewer/?uri=github.com/lakshyapocketlab/hello-python)
[![PyPI version](https://img.shields.io/pypi/v/lakshyapocketlab-hello)](https://pypi.org/project/lakshyapocketlab-hello/)
[![Python versions](https://img.shields.io/pypi/pyversions/lakshyapocketlab-hello)](https://pypi.org/project/lakshyapocketlab-hello/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A typed, sync and async client for the Hello `/v1` Integration API (a drop-in for the WhatsApp
Cloud API). Python 3.9+, one dependency (`httpx`), `py.typed`, 100% test coverage.

## Quick start

**1. Install**

```bash
pip install lakshyapocketlab-hello
```

The distribution is `lakshyapocketlab-hello`; the import package is `lakshyapocketlab_hello`.

**2. Get an API key.** Create one (`hello_live_...`) in the [Hello dashboard](https://hello.lakshyapocketlab.com) under **Integrations**, then export it:

```bash
export HELLO_API_KEY=hello_live_...
```

**3. Send your first message.** Replace `PHONE_NUMBER_ID` with your sending number's ID (see [Setup](#phone-number-id-and-waba-id)). Free-form text needs the recipient to have messaged you in the last 24 hours; otherwise send an approved template.

```python
from lakshyapocketlab_hello import Hello

with Hello() as client:  # reads HELLO_API_KEY
    sent = client.messages.send_text("PHONE_NUMBER_ID", "+16505551234", "Your order has shipped.")
    print(sent["messages"][0]["hello_id"])
```

Pass the key explicitly with `Hello(api_key="hello_live_...")` if you do not use the environment. The runnable version is [`examples/send_text.py`](examples/send_text.py).

## Setup

### Prerequisites

- Python 3.9 or newer. The SDK has one runtime dependency, `httpx`, and ships `py.typed`.

### Phone number ID and WABA ID

- `phone_number_id` identifies the sending number. Messages and media use it.
- `waba_id` (WhatsApp Business Account ID) identifies the account. Templates use it.

Both are shown for each number in the Hello dashboard. You can also read them in code:

```python
numbers = client.phone_numbers.list()["data"]
pnid = numbers[0]["phone_number_id"]  # messages.*, media.*
waba_id = numbers[0]["waba_id"]  # templates.*
```

### API key and base URL

Pass the key explicitly, or leave it out and set `HELLO_API_KEY`:

```python
client = Hello(api_key="hello_live_...")  # the argument wins
client = Hello()  # reads HELLO_API_KEY; HelloError if neither is set
```

The API host defaults to `https://helloapi.lakshyapocketlab.com`. Override it with `base_url` or the `HELLO_BASE_URL` environment variable (the argument wins over the variable). Use this for staging or a self-hosted gateway.

### Client options

```python
Hello(api_key=None, base_url=None, timeout=30, max_retries=2, http_client=None)
```

| Option | Default | Notes |
|---|---|---|
| `api_key` | env `HELLO_API_KEY` (the argument wins) | `HelloError` is raised if neither is set |
| `base_url` | env `HELLO_BASE_URL`, else `https://helloapi.lakshyapocketlab.com` | staging / self-host; the argument wins over the env var |
| `timeout` | `30` | seconds, or an `httpx.Timeout` |
| `max_retries` | `2` | see [Idempotency and retries](#idempotency-and-retries) |
| `http_client` | none | your own `httpx.Client` / `httpx.AsyncClient` (proxies, mTLS); you close it |

Requests send `Authorization: Bearer <key>` and `User-Agent: lakshyapocketlab-hello-python/<version>`. Use `with Hello() as client:` so the connection pool closes.

## Usage

All methods return the decoded JSON as a `dict`, except `media.download`, which returns `bytes`. Message and template bodies accept plain dicts or the `TypedDict`s in `lakshyapocketlab_hello.types`. The examples assume `client = Hello()` inside a `with` block.

### Send a text message

```python
sent = client.messages.send_text(pnid, "+16505551234", "Hi Asha")
print(sent["messages"][0]["hello_id"])  # follow it with messages.get
```

### Send a template

Templates are the only type that can start a conversation. Body variables (`{{1}}`, `{{2}}`) go in `components`, in order:

```python
client.messages.send_template(
    pnid,
    "+16505551234",
    "order_shipped",
    "en_US",
    components=[
        {
            "type": "body",
            "parameters": [{"type": "text", "text": "Asha"}, {"type": "text", "text": "#10432"}],
        }
    ],
)
```

### Send media (upload, then send)

Media uploaded from one number can only be sent from that number. `upload` takes a file path, bytes or a binary file object:

```python
media = client.media.upload(pnid, "invoice.pdf", "application/pdf")  # {"id": "<media_id>"}
client.messages.send_media(
    pnid, "+16505551234", "document", media_id=media["id"], filename="invoice.pdf"
)
```

Media at a public URL needs no upload: pass `link=` instead of `media_id=`. For other message types (reaction, location, interactive, ...), call `messages.send` with the raw Cloud API body.

To download inbound media:

```python
data = client.media.download(inbound_media_id)  # bytes
info = client.media.get(inbound_media_id)  # mime type, size, sha256
```

### Mark as read

```python
client.messages.mark_as_read(pnid, inbound_wamid)
client.messages.mark_as_read(pnid, inbound_wamid, typing_indicator=True)
```

### Message status

```python
msg = client.messages.get(sent["messages"][0]["hello_id"])  # Hello id or wamid
print(msg["status"])  # queued, sent, delivered, read or failed
```

### Send options

Every send accepts these keyword arguments:

| Argument | Effect |
|---|---|
| `idempotency_key` | Makes the send safe to retry. See [Idempotency and retries](#idempotency-and-retries). |
| `sync=True` | Wait up to 25 s for WhatsApp to accept; `messages[0].id` is then the wamid. |
| `async_=True` | Return at once, queued. `messages[0].hello_id` identifies the message. Wins over `sync`. |

Without `sync` or `async_`, the API key's default send mode applies.

### Async usage

`AsyncHello` has the same surface; every method is awaited:

```python
import asyncio
from lakshyapocketlab_hello import AsyncHello


async def main() -> None:
    async with AsyncHello() as client:  # reads HELLO_API_KEY
        await client.messages.send_text("PHONE_NUMBER_ID", "+16505551234", "Hi")
        page = await client.templates.list("WABA_ID", status="APPROVED")


asyncio.run(main())
```

### Templates

```python
page = client.templates.list(waba_id, status="APPROVED", limit=50)
# next page: pass page["paging"]["cursors"]["after"] as after=...

created = client.templates.create(
    waba_id,
    {
        "name": "order_shipped",
        "language": "en",
        "category": "UTILITY",
        "components": [{"type": "BODY", "text": "Order {{1}} shipped."}],
    },
)
client.templates.edit(created["id"], {"category": "UTILITY"})
client.templates.create_bulk(waba_id, [template_a, template_b])  # up to 100 create bodies
client.templates.sync(waba_id)  # re-read every template from Meta
client.templates.delete(template_id)  # one language
client.templates.delete_by_name(waba_id, "order_shipped")  # every language
```

A full paging loop is in [`examples/list_templates.py`](examples/list_templates.py).

### Phone numbers

```python
numbers = client.phone_numbers.list()  # all numbers of the key's organization
waba = client.phone_numbers.list_for_waba(waba_id)  # numbers of one WABA
```

### Direct webhook (webhook override)

This points a number's Meta webhook straight at your URL. Hello's dashboard then stops tracking that number's incoming messages and statuses, so read the Hello docs on direct mode before you enable it.

```python
client.webhook_override.set(
    pnid,
    "https://example.com/hooks/meta/9f2c4e1a7b3d",
    "a-long-token",
    acknowledge_no_tracking=True,
)
current = client.webhook_override.get(pnid, refresh=True)  # checks Meta's live setting
client.webhook_override.reapply(pnid)  # when status is "draft"
client.webhook_override.remove(pnid)
```

### Errors

Every exception extends `HelloError`. Both server error formats are parsed (Meta-style and Hello-style).

| Exception | When |
|---|---|
| `APIError` | Any non-2xx response: `status`, `message`, `code`, `subcode`, `hello_code`, `fbtrace_id`, `details`, `body`, `retry_after` |
| `AuthenticationError` | 401 |
| `NotFoundError` | 404 |
| `RateLimitError` | 429 |
| `APIConnectionError` | No response (DNS, TLS, reset) |
| `APITimeoutError` | Timeout (subclass of `APIConnectionError`) |

```python
from lakshyapocketlab_hello import APIError, RateLimitError

try:
    client.messages.send_text(pnid, to, "Hi")
except RateLimitError as e:
    print("retry in", e.retry_after)
except APIError as e:
    print(e.status, e.message, e.code, e.subcode, e.hello_code, e.fbtrace_id, e.details)
```

A complete program is in [`examples/error_handling.py`](examples/error_handling.py).

### Idempotency and retries

429, 5xx and network errors are retried `max_retries` times with exponential backoff and jitter (0.5 s, 1 s, 2 s ... capped at 8 s). A `Retry-After` header is honoured; a wait over 60 s raises instead.

- **Always retried:** `GET`, `PUT`, `DELETE`, `templates.sync`, `mark_as_read` and `webhook_override.reapply`.
- **Message sends are retried only with an `idempotency_key`.** Hello returns the original message for a repeated key, so a billed message is never sent twice. Reuse the same key for the same logical message, for example `f"order-{order_id}-shipped"`.
- **Never retried:** `media.upload`, `templates.create`, `templates.edit` and `templates.create_bulk`.

```python
client.messages.send_text(pnid, to, "Order shipped", idempotency_key=f"order-{order_id}-shipped")
```

## Examples

Runnable programs live in [`examples/`](examples). Run them with the package installed, for example `HELLO_API_KEY=hello_live_... python examples/list_templates.py <waba_id>`. Each one takes its inputs as command-line arguments.

| Example | What it shows | Arguments |
|---|---|---|
| [`send_text.py`](examples/send_text.py) | Send a text message | `<to>` |
| [`send_template.py`](examples/send_template.py) | Send an approved template with body variables and an idempotency key | `<to> <template_name>` |
| [`upload_and_send_media.py`](examples/upload_and_send_media.py) | Upload a file, then send it as a document | `<to> <path>` |
| [`error_handling.py`](examples/error_handling.py) | Branch on `AuthenticationError`, `RateLimitError`, `NotFoundError` and `APIError` | `<phone_number_id> <to> "<text>"` |
| [`list_templates.py`](examples/list_templates.py) | List approved templates across all pages | `<waba_id>` |

### More examples

The [hello-examples](https://github.com/lakshyapocketlab/hello-examples) repository has more runnable programs:

- [`message-types/python`](https://github.com/lakshyapocketlab/hello-examples/tree/main/message-types/python): one example per message type (media, location, interactive, templates, ...) with delivery tracking
- [`smoke-test/python`](https://github.com/lakshyapocketlab/hello-examples/tree/main/smoke-test/python): a live smoke test of this SDK against the real API
- [`webhooks`](https://github.com/lakshyapocketlab/hello-examples/tree/main/webhooks): receive and verify webhooks
- [`n8n`](https://github.com/lakshyapocketlab/hello-examples/tree/main/n8n): send messages from n8n workflows
- [`ai-agents`](https://github.com/lakshyapocketlab/hello-examples/tree/main/ai-agents): connect AI agents over MCP

## API reference

All methods return the decoded JSON as a `dict` (except `media.download`, which returns `bytes`).

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

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check . && .venv/bin/mypy && .venv/bin/pytest
```

## Links

- Docs: [lakshyapocketlab.com/docs](https://lakshyapocketlab.com/docs/)
- Examples: [hello-examples](https://github.com/lakshyapocketlab/hello-examples)
- MCP server: [hello-mcp](https://github.com/lakshyapocketlab/hello-mcp)
- Support: support@lakshyapocketlab.com
- [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## License

MIT, Copyright (c) 2026 Lakshya Pocket Lab.
