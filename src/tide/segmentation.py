from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from . import agility as _agility
from . import closure as _closure
from .project import TideError, load_runtime, save_runtime

_CORE: ModuleType | None = None
_ORIGINAL_SPLIT: Any = None
_ORIGINAL_AUTHORIZE: Any = None


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide segmentation refinements are not installed")
    return _CORE


def install(core: ModuleType) -> None:
    global _CORE, _ORIGINAL_SPLIT, _ORIGINAL_AUTHORIZE
    if getattr(core, "_segmentation_refinements_installed", False):
        return
    _CORE = core
    _ORIGINAL_SPLIT = core.split
    _ORIGINAL_AUTHORIZE = core.authorize
    core.split = split
    core.authorize = authorize
    core._segmentation_refinements_installed = True


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    before = load_runtime(root)
    if not before:
        raise TideError("run tide prepare before splitting")
    _closure._ensure_defaults(before)
    task = task.strip()
    target = sorted(dict.fromkeys(str(item).strip() for item in files if str(item).strip()))
    if not task:
        raise TideError("split requires a concrete child task")
    if not target:
        raise TideError("split requires a non-empty child boundary")

    current_files = _core()._task_files(root, before)
    selected = [path for path in current_files if _core()._inside(path, target)]
    if not selected:
        raise TideError("split boundary does not contain any changed file from the current segment")

    history = list(before.get("segment_history", []))
    history.append(_closure._archive_segment(before))
    previous_segment_id = str(before.get("segment_id"))
    previous_validations = list(before.get("validations", []))
    previous_followups = list(before.get("follow_up_tasks", []))
    previous_records = list(before.get("follow_up_records", []))
    old_boundary = list(before.get("boundary", []))
    add_files = [item for item in target if item not in old_boundary]
    remove_files = [item for item in old_boundary if item not in target]

    before["closure_locked"] = False
    before["review"] = None
    save_runtime(root, before)
    _closure._ORIGINALS["revise"](
        root,
        task=task,
        add_files=add_files,
        remove_files=remove_files,
        add_required_validations=None,
        remove_required_validations=None,
    )
    runtime = load_runtime(root)
    _closure._ensure_defaults(runtime)
    compatible_validations = []
    for item in previous_validations:
        evidence_files = [str(path) for path in item.get("files", [])]
        if evidence_files and all(_core()._inside(path, target) for path in evidence_files):
            if _agility._validation_is_current(root, item):
                compatible_validations.append(item)

    runtime["segment_history"] = history
    runtime["parent_segment_id"] = previous_segment_id
    runtime["segment_id"] = _closure._segment_id()
    runtime["segment_index"] = int(before.get("segment_index", 0)) + 1
    runtime["segment_started_at"] = _closure._now_iso()
    runtime["boundary_signature"] = _closure._boundary_signature(list(runtime.get("boundary", [])))
    runtime["workflow_metrics"] = {
        "review_cycles": 0,
        "review_attempts": 0,
        "review_cancelled": 0,
        "review_packets": 0,
        "scope_expansions": 0,
        "validation_runs": 0,
        "reopens": 0,
    }
    runtime["review"] = None
    runtime["review_history"] = []
    runtime["pending_review"] = None
    runtime["validations"] = compatible_validations
    runtime["follow_up_tasks"] = previous_followups
    runtime["follow_up_records"] = previous_records
    runtime["closure_locked"] = False
    runtime["closure_reason"] = None
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["closure_warning"] = None
    runtime["extended_investigation_grant"] = None
    hardgates = set(runtime.get("hardgates", [])) - {"extended_investigation", "closure_reopen"}
    authorized = set(runtime.get("authorized_hardgates", [])) - {"extended_investigation", "closure_reopen"}
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["status"] = "revising"
    _agility._apply_budget(runtime)
    runtime["updated_at"] = _closure._now_iso()
    save_runtime(root, runtime)
    return _closure.preparation_report(root, runtime)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before authorization")
    _closure._ensure_defaults(runtime)
    requested = set(runtime.get("hardgates", [])) if all_gates else set(gates or [])
    if "extended_investigation" in requested and "extended_investigation" not in set(runtime.get("hardgates", [])):
        state = _agility._apply_budget(runtime)
        if state.get("split_required"):
            hardgates = set(runtime.get("hardgates", []))
            hardgates.add("extended_investigation")
            runtime["hardgates"] = sorted(hardgates)
            save_runtime(root, runtime)
    return _ORIGINAL_AUTHORIZE(root, gates, all_gates=all_gates)
