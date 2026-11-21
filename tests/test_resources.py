"""Every method, sync and async: method, path, query, headers, body."""

from __future__ import annotations

import io
import json
from typing import Any, Dict

import httpx
import pytest
import respx

from lakshyapocketlab_hello import __version__

from .conftest import BASE, Runner, ok

PN = "106540352242922"
WABA = "102290129340398"

Case = Dict[str, Any]


def body_of(req: httpx.Request) -> Any:
    return json.loads(req.content)


CASES: Dict[str, Case] = {
    "ping": dict(call=lambda c: c.ping(), method="GET", path="/v1/ping"),
    "phone_numbers.list": dict(
        call=lambda c: c.phone_numbers.list(), method="GET", path="/v1/phone_numbers"
    ),
    "phone_numbers.list_for_waba": dict(
        call=lambda c: c.phone_numbers.list_for_waba(WABA),
        method="GET",
        path=f"/v1/{WABA}/phone_numbers",
    ),
    "messages.send_raw": dict(
        call=lambda c: c.messages.send(PN, {"to": "+1", "type": "text", "text": {"body": "x"}}),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={"to": "+1", "type": "text", "text": {"body": "x"}},
        query="",
    ),
    "messages.send_sync": dict(
        call=lambda c: c.messages.send(PN, {"to": "+1"}, sync=True),
        method="POST",
        path=f"/v1/{PN}/messages",
        query="sync=true",
    ),
    "messages.send_async_wins": dict(
        call=lambda c: c.messages.send(PN, {"to": "+1"}, sync=True, async_=True),
        method="POST",
        path=f"/v1/{PN}/messages",
        query="async=true",
    ),
    "messages.send_text": dict(
        call=lambda c: c.messages.send_text(PN, "+1", "Hi", preview_url=True, reply_to="wamid.A"),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "+1",
            "type": "text",
            "text": {"body": "Hi", "preview_url": True},
            "context": {"message_id": "wamid.A"},
        },
    ),
    "messages.send_text_plain": dict(
        call=lambda c: c.messages.send_text(PN, "+1", "Hi", idempotency_key="k1"),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "+1",
            "type": "text",
            "text": {"body": "Hi"},
        },
        headers={"idempotency-key": "k1"},
    ),
    "messages.send_template": dict(
        call=lambda c: c.messages.send_template(
            PN, "+1", "promo", "en", [{"type": "body"}], reply_to="wamid.B", async_=True
        ),
        method="POST",
        path=f"/v1/{PN}/messages",
        query="async=true",
        body={
            "messaging_product": "whatsapp",
            "to": "+1",
            "type": "template",
            "template": {
                "name": "promo",
                "language": {"code": "en"},
                "components": [{"type": "body"}],
            },
            "context": {"message_id": "wamid.B"},
        },
    ),
    "messages.send_template_default": dict(
        call=lambda c: c.messages.send_template(PN, "+1", "promo"),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "to": "+1",
            "type": "template",
            "template": {"name": "promo", "language": {"code": "en_US"}},
        },
    ),
    "messages.send_media_id": dict(
        call=lambda c: c.messages.send_media(
            PN, "+1", "document", media_id="m1", caption="c", filename="a.pdf", reply_to="w"
        ),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "to": "+1",
            "type": "document",
            "document": {"id": "m1", "caption": "c", "filename": "a.pdf"},
            "context": {"message_id": "w"},
        },
    ),
    "messages.send_media_link": dict(
        call=lambda c: c.messages.send_media(PN, "+1", "image", link="https://x/y.jpg"),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "to": "+1",
            "type": "image",
            "image": {"link": "https://x/y.jpg"},
        },
    ),
    "messages.mark_as_read": dict(
        call=lambda c: c.messages.mark_as_read(PN, "wamid.X", typing_indicator=True),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": "wamid.X",
            "typing_indicator": {"type": "text"},
        },
    ),
    "messages.mark_as_read_plain": dict(
        call=lambda c: c.messages.mark_as_read(PN, "wamid.X"),
        method="POST",
        path=f"/v1/{PN}/messages",
        body={"messaging_product": "whatsapp", "status": "read", "message_id": "wamid.X"},
    ),
    "messages.get": dict(
        call=lambda c: c.messages.get("wamid.a/b=="),
        method="GET",
        path="/v1/messages/wamid.a%2Fb%3D%3D",
    ),
    "media.get": dict(call=lambda c: c.media.get("99"), method="GET", path="/v1/99"),
    "templates.list": dict(
        call=lambda c: c.templates.list(
            WABA,
            name="n",
            search="s",
            status="APPROVED",
            category="UTILITY",
            language="en_US",
            limit=5,
            after="a",
            before="b",
            summary="total_count",
            sort_by="name",
            sort_order="asc",
        ),
        method="GET",
        path=f"/v1/{WABA}/message_templates",
        query=(
            "name=n&search=s&status=APPROVED&category=UTILITY&language=en_US&limit=5"
            "&after=a&before=b&summary=total_count&sort_by=name&sort_order=asc"
        ),
    ),
    "templates.list_bare": dict(
        call=lambda c: c.templates.list(WABA),
        method="GET",
        path=f"/v1/{WABA}/message_templates",
        query="",
    ),
    "templates.get": dict(
        call=lambda c: c.templates.get("55"), method="GET", path="/v1/templates/55"
    ),
    "templates.create": dict(
        call=lambda c: c.templates.create(WABA, {"name": "t"}),
        method="POST",
        path=f"/v1/{WABA}/message_templates",
        body={"name": "t"},
    ),
    "templates.create_bulk": dict(
        call=lambda c: c.templates.create_bulk(WABA, [{"name": "a"}, {"name": "b"}]),
        method="POST",
        path=f"/v1/{WABA}/templates/bulk",
        body={"templates": [{"name": "a"}, {"name": "b"}]},
    ),
    "templates.edit": dict(
        call=lambda c: c.templates.edit("55", {"category": "UTILITY"}),
        method="POST",
        path="/v1/templates/55",
        body={"category": "UTILITY"},
    ),
    "templates.sync": dict(
        call=lambda c: c.templates.sync(WABA), method="POST", path=f"/v1/{WABA}/templates/sync"
    ),
    "templates.delete": dict(
        call=lambda c: c.templates.delete("55"), method="DELETE", path="/v1/templates/55"
    ),
    "templates.delete_by_name": dict(
        call=lambda c: c.templates.delete_by_name(WABA, "my tpl"),
        method="DELETE",
        path=f"/v1/{WABA}/message_templates",
        query="name=my+tpl",
    ),
    "webhook.get": dict(
        call=lambda c: c.webhook_override.get(PN),
        method="GET",
        path=f"/v1/{PN}/webhook-override",
        query="",
    ),
    "webhook.get_refresh": dict(
        call=lambda c: c.webhook_override.get(PN, refresh=True),
        method="GET",
        path=f"/v1/{PN}/webhook-override",
        query="refresh=true",
    ),
    "webhook.set": dict(
        call=lambda c: c.webhook_override.set(
            PN, "https://e.com/h", "tok-12345", acknowledge_no_tracking=True
        ),
        method="PUT",
        path=f"/v1/{PN}/webhook-override",
        body={
            "url": "https://e.com/h",
            "verify_token": "tok-12345",
            "acknowledge_no_tracking": True,
        },
    ),
    "webhook.remove": dict(
        call=lambda c: c.webhook_override.remove(PN),
        method="DELETE",
        path=f"/v1/{PN}/webhook-override",
    ),
    "webhook.reapply": dict(
        call=lambda c: c.webhook_override.reapply(PN),
        method="POST",
        path=f"/v1/{PN}/webhook-override/reapply",
    ),
}


