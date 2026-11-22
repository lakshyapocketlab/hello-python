"""Transport-independent logic shared by the sync and async clients."""

from __future__ import annotations

import email.utils
import json
import mimetypes
import os
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import httpx

from . import errors
from ._version import __version__
from .types import FileInput

DEFAULT_BASE_URL = "https://helloapi.lakshyapocketlab.com"
ENV_API_KEY = "HELLO_API_KEY"
ENV_BASE_URL = "HELLO_BASE_URL"
USER_AGENT = f"lakshyapocketlab-hello-python/{__version__}"
IDEMPOTENCY_HEADER = "Idempotency-Key"

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
BACKOFF_BASE = 0.5
BACKOFF_MAX = 8.0
#: A server asking us to wait longer than this is not retried; the error is raised instead.
MAX_RETRY_AFTER = 60.0


@dataclass
class Spec:
    """A fully described API call, independent of sync/async transport."""

    method: str
    path: str
    params: Dict[str, Any] = field(default_factory=dict)
    json_body: Optional[Any] = None
    headers: Dict[str, str] = field(default_factory=dict)
    form: Optional[Dict[str, str]] = None
    file: Optional[Tuple[str, bytes, str]] = None
    #: Safe to repeat (GET/PUT/DELETE and idempotent POSTs, or a send with an idempotency key).
    idempotent: bool = False
    expect_bytes: bool = False


def segment(name: str, value: str) -> str:
    """URL-quote one path segment, refusing empty values that would hit a different route."""
    text = str(value)
    if not text:
        raise ValueError(f"{name} must not be empty")
    return quote(text, safe="")


def clean_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop ``None`` values and render booleans the way the API expects."""
    out: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        out[key] = "true" if value is True else "false" if value is False else value
    return out


def resolve_api_key(api_key: Optional[str]) -> str:
    key = api_key if api_key is not None else os.environ.get(ENV_API_KEY)
    if not key:
        raise errors.HelloError(
            f"No API key provided. Pass api_key=... or set the {ENV_API_KEY} environment variable."
        )
    return key


def read_file(file: FileInput, mime_type: str, filename: Optional[str]) -> Tuple[str, bytes, str]:
    """Return ``(filename, content, mime_type)`` for an upload."""
    if isinstance(file, (bytes, bytearray)):
        data = bytes(file)
        guessed: Optional[str] = None
    elif isinstance(file, (str, os.PathLike)):
        path = os.fspath(file)
        with open(path, "rb") as fh:
            data = fh.read()
        guessed = os.path.basename(path)
    else:
        data = file.read()
        name = getattr(file, "name", None)
        guessed = os.path.basename(name) if isinstance(name, str) else None
    if filename is None:
        filename = guessed or "file" + (mimetypes.guess_extension(mime_type) or "")
    return filename, data, mime_type


def backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter: 0.5s, 1s, 2s ... capped at 8s, scaled by 0.5-1.0."""
    return min(BACKOFF_BASE * float(2**attempt), BACKOFF_MAX) * random.uniform(0.5, 1.0)


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Seconds from a ``Retry-After`` header (delta-seconds or HTTP-date)."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(float(value), 0.0)
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(float(when.timestamp() - time.time()), 0.0)


def retry_delay(
    spec: Spec, attempt: int, max_retries: int, error: errors.HelloError
) -> Optional[float]:
    """Seconds to wait before retrying, or ``None`` when the error must be raised."""
    if not spec.idempotent or attempt >= max_retries:
        return None
    if isinstance(error, errors.APIError):
        if error.status not in RETRY_STATUSES:
            return None
        if error.retry_after is not None:
            return error.retry_after if error.retry_after <= MAX_RETRY_AFTER else None
    return backoff_delay(attempt)


def build_api_error(response: httpx.Response) -> errors.APIError:
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text or None
    parsed = errors.parse_error_body(body, response.reason_phrase or f"HTTP {response.status_code}")
    cls = errors.error_class(response.status_code, parsed["hello_code"])
    return cls(
        parsed["message"],
        status=response.status_code,
        code=parsed["code"],
        subcode=parsed["subcode"],
        hello_code=parsed["hello_code"],
        fbtrace_id=parsed["fbtrace_id"],
        details=parsed["details"],
        body=body,
        retry_after=parse_retry_after(response.headers.get("Retry-After")),
    )


def decode_success(response: httpx.Response, spec: Spec) -> Any:
    if spec.expect_bytes:
        return response.content
    if not response.content:
        return {}
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise errors.HelloError(
            f"Invalid JSON in {response.status_code} response from {spec.method} {spec.path}"
        ) from exc


class ClientConfig:
    """Resolved client options plus request building shared by both clients."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: Any,
        max_retries: int,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.api_key = resolve_api_key(api_key)
        self.base_url = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def request_kwargs(self, spec: Spec) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream" if spec.expect_bytes else "application/json",
            **spec.headers,
        }
        kwargs: Dict[str, Any] = {
            "method": spec.method,
            "url": self.base_url + spec.path,
            "headers": headers,
            "timeout": self.timeout,
        }
        params = clean_params(spec.params)
        if params:
            kwargs["params"] = params
        if spec.json_body is not None:
            kwargs["json"] = spec.json_body
        if spec.file is not None:
            kwargs["data"] = spec.form or {}
            kwargs["files"] = {"file": spec.file}
        return kwargs


def send_headers(idempotency_key: Optional[str]) -> Dict[str, str]:
    return {IDEMPOTENCY_HEADER: idempotency_key} if idempotency_key else {}
