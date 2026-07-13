from __future__ import annotations

import json
import sys

from . import cli
from .commit_hook import main as commit_hook_main
from .project import TideError, project_root
from .stability import ensure_commit_hook


def _install_hook() -> None:
    try:
        result = ensure_commit_hook(project_root())
    except TideError as exc:
        print(f"Tide hook installation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(result, ensure_ascii=False))
    if not result.get("installed"):
        raise SystemExit(2)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "commit-check":
        commit_hook_main()
        return
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["hook", "install"]:
        _install_hook()
        return
    cli.main()
