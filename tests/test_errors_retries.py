"""Error envelopes, exception mapping, retries and timeouts (sync and async)."""

from __future__ import annotations

import asyncio
import email.utils
import time
from typing import Any, Dict, List, Type

import httpx
import pytest
import respx

from lakshyapocketlab_hello import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    HelloError,
    NotFoundError,
    RateLimitError,
)
from lakshyapocketlab_hello import _core as core

from .conftest import Runner, ok

PN = "106540352242922"


def meta_error(code: int = 131047, hello_code: str = "OUTSIDE_24H_WINDOW", **extra: Any) -> Any:
    return {
        "error": {
            "message": "Free-form messages need an open window",
            "type": "OAuthException",
            "code": code,
            "error_subcode": 33,
            "error_data": {
                "messaging_product": "whatsapp",
                "details": "window closed",
                "hello_code": hello_code,
                **extra,
            },
            "fbtrace_id": "trace-1",
        }
    }


async def test_meta_envelope_fields(run: Runner, mock: respx.MockRouter) -> None:
    mock.route().mock(return_value=httpx.Response(400, json=meta_error()))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.messages.send_text(PN, "+1", "x"))
    e = info.value
    assert type(e) is APIError
    assert (e.status, e.code, e.subcode) == (400, 131047, 33)
    assert e.hello_code == "OUTSIDE_24H_WINDOW"
    assert e.fbtrace_id == "trace-1"
    assert e.details == "window closed"
    assert e.message == "Free-form messages need an open window"
    assert "HTTP 400" in str(e) and "OUTSIDE_24H_WINDOW" in str(e)
    assert isinstance(e, HelloError)
    assert e.body["error"]["code"] == 131047


async def test_meta_envelope_without_details_keeps_error_data(
    run: Runner, mock: respx.MockRouter
) -> None:
    body = {"error": {"message": "m", "code": "x", "error_data": {"limit": 3}}}
    mock.route().mock(return_value=httpx.Response(400, json=body))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert info.value.details == {"limit": 3}
    assert info.value.code is None and info.value.subcode is None


async def test_meta_envelope_minimal(run: Runner, mock: respx.MockRouter) -> None:
    mock.route().mock(return_value=httpx.Response(400, json={"error": {"error_data": "bad"}}))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert info.value.message == "Bad Request"
    assert info.value.details is None


async def test_hello_envelope(run: Runner, mock: respx.MockRouter) -> None:
    body = {"message": "waba not found", "code": "NOT_FOUND", "extra": 1}
    mock.route().mock(return_value=httpx.Response(404, json=body))
    with pytest.raises(NotFoundError) as info:
        await run(lambda c: c.templates.get("1"))
    e = info.value
    assert (e.status, e.message, e.hello_code, e.code) == (404, "waba not found", "NOT_FOUND", None)
    assert e.details == {"extra": 1}


async def test_hello_envelope_numeric_code_and_string_error(
    run: Runner, mock: respx.MockRouter
) -> None:
    mock.route().mock(return_value=httpx.Response(400, json={"message": "m", "code": 7}))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert info.value.code == 7 and info.value.hello_code is None

    mock.route().mock(return_value=httpx.Response(400, json={"error": "plain", "code": True}))
    with pytest.raises(APIError) as info2:
        await run(lambda c: c.ping())
    assert info2.value.message == "plain" and info2.value.code is None


async def test_non_json_and_non_dict_bodies(run: Runner, mock: respx.MockRouter) -> None:
    mock.route().mock(return_value=httpx.Response(400, content=b"oops"))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert info.value.body == "oops" and info.value.message == "Bad Request"

    mock.route().mock(return_value=httpx.Response(400, json=["x"]))
    with pytest.raises(APIError) as info2:
        await run(lambda c: c.ping())
    assert info2.value.message == "Bad Request"

    mock.route().mock(return_value=httpx.Response(400, content=b""))
    with pytest.raises(APIError) as info3:
        await run(lambda c: c.ping())
    assert info3.value.body is None


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, meta_error(190, "UNAUTHORIZED"), AuthenticationError),
        (404, {"message": "x", "code": "NOT_FOUND"}, NotFoundError),
        (429, meta_error(4, "PLAN_DAILY_LIMIT_REACHED"), RateLimitError),
        (429, {"message": "quota", "code": "PLAN_QUOTA_EXCEEDED"}, RateLimitError),
        (409, meta_error(133010, "ACCOUNT_NOT_REGISTERED"), APIError),
        (422, {"message": "x", "code": "SEND_FAILED"}, APIError),
    ],
)
async def test_exception_classes(
    run: Runner,
    mock: respx.MockRouter,
    sleeps: List[float],
    status: int,
    body: Any,
    expected: Type[APIError],
) -> None:
    mock.route().mock(return_value=httpx.Response(status, json=body))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert type(info.value) is expected


def test_hierarchy() -> None:
    assert issubclass(APITimeoutError, APIConnectionError)
    assert issubclass(APIConnectionError, HelloError)
    assert not issubclass(APIConnectionError, APIError)
    for cls in (AuthenticationError, NotFoundError, RateLimitError):
        assert issubclass(cls, APIError)


# --- retries ----------------------------------------------------------------------------------


