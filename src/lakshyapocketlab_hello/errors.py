"""Exception hierarchy.

``HelloError`` is the root. ``APIError`` is raised for any non-2xx response and carries the
fields of both error envelopes the API uses:

* Meta-style (send and media routes)::

      {"error": {"message", "type", "code", "error_subcode",
                 "error_data": {"details", "hello_code", ...}, "fbtrace_id"}}

* Hello-style (every other route): ``{"message", "code"}`` where ``code`` is Hello's own
  string code (for example ``VALIDATION_ERROR``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class HelloError(Exception):
    """Base class for every error raised by this SDK."""


class APIConnectionError(HelloError):
    """The request never produced an HTTP response (DNS, TLS, connection reset, ...)."""


class APITimeoutError(APIConnectionError):
    """The request timed out."""


class APIError(HelloError):
    """The API answered with a non-2xx status."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: Optional[int] = None,
        subcode: Optional[int] = None,
        hello_code: Optional[str] = None,
        fbtrace_id: Optional[str] = None,
        details: Any = None,
        body: Any = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.subcode = subcode
        self.hello_code = hello_code
        self.fbtrace_id = fbtrace_id
        self.details = details
        self.body = body
        self.retry_after = retry_after

    def __str__(self) -> str:
        parts = [f"HTTP {self.status}"]
        if self.hello_code:
            parts.append(self.hello_code)
        return f"{self.message} ({', '.join(parts)})"


class AuthenticationError(APIError):
    """401: the API key is missing, wrong or disabled."""


class NotFoundError(APIError):
    """404: the resource does not exist in your organization."""


class RateLimitError(APIError):
    """429: too many requests, or a plan limit was reached. See ``retry_after``."""


def parse_error_body(body: Any, status_text: str) -> Dict[str, Any]:
    """Normalise either error envelope into ``APIError`` keyword arguments."""
    out: Dict[str, Any] = {
        "message": status_text,
        "code": None,
        "subcode": None,
        "hello_code": None,
        "fbtrace_id": None,
        "details": None,
    }
    if not isinstance(body, dict):
        return out
    err = body.get("error")
    if isinstance(err, dict):
        data = err.get("error_data")
        data = data if isinstance(data, dict) else {}
        out["message"] = str(err.get("message") or status_text)
        out["code"] = err.get("code") if isinstance(err.get("code"), int) else None
        out["subcode"] = (
            err.get("error_subcode") if isinstance(err.get("error_subcode"), int) else None
        )
        out["hello_code"] = data.get("hello_code")
        out["fbtrace_id"] = err.get("fbtrace_id")
        out["details"] = data.get("details", data or None)
        return out
    if isinstance(err, str):
        out["message"] = err
    elif body.get("message"):
        out["message"] = str(body["message"])
    code = body.get("code")
    if isinstance(code, str):
        out["hello_code"] = code
    elif isinstance(code, int) and not isinstance(code, bool):
        out["code"] = code
    extra = {k: v for k, v in body.items() if k not in ("message", "code", "error")}
    out["details"] = extra or None
    return out


def error_class(status: int, hello_code: Optional[str]) -> type[APIError]:
    """Pick the exception class for a response."""
    if status == 401:
        return AuthenticationError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    return APIError
