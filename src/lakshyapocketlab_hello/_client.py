"""The synchronous and asynchronous clients."""

from __future__ import annotations

import asyncio
import time
from types import TracebackType
from typing import Any, Dict, Optional, Type, Union

import httpx

from . import _core
from . import _resources_async as ra
from . import _resources_sync as rs
from . import _specs as specs
from ._core import ClientConfig, Spec
from .errors import APIConnectionError, APITimeoutError, HelloError

Timeout = Union[float, httpx.Timeout]


def sleep(seconds: float) -> None:
    """Blocking sleep used between retries (patch in tests)."""
    time.sleep(seconds)


async def asleep(seconds: float) -> None:
    """Async sleep used between retries (patch in tests)."""
    await asyncio.sleep(seconds)


def _transport_error(exc: httpx.HTTPError, spec: Spec) -> HelloError:
    target = f"{spec.method} {spec.path}"
    if isinstance(exc, httpx.TimeoutException):
        return APITimeoutError(f"Request timed out: {target}")
    return APIConnectionError(f"Connection error: {target}: {exc}")


class Hello:
    """Synchronous client for the Hello WhatsApp Business API.

    >>> from lakshyapocketlab_hello import Hello
    >>> client = Hello()  # reads HELLO_API_KEY
    >>> client.ping()
    {'status': 'ok', 'test_mode': False}
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = 30,
        max_retries: int = 2,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = ClientConfig(api_key, base_url, timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client()
        self.phone_numbers = rs.PhoneNumbers(self)
        self.messages = rs.Messages(self)
        self.media = rs.Media(self)
        self.templates = rs.Templates(self)
        self.webhook_override = rs.WebhookOverride(self)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def ping(self) -> Dict[str, Any]:
        """Check that the API key works (``GET /v1/ping``)."""
        result: Dict[str, Any] = self._request(specs.ping())
        return result

    def close(self) -> None:
        """Close the HTTP client if this instance created it."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> Hello:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def _request(self, spec: Spec) -> Any:
        cfg = self._config
        attempt = 0
        while True:
            error: HelloError
            try:
                response = self._http.request(**cfg.request_kwargs(spec))
            except httpx.HTTPError as exc:
                error = _transport_error(exc, spec)
                error.__cause__ = exc
            else:
                if response.status_code < 400:
                    return _core.decode_success(response, spec)
                error = _core.build_api_error(response)
            delay = _core.retry_delay(spec, attempt, cfg.max_retries, error)
            if delay is None:
                raise error
            sleep(delay)
            attempt += 1


class AsyncHello:
    """Asynchronous client; same surface as :class:`Hello` with ``await``."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = 30,
        max_retries: int = 2,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._config = ClientConfig(api_key, base_url, timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient()
        self.phone_numbers = ra.PhoneNumbers(self)
        self.messages = ra.Messages(self)
        self.media = ra.Media(self)
        self.templates = ra.Templates(self)
        self.webhook_override = ra.WebhookOverride(self)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    async def ping(self) -> Dict[str, Any]:
        """Check that the API key works (``GET /v1/ping``)."""
        result: Dict[str, Any] = await self._request(specs.ping())
        return result

    async def aclose(self) -> None:
        """Close the HTTP client if this instance created it."""
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncHello:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def _request(self, spec: Spec) -> Any:
        cfg = self._config
        attempt = 0
        while True:
            error: HelloError
            try:
                response = await self._http.request(**cfg.request_kwargs(spec))
            except httpx.HTTPError as exc:
                error = _transport_error(exc, spec)
                error.__cause__ = exc
            else:
                if response.status_code < 400:
                    return _core.decode_success(response, spec)
                error = _core.build_api_error(response)
            delay = _core.retry_delay(spec, attempt, cfg.max_retries, error)
            if delay is None:
                raise error
            await asleep(delay)
            attempt += 1