async def test_get_retries_5xx_then_succeeds(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    route = mock.route().mock(
        side_effect=[httpx.Response(503, json={"message": "x"}), httpx.Response(502), ok({"a": 1})]
    )
    assert await run(lambda c: c.ping()) == {"a": 1}
    assert route.call_count == 3
    assert len(sleeps) == 2
    assert 0.25 <= sleeps[0] <= 0.5 and 0.5 <= sleeps[1] <= 1.0


async def test_retries_exhausted_raises_last_error(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    route = mock.route().mock(return_value=httpx.Response(500, json={"message": "boom"}))
    with pytest.raises(APIError) as info:
        await run(lambda c: c.ping())
    assert info.value.status == 500 and route.call_count == 3 and len(sleeps) == 2


async def test_429_honours_retry_after_seconds(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    mock.route().mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "7"}, json={}), ok()]
    )
    await run(lambda c: c.ping())
    assert sleeps == [7.0]


async def test_retry_after_http_date(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    when = email.utils.formatdate(time.time() + 20, usegmt=True)
    mock.route().mock(side_effect=[httpx.Response(429, headers={"Retry-After": when}), ok()])
    await run(lambda c: c.ping())
    assert 15 <= sleeps[0] <= 21


async def test_retry_after_too_long_raises(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    mock.route().mock(return_value=httpx.Response(429, headers={"Retry-After": "3600"}))
    with pytest.raises(RateLimitError) as info:
        await run(lambda c: c.ping())
    assert info.value.retry_after == 3600.0 and sleeps == []


async def test_garbage_retry_after_falls_back_to_backoff(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    mock.route().mock(side_effect=[httpx.Response(503, headers={"Retry-After": "soon"}), ok()])
    await run(lambda c: c.ping())
    assert len(sleeps) == 1 and sleeps[0] <= 0.5


async def test_4xx_not_retried(run: Runner, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.route().mock(return_value=httpx.Response(400, json={"message": "bad"}))
    with pytest.raises(APIError):
        await run(lambda c: c.ping())
    assert route.call_count == 1 and sleeps == []


async def test_plain_send_never_retried(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    route = mock.route().mock(return_value=httpx.Response(503))
    with pytest.raises(APIError):
        await run(lambda c: c.messages.send_text(PN, "+1", "x"))
    assert route.call_count == 1 and sleeps == []


async def test_send_with_idempotency_key_retried(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    route = mock.route().mock(side_effect=[httpx.Response(503), ok({"sent": 1})])
    out = await run(lambda c: c.messages.send_text(PN, "+1", "x", idempotency_key="k"))
    assert out == {"sent": 1} and route.call_count == 2
    assert all(c.request.headers["idempotency-key"] == "k" for c in route.calls)


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.templates.create("1", {"name": "t"}),
        lambda c: c.templates.edit("1", {"a": 1}),
        lambda c: c.media.upload("1", b"x", "image/png"),
    ],
)
async def test_non_idempotent_posts_not_retried(
    run: Runner, mock: respx.MockRouter, sleeps: List[float], call: Any
) -> None:
    route = mock.route().mock(return_value=httpx.Response(500))
    with pytest.raises(APIError):
        await run(call)
    assert route.call_count == 1


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.messages.mark_as_read("1", "w"),
        lambda c: c.templates.sync("1"),
        lambda c: c.webhook_override.reapply("1"),
        lambda c: c.webhook_override.set("1", "https://x", "tok", acknowledge_no_tracking=True),
        lambda c: c.templates.delete("1"),
        lambda c: c.media.download("1"),
    ],
)
async def test_idempotent_calls_retried(
    run: Runner, mock: respx.MockRouter, sleeps: List[float], call: Any
) -> None:
    route = mock.route().mock(side_effect=[httpx.Response(500), ok()])
    await run(call)
    assert route.call_count == 2


async def test_multipart_upload_rebuilt_not_reused(run: Runner, mock: respx.MockRouter) -> None:
    mock.route().mock(return_value=httpx.Response(500))
    with pytest.raises(APIError):
        await run(lambda c: c.media.upload("1", b"x", "image/png"))


# --- transport errors -------------------------------------------------------------------------


async def test_timeout_maps_to_api_timeout_error(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    route = mock.route().mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError) as info:
        await run(lambda c: c.ping())
    assert route.call_count == 3 and len(sleeps) == 2
    assert isinstance(info.value.__cause__, httpx.ReadTimeout)


async def test_connection_error_retried_then_succeeds(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    mock.route().mock(side_effect=[httpx.ConnectError("refused"), ok({"a": 2})])
    assert await run(lambda c: c.ping()) == {"a": 2}


async def test_connection_error_on_send_not_retried(
    run: Runner, mock: respx.MockRouter, sleeps: List[float]
) -> None:
    mock.route().mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(APIConnectionError) as info:
        await run(lambda c: c.messages.send_text(PN, "+1", "x"))
    assert not isinstance(info.value, APITimeoutError) and "refused" in str(info.value)


def test_backoff_is_capped() -> None:
    assert core.backoff_delay(10) <= core.BACKOFF_MAX
    assert core.parse_retry_after(None) is None
    assert core.parse_retry_after("-5") == 0.0


def test_default_sleep_functions_are_real(monkeypatch: pytest.MonkeyPatch) -> None:
    from lakshyapocketlab_hello import _client

    seen: Dict[str, float] = {}
    monkeypatch.setattr(time, "sleep", lambda s: seen.setdefault("s", s))
    _client.sleep(0.25)
    assert seen == {"s": 0.25}


async def test_default_async_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    from lakshyapocketlab_hello import _client

    seen: Dict[str, float] = {}

    async def fake(s: float) -> None:
        seen["s"] = s

    monkeypatch.setattr(asyncio, "sleep", fake)
    await _client.asleep(0.5)
    assert seen == {"s": 0.5}


def test_str_without_hello_code() -> None:
    assert str(APIError("nope", status=500)) == "nope (HTTP 500)"
