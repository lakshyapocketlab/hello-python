"""Send an approved template (the only type that can start a conversation)."""

from __future__ import annotations

import sys

from lakshyapocketlab_hello import Hello


def main(to: str, template_name: str) -> None:
    with Hello() as client:
        number = client.phone_numbers.list()["data"][0]
        sent = client.messages.send_template(
            number["phone_number_id"],
            to,
            template_name,
            "en_US",
            components=[{"type": "body", "parameters": [{"type": "text", "text": "Asha"}]}],
            idempotency_key=f"example-{template_name}-{to}",  # makes retries safe
        )
        print(sent["messages"][0]["hello_id"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
