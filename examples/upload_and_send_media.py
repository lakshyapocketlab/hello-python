"""Upload a file, then send it as a document."""

from __future__ import annotations

import sys

from lakshyapocketlab_hello import Hello


def main(to: str, path: str) -> None:
    with Hello() as client:
        number = client.phone_numbers.list()["data"][0]
        pnid = number["phone_number_id"]
        media = client.media.upload(pnid, path, "application/pdf")
        sent = client.messages.send_media(pnid, to, "document", media_id=media["id"])
        print(sent["messages"][0]["hello_id"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
