from __future__ import annotations

import json
import sys

from .core import commit_check
from .project import TideError, project_root


def main() -> None:
    try:
        result = commit_check(project_root())
    except TideError as exc:
        print(f"Tide blocked this commit: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if result.get("allowed"):
        return
    print("Tide blocked this commit.", file=sys.stderr)
    print(json.dumps({"blockers": result.get("blockers"), "next_action": result.get("next_action")}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(2)