@pytest.mark.parametrize("case", CASES.values(), ids=CASES.keys())
async def test_request_shape(run: Runner, mock: respx.MockRouter, case: Case) -> None:
    route = mock.route().mock(return_value=ok({"hello": "world"}))
    result = await run(case["call"])
    assert result == {"hello": "world"}
    req = route.calls.last.request
    assert req.method == case["method"]
    assert req.url.raw_path.split(b"?")[0].decode() == case["path"]
    if "query" in case:
        assert req.url.query.decode() == case["query"]
    assert req.headers["authorization"] == "Bearer hello_live_test"
    assert req.headers["user-agent"] == f"lakshyapocketlab-hello-python/{__version__}"
    assert req.headers["accept"] == "application/json"
    for name, value in case.get("headers", {}).items():
        assert req.headers[name] == value
    if "body" in case:
        assert body_of(req) == case["body"]
        assert req.headers["content-type"] == "application/json"
    elif case["method"] in ("GET", "DELETE"):
        assert req.content == b""
    assert str(req.url).startswith(BASE)


async def test_send_without_idempotency_key_has_no_header(
    run: Runner, mock: respx.MockRouter
) -> None:
    route = mock.route().mock(return_value=ok())
    await run(lambda c: c.messages.send(PN, {"to": "+1"}))
    assert "idempotency-key" not in route.calls.last.request.headers


