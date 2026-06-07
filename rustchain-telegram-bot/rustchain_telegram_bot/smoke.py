from __future__ import annotations

import os

from .api import RustChainClient
from .formatting import fmt_epoch, fmt_health, fmt_miners


def main() -> None:
    client = RustChainClient(os.environ.get("RUSTCHAIN_NODE_URL", "https://50.28.86.131"))
    explorer = os.environ.get("RUSTCHAIN_EXPLORER_URL", "https://50.28.86.131/explorer")
    print(fmt_health(client.health()))
    print()
    print(fmt_epoch(client.epoch(), explorer))
    print()
    print(fmt_miners(client.miners()))


if __name__ == "__main__":
    main()
