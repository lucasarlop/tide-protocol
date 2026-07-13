from __future__ import annotations

import sys

from .core import commit_check
from .project import TideError, project_root


def main() -> None:
    try:
        report = commit_check(project_root())
    except TideError as exc:
        print(f"Tide commit gate failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if report.get("allowed"):
        return
    print("Tide blocked this commit.", file=sys.stderr)
    for blocker in report.get("blockers", []):
        print(f"- {blocker}", file=sys.stderr)
    next_action = str(report.get("next_action") or "").strip()
    if next_action:
        print(f"Next: {next_action}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