async def test_send_media_requires_exactly_one_source(run: Runner) -> None:
    with pytest.raises(ValueError):
        await run(lambda c: c.messages.send_media(PN, "+1", "image"))
    with pytest.raises(ValueError):
        await run(lambda c: c.messages.send_media(PN, "+1", "image", media_id="a", link="b"))


async def test_empty_path_param_rejected(run: Runner) -> None:
    with pytest.raises(ValueError, match="phone_number_id"):
        await run(lambda c: c.messages.send("", {"to": "1"}))


async def test_path_params_are_quoted(run: Runner, mock: respx.MockRouter) -> None:
    route = mock.route().mock(return_value=ok())
    await run(lambda c: c.templates.get("../admin?x=1"))
    assert route.calls.last.request.url.raw_path == b"/v1/templates/..%2Fadmin%3Fx%3D1"


# --- media ------------------------------------------------------------------------------------


def multipart(req: httpx.Request) -> str:
    return req.content.decode("latin-1")


async def test_media_upload_bytes(run: Runner, mock: respx.MockRouter) -> None:
    route = mock.route().mock(return_value=ok({"id": "m1"}))
    out = await run(lambda c: c.media.upload(PN, b"%PDF-1", "application/pdf", "inv.pdf"))
    assert out == {"id": "m1"}
    req = route.calls.last.request
    assert req.method == "POST" and req.url.path == f"/v1/{PN}/media"
    assert req.headers["content-type"].startswith("multipart/form-data; boundary=")
    text = multipart(req)
    assert 'name="messaging_product"' in text and "whatsapp" in text
    assert 'name="type"' in text and "application/pdf" in text
    assert 'name="file"; filename="inv.pdf"' in text
    assert "%PDF-1" in text


async def test_media_upload_bytes_default_filename(run: Runner, mock: respx.MockRouter) -> None:
    route = mock.route().mock(return_value=ok({"id": "m1"}))
    await run(lambda c: c.media.upload(PN, b"x", "image/png"))
    assert 'filename="file.png"' in multipart(route.calls.last.request)


async def test_media_upload_unknown_mime_default_filename(
    run: Runner, mock: respx.MockRouter
) -> None:
    route = mock.route().mock(return_value=ok({"id": "m1"}))
    await run(lambda c: c.media.upload(PN, b"x", "application/x-unknown-thing"))
    assert 'filename="file"' in multipart(route.calls.last.request)


async def test_media_upload_path(run: Runner, mock: respx.MockRouter, tmp_path: Any) -> None:
    route = mock.route().mock(return_value=ok({"id": "m1"}))
    path = tmp_path / "report.pdf"
    path.write_bytes(b"PDFDATA")
    await run(lambda c: c.media.upload(PN, str(path), "application/pdf"))
    text = multipart(route.calls.last.request)
    assert 'filename="report.pdf"' in text and "PDFDATA" in text
    await run(lambda c: c.media.upload(PN, path, "application/pdf", "other.pdf"))
    assert 'filename="other.pdf"' in multipart(route.calls.last.request)


async def test_media_upload_file_object(run: Runner, mock: respx.MockRouter, tmp_path: Any) -> None:
    route = mock.route().mock(return_value=ok({"id": "m1"}))
    path = tmp_path / "pic.jpg"
    path.write_bytes(b"JPEG")
    with open(path, "rb") as fh:
        await run(lambda c: c.media.upload(PN, fh, "image/jpeg"))
    assert 'filename="pic.jpg"' in multipart(route.calls.last.request)
    await run(lambda c: c.media.upload(PN, io.BytesIO(b"abc"), "image/jpeg"))
    assert 'filename="file.jpg"' in multipart(route.calls.last.request)


async def test_media_download(run: Runner, mock: respx.MockRouter) -> None:
    route = mock.route().mock(return_value=httpx.Response(200, content=b"\x00\x01binary"))
    data = await run(lambda c: c.media.download("99"))
    assert data == b"\x00\x01binary"
    req = route.calls.last.request
    assert req.url.path == "/v1/99/download"
    assert req.headers["accept"] == "application/octet-stream"


async def test_empty_success_body_is_empty_dict(run: Runner, mock: respx.MockRouter) -> None:
    mock.route().mock(return_value=httpx.Response(204))
    assert await run(lambda c: c.templates.delete("5")) == {}


async def test_invalid_json_success_raises(run: Runner, mock: respx.MockRouter) -> None:
    from lakshyapocketlab_hello import HelloError

    mock.route().mock(return_value=httpx.Response(200, content=b"<html>"))
    with pytest.raises(HelloError, match="Invalid JSON"):
        await run(lambda c: c.ping())
