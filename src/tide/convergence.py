from __future__ import annotations

from pathlib import Path
from typing import Any

from .project import TideError, load_runtime, save_runtime
from .rules import evaluate_state

def convergence(
    root: Path,
    *,
    summary: str | None = None,
    new_evidence: bool = False,
    root_cause_known: bool | None = None,
    next_step: str | None = None,
    decision: str | None = None,
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before recording convergence")
    value = state.setdefault("convergence", {})
    if decision:
        if decision not in {"continue_one_cycle", "stop_and_report"}:
            raise TideError("invalid convergence decision")
        if value.get("status") != "investigation_checkpoint":
            raise TideError("no investigation checkpoint is awaiting a decision")
        value["decision"] = decision
        if decision == "continue_one_cycle":
            value["status"] = "investigating"
            value["cycle_grants"] = int(value.get("cycle_grants", 0)) + 1
            value["cycle_active"] = True
            value["failed_attempts"] = 0
        else:
            value["status"] = "stop_requested"
        save_runtime(root, state)
        return evaluate_state(root, state)

    note = str(summary or "").strip()
    if note:
        value["last_progress"] = note
        if new_evidence:
            evidence = list(value.get("evidence") or [])
            evidence.append(note)
            value["evidence"] = evidence[-20:]
    if root_cause_known is not None:
        value["root_cause_known"] = bool(root_cause_known)
    if next_step is not None:
        value["next_step"] = next_step.strip()

    if root_cause_known is True:
        value["status"] = "progressing"
        value["cycle_active"] = False
        value["failed_attempts"] = 0
    elif new_evidence and int(value.get("failed_attempts", 0)) >= 2:
        value["status"] = "investigation_checkpoint"
        value["investigation_cycles"] = int(value.get("investigation_cycles", 0)) + 1
        value["decision"] = None
    elif not new_evidence and int(value.get("failed_attempts", 0)) >= 2:
        value["status"] = "stop_requested"
    else:
        value["status"] = "progressing"
    save_runtime(root, state)
    return evaluate_state(root, state)
