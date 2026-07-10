from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .commands import run_validation
from .validation_jobs import read_job, save_job


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--validation-id", required=True)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    job = read_job(root, args.validation_id)
    try:
        result = run_validation(
            root,
            list(job.get("command") or []),
            timeout=int(job.get("timeout") or 300),
        )
    except BaseException as exc:
        result = {
            "command": list(job.get("command") or []),
            "exit_code": 125,
            "passed": False,
            "timed_out": False,
            "duration_seconds": None,
            "stdout": "",
            "stderr": f"validation worker failed: {exc}",
        }
    job.update(
        {
            "status": "completed",
            "completed_at": now_iso(),
            "result": result,
        }
    )
    save_job(root, job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
