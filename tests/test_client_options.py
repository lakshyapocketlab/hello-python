"""Constructor options, environment, lifecycle."""

from __future__ import annotations

import httpx
import pytest
import respx

from lakshyapocketlab_hello import AsyncHello, Hello, HelloError, __version__

from .conftest import ok


def test_missing_api_key_raises() -> None:
    with pytest.raises(HelloError, match="HELLO_API_KEY"):
        Hello()
    with pytest.raises(HelloError):
        AsyncHello()
    with pytest.raises(HelloError):
        Hello(api_key="")


def test_negative_retries_rejected() -> None:
    with pytest.raises(ValueError):
        Hello(api_key="k", max_retries=-1)


def test_api_key_from_env_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELLO_API_KEY", "hello_live_env")
    client = Hello()
    assert client.base_url == "https://helloapi.lakshyapocketlab.com"
    with respx.mock() as router:
        route = router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(
            return_value=ok({"status": "ok"})
        )
        assert client.ping() == {"status": "ok"}
        assert route.calls.last.request.headers["authorization"] == "Bearer hello_live_env"
    client.close()


def test_api_key_passed_directly_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HELLO_API_KEY", raising=False)
    with respx.mock() as router, Hello(api_key="hello_live_direct") as client:
        route = router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(return_value=ok())
        client.ping()
        assert route.calls.last.request.headers["authorization"] == "Bearer hello_live_direct"


async def test_async_api_key_passed_directly_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HELLO_API_KEY", raising=False)
    with respx.mock() as router:
        route = router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(return_value=ok())
        async with AsyncHello(api_key="hello_live_direct") as client:
            await client.ping()
        assert route.calls.last.request.headers["authorization"] == "Bearer hello_live_direct"


def test_explicit_key_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELLO_API_KEY", "env")
    with respx.mock() as router, Hello(api_key="explicit") as client:
        route = router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(return_value=ok())
        client.ping()
        assert route.calls.last.request.headers["authorization"] == "Bearer explicit"


def test_custom_base_url_and_timeout() -> None:
    with (
        respx.mock() as router,
        Hello(
            api_key="k", base_url="https://staging.example.com/", timeout=5, max_retries=0
        ) as client,
    ):
        route = router.get("https://staging.example.com/v1/ping").mock(
            return_value=httpx.Response(503)
        )
        with pytest.raises(HelloError):
            client.ping()
        assert route.call_count == 1  # max_retries=0
        assert route.calls.last.request.extensions["timeout"]["read"] == 5


def test_custom_http_client_is_used_and_not_closed() -> None:
    http = httpx.Client()
    client = Hello(api_key="k", http_client=http)
    with respx.mock() as router:
        router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(return_value=ok())
        client.ping()
    client.close()
    assert not http.is_closed
    http.close()


async def test_async_custom_http_client_not_closed() -> None:
    http = httpx.AsyncClient()
    async with AsyncHello(api_key="k", http_client=http) as client:
        with respx.mock() as router:
            router.get("https://helloapi.lakshyapocketlab.com/v1/ping").mock(return_value=ok())
            await client.ping()
    assert not http.is_closed
    await http.aclose()


def test_owned_client_closed_on_exit() -> None:
    with Hello(api_key="k") as client:
        inner = client._http
    assert inner.is_closed


async def test_async_owned_client_closed_on_exit() -> None:
    async with AsyncHello(api_key="k") as client:
        inner = client._http
    assert inner.is_closed


def test_base_url_from_env_and_explicit_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELLO_BASE_URL", "https://staging.example.com/")
    assert Hello(api_key="k").base_url == "https://staging.example.com"
    assert AsyncHello(api_key="k").base_url == "https://staging.example.com"
    assert Hello(api_key="k", base_url="https://x.test").base_url == "https://x.test"


def test_version_exported() -> None:
    assert __version__ == "0.1.1"


def test_async_base_url_property() -> None:
    assert AsyncHello(api_key="k", base_url="https://x.test//").base_url == "https://x.test"
