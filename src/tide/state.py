from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import TideError, read_json, runtime_path, write_json

SCHEMA_VERSION = 4
LIFECYCLES = {"idle", "active", "approved", "committed", "abandoned"}
CONVERGENCE_STATES = {
    "progressing",
    "investigating",
    "investigation_checkpoint",
    "stop_requested",
    "externally_blocked",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_task_state(
    *,
    task: str,
    boundary: list[str],
    baseline_files: list[str],
    baseline_fingerprints: dict[str, str],
    required_validations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": f"task-{uuid.uuid4().hex[:12]}",
        "task": task.strip(),
        "lifecycle": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "revision": 0,
        "boundary": sorted(dict.fromkeys(boundary)),
        "baseline_files": sorted(dict.fromkeys(baseline_files)),
        "baseline_fingerprints": dict(baseline_fingerprints),
        "required_validations": sorted(dict.fromkeys(required_validations)),
        "validations": [],
        "review": None,
        "pending_review": None,
        "review_history": [],
        "follow_up_tasks": [],
        "approved_snapshot": None,
        "operational_checks": [],
        "operational_mode": False,
        "authorizations": [],
        "policy": dict(policy),
        "segments": {
            "current_id": f"segment-{uuid.uuid4().hex[:12]}",
            "index": 0,
            "history": [],
            "receipts": [],
        },
        "external_acknowledgements": {},
        "convergence": {
            "status": "progressing",
            "failed_attempts": 0,
            "investigation_cycles": 0,
            "cycle_grants": 0,
            "cycle_active": False,
            "root_cause_known": None,
            "last_progress": None,
            "evidence": [],
            "next_step": None,
            "decision": None,
        },
        "warnings": [],
        "archive": [],
    }


def load_state(root: Path) -> dict[str, Any]:
    path = runtime_path(root)
    if not path.exists():
        return {}
    value = read_json(path, None, strict=True)
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise TideError(f"invalid Tide runtime at {path}: expected JSON object")
    migrated = migrate_state(value)
    validate_state(migrated)
    if migrated != value:
        save_state(root, migrated)
    return migrated


def save_state(root: Path, state: dict[str, Any]) -> None:
    if state:
        state = migrate_state(dict(state))
        validate_state(state)
        state["updated_at"] = now_iso()
    write_json(runtime_path(root), state)


def migrate_state(value: dict[str, Any]) -> dict[str, Any]:
    if not value:
        return {}
    result = dict(value)
    schema = int(result.get("schema_version") or 0)
    if schema >= SCHEMA_VERSION:
        _ensure_defaults(result)
        return result

    task = str(result.get("task") or "").strip()
    if not task:
        return {}

    legacy_lifecycle = str(result.get("lifecycle") or result.get("status") or "active")
    if legacy_lifecycle in {"committed", "closed"}:
        lifecycle = "committed"
    elif legacy_lifecycle == "approved":
        lifecycle = "approved"
    elif legacy_lifecycle == "abandoned":
        lifecycle = "abandoned"
    else:
        lifecycle = "active"

    approved_snapshot = result.get("approved_snapshot")
    if not isinstance(approved_snapshot, dict):
        approved_files = result.get("approved_files")
        approved_content = result.get("approved_content")
        if isinstance(approved_files, dict) and approved_files:
            approved_snapshot = {
                "fingerprint": result.get("approved_fingerprint"),
                "files": dict(approved_files),
                "content": dict(approved_content or {}),
                "review_id": (result.get("review") or {}).get("review_id")
                if isinstance(result.get("review"), dict)
                else None,
                "approved_at": result.get("approved_at"),
            }
        else:
            approved_snapshot = None

    segments = result.get("segments")
    if not isinstance(segments, dict):
        segments = {
            "current_id": result.get("segment_id") or f"segment-{uuid.uuid4().hex[:12]}",
            "index": int(result.get("segment_index", 0)),
            "history": list(result.get("segment_history") or []),
            "receipts": list(result.get("segment_receipts") or []),
        }

    authorizations = result.get("authorizations")
    if not isinstance(authorizations, list):
        authorizations = list(result.get("authorized_hardgates") or [])

    convergence = result.get("convergence")
    if not isinstance(convergence, dict):
        convergence = {
            "status": "progressing",
            "failed_attempts": 0,
            "investigation_cycles": 0,
            "cycle_grants": 0,
            "cycle_active": False,
            "root_cause_known": None,
            "last_progress": None,
            "evidence": [],
            "next_step": None,
            "decision": None,
        }

    result.update(
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": result.get("task_id") or f"task-{uuid.uuid4().hex[:12]}",
            "task": task,
            "lifecycle": lifecycle,
            "created_at": result.get("created_at") or now_iso(),
            "updated_at": result.get("updated_at") or now_iso(),
            "revision": int(result.get("revision", 0)),
            "boundary": list(result.get("boundary") or []),
            "baseline_files": list(result.get("baseline_files") or []),
            "baseline_fingerprints": dict(result.get("baseline_fingerprints") or {}),
            "required_validations": list(result.get("required_validations") or []),
            "validations": list(result.get("validations") or []),
            "review": result.get("review") if isinstance(result.get("review"), dict) else None,
            "pending_review": result.get("pending_review") if isinstance(result.get("pending_review"), dict) else None,
            "review_history": list(result.get("review_history") or []),
            "follow_up_tasks": list(result.get("follow_up_tasks") or []),
            "approved_snapshot": approved_snapshot,
            "operational_checks": list(result.get("operational_checks") or []),
            "operational_mode": legacy_lifecycle == "operational_verification"
            or bool(result.get("operational_mode")),
            "authorizations": authorizations,
            "policy": dict(result.get("policy") or {}),
            "segments": segments,
            "external_acknowledgements": dict(
                result.get("external_acknowledgements")
                or result.get("acknowledged_external_changes")
                or {}
            ),
            "convergence": convergence,
            "warnings": list(result.get("warnings") or []),
            "archive": list(result.get("archive") or []),
        }
    )
    _ensure_defaults(result)
    return result


