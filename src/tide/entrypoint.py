from __future__ import annotations

import sys

from . import cli
from .commit_hook import main as commit_hook_main


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "commit-check":
        commit_hook_main()
        return
    cli.main()
