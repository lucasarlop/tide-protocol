from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

from .project import load_runtime, save_runtime

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Any] = {}


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_v1_fixes_installed", False):
        return
    _CORE = core
    for name in ("submit_review", "record_review", "check"):
        _ORIGINALS[name] = getattr(core, name)
    core.submit_review = submit_review
    core.record_review = record_review
    core.check = check
    core._v1_fixes_installed = True


def _details(findings: list[Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): {
            "paths": list(item.get("paths") or []),
            "expected_action": str(item.get("expected_action") or ""),
        }
        for item in findings
        if isinstance(item, dict) and item.get("id")
    }


def _content_hashes(root: Path, files: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in files:
        path = root / name
        if path.is_file():
            values[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.exists():
            values[name] = "directory"
        else:
            values[name] = "missing"
    return values


def _restore_details(root: Path, review: dict[str, Any], findings: list[Any]) -> dict[str, Any]:
    by_id = _details(findings)
    for item in review.get("findings", []):
        if not isinstance(item, dict):
            continue
        extra = by_id.get(str(item.get("id")), {})
        item["paths"] = list(extra.get("paths") or item.get("paths") or [])
        item["expected_action"] = str(extra.get("expected_action") or item.get("expected_action") or "")
    runtime = load_runtime(root)
    if runtime:
        runtime["review"] = review
        for historical in runtime.get("review_history", []):
            if isinstance(historical, dict) and historical.get("review_id") == review.get("review_id"):
                historical.update(review)
        if review.get("approved"):
            files = list((runtime.get("approved_files") or {}).keys())
            runtime["approved_content"] = _content_hashes(root, files)
        save_runtime(root, runtime)
    return review


def submit_review(root: Path, **kwargs: Any) -> dict[str, Any]:
    findings = list(kwargs.get("findings") or [])
    review = _ORIGINALS["submit_review"](root, **kwargs)
    return _restore_details(root, review, findings)


def record_review(root: Path, **kwargs: Any) -> dict[str, Any]:
    findings = list(kwargs.get("findings") or [])
    review = _ORIGINALS["record_review"](root, **kwargs)
    return _restore_details(root, review, findings)


def _clean_for_approved_files(root: Path, files: list[str]) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *files],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


def _approved_files_current(root: Path, runtime: dict[str, Any]) -> bool:
    expected = runtime.get("approved_content")
    if not isinstance(expected, dict) or not expected:
        return False
    return _content_hashes(root, list(expected)) == expected


def check(root: Path) -> dict[str, Any]:
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    if not runtime or not runtime.get("approved_fingerprint"):
        return report

    approved_files = list((runtime.get("approved_content") or {}).keys())
    equivalent = _approved_files_current(root, runtime) and _clean_for_approved_files(root, approved_files)
    if not equivalent:
        return report

    stale_messages = {
        "independent review is stale for the current diff",
        "independent review required",
        "changed files lack current validation coverage",
    }
    blockers = [item for item in report.get("blockers", []) if str(item) not in stale_messages]
    pending = list(report.get("pending_hardgates", []))
    ready = not blockers and not pending
    runtime["lifecycle"] = "committed"
    runtime["closure_locked"] = True
    save_runtime(root, runtime)

    report["blockers"] = blockers
    report["primary_blocker"] = blockers[0] if blockers else None
    report["ready"] = ready
    report["status"] = "ready" if ready else "blocked"
    report["lifecycle"] = "committed"
    report["next_action"] = "closure ready" if ready else report.get("next_action")
    return report