def validate_state(state: dict[str, Any]) -> None:
    if int(state.get("schema_version", 0)) != SCHEMA_VERSION:
        raise TideError("unsupported Tide runtime schema")
    if not str(state.get("task") or "").strip():
        raise TideError("invalid Tide runtime: task is required")
    lifecycle = str(state.get("lifecycle") or "")
    if lifecycle not in LIFECYCLES:
        raise TideError(f"invalid Tide runtime lifecycle: {lifecycle}")
    if not isinstance(state.get("boundary"), list):
        raise TideError("invalid Tide runtime: boundary must be a list")
    if not isinstance(state.get("validations"), list):
        raise TideError("invalid Tide runtime: validations must be a list")
    if not isinstance(state.get("segments"), dict):
        raise TideError("invalid Tide runtime: segments must be an object")
    convergence = state.get("convergence")
    if not isinstance(convergence, dict):
        raise TideError("invalid Tide runtime: convergence must be an object")
    status = str(convergence.get("status") or "progressing")
    if status not in CONVERGENCE_STATES:
        raise TideError(f"invalid convergence status: {status}")


def archive_summary(state: dict[str, Any], *, outcome: str) -> dict[str, Any]:
    return {
        "task_id": state.get("task_id"),
        "task": state.get("task"),
        "outcome": outcome,
        "lifecycle": state.get("lifecycle"),
        "files": sorted((state.get("approved_snapshot") or {}).get("files", {})),
        "review_id": (state.get("approved_snapshot") or {}).get("review_id"),
        "created_at": state.get("created_at"),
        "closed_at": now_iso(),
    }


def _ensure_defaults(state: dict[str, Any]) -> None:
    state.setdefault("schema_version", SCHEMA_VERSION)
    state.setdefault("task_id", f"task-{uuid.uuid4().hex[:12]}")
    state.setdefault("lifecycle", "active")
    state.setdefault("created_at", now_iso())
    state.setdefault("updated_at", now_iso())
    state.setdefault("revision", 0)
    state.setdefault("boundary", [])
    state.setdefault("baseline_files", [])
    state.setdefault("baseline_fingerprints", {})
    state.setdefault("required_validations", [])
    state.setdefault("validations", [])
    state.setdefault("review", None)
    state.setdefault("pending_review", None)
    state.setdefault("review_history", [])
    state.setdefault("follow_up_tasks", [])
    state.setdefault("approved_snapshot", None)
    state.setdefault("operational_checks", [])
    state.setdefault("operational_mode", False)
    state.setdefault("authorizations", [])
    state.setdefault("policy", {})
    state.setdefault(
        "segments",
        {
            "current_id": f"segment-{uuid.uuid4().hex[:12]}",
            "index": 0,
            "history": [],
            "receipts": [],
        },
    )
    state.setdefault("external_acknowledgements", {})
    state.setdefault(
        "convergence",
        {
            "status": "progressing",
            "failed_attempts": 0,
            "investigation_cycles": 0,
            "cycle_grants": 0,
            "cycle_active": False,
            "root_cause_known": None,
            "last_progress": None,
            "evidence": [],
            "next_step": None,
            "decision": None,
        },
    )
    state.setdefault("warnings", [])
    state.setdefault("archive", [])
