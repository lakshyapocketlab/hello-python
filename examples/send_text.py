"""Send a text message. Needs an open 24-hour window with the recipient."""

from __future__ import annotations

import sys

from lakshyapocketlab_hello import Hello


def main(to: str) -> None:
    with Hello() as client:  # reads HELLO_API_KEY
        number = client.phone_numbers.list()["data"][0]
        sent = client.messages.send_text(
            number["phone_number_id"], to, "Hello from the Hello Python SDK!", sync=True
        )
        print(sent["messages"][0]["id"])


if __name__ == "__main__":
    main(sys.argv[1])
