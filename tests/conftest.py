from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator, List, Union

import httpx
import pytest
import respx

from lakshyapocketlab_hello import AsyncHello, Hello
from lakshyapocketlab_hello import _client as client_module

BASE = "https://helloapi.lakshyapocketlab.com"
Client = Union[Hello, AsyncHello]


class Runner:
    """Runs one client call identically for the sync and async client."""

    def __init__(self, client: Client) -> None:
        self.client = client

    async def __call__(self, fn: Callable[[Any], Any]) -> Any:
        result = fn(self.client)
        if inspect.isawaitable(result):
            return await result
        return result


@pytest.fixture
def mock() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    calls: List[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    async def fake_asleep(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr(client_module, "sleep", fake_sleep)
    monkeypatch.setattr(client_module, "asleep", fake_asleep)
    return calls


@pytest.fixture(params=["sync", "async"])
async def run(request: pytest.FixtureRequest, mock: respx.MockRouter) -> Any:
    kwargs: Any = {"api_key": "hello_live_test"}
    if request.param == "sync":
        sync_client = Hello(**kwargs)
        yield Runner(sync_client)
        sync_client.close()
    else:
        async_client = AsyncHello(**kwargs)
        yield Runner(async_client)
        await async_client.aclose()


@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HELLO_API_KEY", raising=False)


def ok(payload: Any = None, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload if payload is not None else {"ok": True})
