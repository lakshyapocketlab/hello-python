"""Send a text message and branch on the SDK's typed exceptions.

Run: HELLO_API_KEY=hello_live_xxx python examples/error_handling.py <phone_number_id> <to> "Hello"
"""

from __future__ import annotations

import sys

from lakshyapocketlab_hello import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    Hello,
    HelloError,
    NotFoundError,
    RateLimitError,
)


def main(phone_number_id: str, to: str, text: str) -> int:
    try:
        # Reads HELLO_API_KEY. Retries for 429, 5xx and network errors have already run here.
        with Hello() as client:
            sent = client.messages.send_text(phone_number_id, to, text)
    except AuthenticationError as e:
        print("bad or disabled API key:", e.message, file=sys.stderr)
    except RateLimitError as e:
        print(f"rate limited ({e.hello_code}); retry after {e.retry_after} s", file=sys.stderr)
    except NotFoundError as e:
        print("not found, check the phone_number_id:", e.message, file=sys.stderr)
    except APIError as e:
        # hello_code (e.g. VALIDATION_ERROR) is the stable value to branch on; quote fbtrace_id
        # when you contact support.
        print(
            f"API error {e.status} hello_code={e.hello_code} code={e.code} "
            f"trace={e.fbtrace_id}: {e.message}",
            file=sys.stderr,
        )
    except APIConnectionError as e:  # includes APITimeoutError
        print("network problem, retries already ran:", e, file=sys.stderr)
    except HelloError as e:
        print("hello error:", e, file=sys.stderr)
    else:
        print("accepted, Hello ID:", sent["messages"][0]["hello_id"])
        return 0
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit('usage: error_handling.py <phone_number_id> <to> "<text>"')
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
