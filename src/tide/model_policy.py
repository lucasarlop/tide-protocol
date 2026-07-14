from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import TideError, load_runtime

STRATEGIES = {"balanced", "quality", "manual"}
PHASES = {
    "planning", "exploration", "implementation", "correction", "investigation",
    "validation", "review", "operational", "closure",
}

PRESETS: dict[str, dict[str, str]] = {
    "terra_medium": {"model_class": "balanced", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
    "terra_high": {"model_class": "balanced", "model": "gpt-5.6-terra", "reasoning_effort": "high"},
    "sol_medium": {"model_class": "reasoning", "model": "gpt-5.6-sol", "reasoning_effort": "medium"},
    "sol_high": {"model_class": "reasoning", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
    "sol_xhigh": {"model_class": "critical", "model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
}


def _config_path(root: Path) -> Path:
    return root / ".tide" / "model-policy.json"


def _load_config(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = _config_path(root)
    default = {"strategy": "balanced", "allow_xhigh": True}
    if not path.exists():
        return default, []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return default, [f"ignored invalid {path.relative_to(root)}: {exc}"]
    if not isinstance(parsed, dict):
        return default, [f"ignored invalid {path.relative_to(root)}: expected JSON object"]
    strategy = str(parsed.get("strategy") or "balanced").strip().lower()
    warnings: list[str] = []
    if strategy == "economy":
        warnings.append("economy strategy was consolidated into balanced")
        strategy = "balanced"
    if strategy not in STRATEGIES:
        warnings.append(f"unknown model strategy {strategy!r}; using balanced")
        strategy = "balanced"
    return {"strategy": strategy, "allow_xhigh": bool(parsed.get("allow_xhigh", True))}, warnings


def _infer_phase(state: dict[str, Any]) -> str:
    if not state:
        return "planning"
    if state.get("operational_mode"):
        return "operational"
    lifecycle = str(state.get("lifecycle") or "active")
    if lifecycle in {"approved", "committed"}:
        return "closure"
    convergence = state.get("convergence") or {}
    if convergence.get("status") in {"investigating", "investigation_checkpoint"}:
        return "investigation"
    review = state.get("review") or {}
    if any(
        isinstance(item, dict) and item.get("severity") == "blocking"
        for item in review.get("findings", [])
    ):
        return "correction"
    if state.get("pending_review"):
        return "review"
    return "implementation" if state.get("boundary") else "planning"


def model_policy(
    root: Path,
    *,
    phase: str | None = None,
    strategy: str | None = None,
    review_mode: str | None = None,
    failed_attempts: int | None = None,
    root_cause_known: bool | None = None,
) -> dict[str, Any]:
    state = load_runtime(root) or {}
    config, warnings = _load_config(root)
    resolved_strategy = str(strategy or config["strategy"]).strip().lower()
    if resolved_strategy == "economy":
        resolved_strategy = "balanced"
        warnings.append("economy strategy was consolidated into balanced")
    if resolved_strategy not in STRATEGIES:
        raise TideError(f"invalid model strategy: {resolved_strategy}")
    resolved_phase = str(phase or _infer_phase(state)).strip().lower()
    if resolved_phase not in PHASES:
        raise TideError(f"invalid model-policy phase: {resolved_phase}")
    review_level = str((state.get("policy") or {}).get("review_level") or "normal")
    strict = review_level == "critical" or bool((state.get("policy") or {}).get("risk_signals"))
    convergence = state.get("convergence") or {}
    attempts = max(0, int(failed_attempts if failed_attempts is not None else convergence.get("failed_attempts", 0)))
    known = root_cause_known if root_cause_known is not None else convergence.get("root_cause_known")

    if resolved_strategy == "manual":
        return {
            "strategy": resolved_strategy,
            "phase": resolved_phase,
            "automatic": False,
            "recommendation": None,
            "reviewer_agent": None,
            "warnings": warnings,
            "reasons": ["manual strategy leaves model selection to the user"],
        }

    if resolved_phase == "review":
        preset_name = "sol_high" if strict or review_mode == "full" else "terra_high"
    elif resolved_phase in {"operational", "closure", "validation"}:
        preset_name = "terra_medium"
    elif resolved_phase == "planning":
        preset_name = "sol_high" if strict else ("sol_medium" if resolved_strategy == "quality" else "terra_medium")
    elif resolved_phase == "implementation":
        preset_name = "sol_medium" if strict or resolved_strategy == "quality" else "terra_medium"
    elif resolved_phase in {"correction", "investigation"}:
        if bool(config["allow_xhigh"]) and attempts >= 2 and known is False:
            preset_name = "sol_xhigh"
        elif known is True and not strict:
            preset_name = "terra_medium"
        else:
            preset_name = "sol_high"
    else:
        preset_name = "sol_medium" if resolved_strategy == "quality" else "terra_medium"

    preset = dict(PRESETS[preset_name])
    switch_recommended = resolved_phase in {"planning", "implementation", "correction", "investigation"}
    if resolved_phase in {"validation", "review", "operational", "closure"}:
        switch_recommended = False
    reviewer_agent = None
    if resolved_phase == "review":
        reviewer_agent = "tide-reviewer-critical" if preset_name == "sol_high" else "tide-reviewer"
    return {
        "strategy": resolved_strategy,
        "phase": resolved_phase,
        "automatic": True,
        "strict": strict,
        "failed_attempts": attempts,
        "root_cause_known": known,
        "recommendation": {
            **preset,
            "preset": preset_name,
            "switch_recommended": switch_recommended,
            "apply_at": "new session or major-phase boundary" if switch_recommended else "keep current writer",
        },
        "reviewer_agent": reviewer_agent,
        "risk_signals": list((state.get("policy") or {}).get("risk_signals") or []),
        "warnings": warnings,
        "reasons": [
            "use proportional reasoning for the current phase",
            "xhigh requires two bounded failures with an explicitly unknown root cause",
        ],
    }
