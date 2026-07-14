from __future__ import annotations

import sys

from . import cli
from .commit_hook import main as commit_hook_main


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "commit-check" and "--hook" in sys.argv[2:]:
        commit_hook_main()
        return
    raise SystemExit(cli.main())


if __name__ == "__main__":
    main()
