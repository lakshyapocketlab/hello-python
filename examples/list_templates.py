"""Print every APPROVED template of a WhatsApp Business Account, following the paging cursor.

Run: HELLO_API_KEY=hello_live_xxx python examples/list_templates.py <waba_id>
"""

from __future__ import annotations

import sys
from typing import Optional

from lakshyapocketlab_hello import Hello


def main(waba_id: str) -> None:
    with Hello() as client:  # reads HELLO_API_KEY
        after: Optional[str] = None
        while True:
            page = client.templates.list(waba_id, status="APPROVED", limit=50, after=after)
            for t in page["data"]:
                print(f"{t['name']:<30} {t['language']:<8} {t['category']}")
            after = page.get("paging", {}).get("cursors", {}).get("after")
            if not after:
                break


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: list_templates.py <waba_id>")
    main(sys.argv[1])
