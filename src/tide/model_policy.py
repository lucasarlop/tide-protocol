from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

from .project import TideError, load_runtime

_CORE: ModuleType | None = None

STRATEGIES = {"economy", "balanced", "quality", "manual"}
PHASES = {
    "planning",
    "exploration",
    "implementation",
    "correction",
    "investigation",
    "validation",
    "review",
    "operational",
    "closure",
}
REVIEW_MODES = {"incremental", "full"}
SENSITIVE_GATES = {
    "auth",
    "database",
    "dependency",
    "infrastructure",
    "production",
    "public_api",
    "secrets",
}

PRESETS: dict[str, dict[str, str]] = {
    "luna_low": {
        "model_class": "fast",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
    },
    "terra_medium": {
        "model_class": "balanced",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
    },
    "terra_high": {
        "model_class": "balanced",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "high",
    },
    "sol_medium": {
        "model_class": "reasoning",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
    },
    "sol_high": {
        "model_class": "reasoning",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
    },
    "sol_xhigh": {
        "model_class": "critical",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    },
}


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_model_policy_installed", False):
        return
    _CORE = core
    core.model_policy = model_policy
    core._model_policy_installed = True


def _config_path(root: Path) -> Path:
    return root / ".tide" / "model-policy.json"


def _load_config(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = _config_path(root)
    if not path.exists():
        return {"strategy": "balanced", "allow_xhigh": True}, []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"strategy": "balanced", "allow_xhigh": True}, [
            f"ignored invalid {path.relative_to(root)}: {exc}"
        ]
    if not isinstance(parsed, dict):
        return {"strategy": "balanced", "allow_xhigh": True}, [
            f"ignored invalid {path.relative_to(root)}: expected JSON object"
        ]
    strategy = str(parsed.get("strategy") or "balanced").strip().lower()
    warnings: list[str] = []
    if strategy not in STRATEGIES:
        warnings.append(f"unknown model strategy {strategy!r}; using balanced")
        strategy = "balanced"
    return {
        "strategy": strategy,
        "allow_xhigh": bool(parsed.get("allow_xhigh", True)),
    }, warnings


def _blocking_findings(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    return [
        item
        for item in review.get("findings", [])
        if isinstance(item, dict) and item.get("severity") == "blocking"
    ]


def _infer_phase(runtime: dict[str, Any]) -> str:
    lifecycle = str(runtime.get("lifecycle") or "active")
    if lifecycle == "operational_verification":
        return "operational"
    if lifecycle in {"approved", "committed", "closed"}:
        return "closure"
    if lifecycle == "reviewing" or runtime.get("pending_review"):
        return "review"
    if _blocking_findings(runtime):
        return "correction"
    if not runtime.get("validations") and not runtime.get("review"):
        return "planning"
    return "implementation"


def _review_mode(runtime: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        value = explicit.strip().lower()
        if value not in REVIEW_MODES:
            raise TideError(f"invalid review mode: {explicit}")
        return value
    pending = runtime.get("pending_review")
    if isinstance(pending, dict) and pending.get("review_mode") in REVIEW_MODES:
        return str(pending["review_mode"])
    review = runtime.get("review")
    if isinstance(review, dict) and review.get("review_mode") in REVIEW_MODES:
        return str(review["review_mode"])
    return "incremental" if runtime.get("review_history") else "full"


def _risk_signals(runtime: dict[str, Any]) -> tuple[bool, list[str]]:
    hardgates = set(runtime.get("hardgates", []))
    sensitive = sorted(hardgates & SENSITIVE_GATES)
    strict = str(runtime.get("mode") or "fast") == "strict" or bool(sensitive) or bool(runtime.get("locks"))
    signals: list[str] = []
    if strict:
        signals.append("strict change")
    if sensitive:
        signals.append("sensitive gates: " + ", ".join(sensitive))
    if runtime.get("locks"):
        signals.append("protected Module Lock")
    if runtime.get("split_required"):
        signals.append("task is not converging and should split")
    return strict, signals


def _select_preset(
    *,
    strategy: str,
    phase: str,
    strict: bool,
    review_mode: str,
    failed_attempts: int,
    root_cause_known: bool | None,
    allow_xhigh: bool,
) -> tuple[str | None, list[str]]:
    reasons: list[str] = []
    if strategy == "manual":
        return None, ["manual strategy leaves model selection to the user"]

    if (
        allow_xhigh
        and phase in {"correction", "investigation"}
        and failed_attempts >= 2
        and root_cause_known is False
    ):
        return "sol_xhigh", [
            "root cause remains unknown after at least two bounded attempts"
        ]

    if phase == "operational":
        return ("terra_medium" if strategy == "quality" else "luna_low"), [
            "operational checks are deterministic and should not trigger deep reasoning"
        ]
    if phase == "closure":
        return ("terra_medium" if strategy == "quality" else "luna_low"), [
            "closure is evidence reporting, not a new implementation pass"
        ]
    if phase == "exploration":
        return ("sol_medium" if strategy == "quality" else "terra_medium"), [
            "read-heavy exploration needs reliable tool use but not maximum reasoning"
        ]
    if phase == "validation":
        return ("sol_medium" if strict and strategy == "quality" else "terra_medium"), [
            "running tests is mechanical; interpretation needs balanced reasoning"
        ]
    if phase == "review":
        if strict or review_mode == "full" or strategy == "quality":
            return "sol_high", [
                "full or sensitive review needs assumption checking and edge-case analysis"
            ]
        return "terra_high", [
            "incremental validated review is narrow but still benefits from high checking effort"
        ]
    if phase == "planning":
        if strict:
            return "sol_high", [
                "sensitive planning has multiple constraints and expensive failure modes"
            ]
        if strategy == "quality":
            return "sol_medium", ["quality strategy raises ordinary planning depth"]
        return "terra_medium", ["ordinary bounded planning is everyday engineering work"]
    if phase == "implementation":
        if strict:
            return ("sol_high" if strategy == "quality" else "sol_medium"), [
                "sensitive implementation keeps the strongest model but avoids unnecessary maximum effort"
            ]
        if strategy == "quality":
            return "sol_medium", ["quality strategy raises implementation model capability"]
        return "terra_medium", ["bounded implementation has known acceptance criteria"]
    if phase in {"correction", "investigation"}:
        if root_cause_known is True and not strict:
            return "terra_medium", ["root cause is known; apply the smallest verified correction"]
        return "sol_high", [
            "unresolved debugging needs deeper causal analysis before another patch"
        ]

    raise TideError(f"unsupported model-policy phase: {phase}")


def _reviewer_agent(preset_name: str | None, *, strict: bool, review_mode: str) -> str | None:
    if preset_name is None:
        return None
    if strict or review_mode == "full" or preset_name in {"sol_high", "sol_xhigh"}:
        return "tide-reviewer-critical"
    return "tide-reviewer"


def _adapter_hints(model: str, reasoning_effort: str) -> dict[str, Any]:
    return {
        "codex": {
            "model": model,
            "reasoning_effort": reasoning_effort,
            "interactive_action": "use /model only at a session or major-phase boundary",
        },
        "opencode": {
            "model": f"openai/{model}",
            "reasoning_effort": reasoning_effort,
            "interactive_action": "use /models or the model/variant selector only at a session or major-phase boundary",
        },
    }


def model_policy(
    root: Path,
    *,
    phase: str | None = None,
    strategy: str | None = None,
    review_mode: str | None = None,
    failed_attempts: int | None = None,
    root_cause_known: bool | None = None,
) -> dict[str, Any]:
    runtime = load_runtime(root) or {}
    config, warnings = _load_config(root)

    resolved_strategy = str(strategy or config["strategy"]).strip().lower()
    if resolved_strategy not in STRATEGIES:
        raise TideError(f"invalid model strategy: {resolved_strategy}")

    resolved_phase = str(phase or _infer_phase(runtime)).strip().lower()
    if resolved_phase not in PHASES:
        raise TideError(f"invalid model-policy phase: {resolved_phase}")

    resolved_review_mode = _review_mode(runtime, review_mode)
    metrics = runtime.get("workflow_metrics") if isinstance(runtime.get("workflow_metrics"), dict) else {}
    inferred_attempts = max(
        int(metrics.get("review_cycles", 0)),
        int(metrics.get("reopens", 0)),
    )
    attempts = max(0, int(inferred_attempts if failed_attempts is None else failed_attempts))
    strict, signals = _risk_signals(runtime)

    preset_name, reasons = _select_preset(
        strategy=resolved_strategy,
        phase=resolved_phase,
        strict=strict,
        review_mode=resolved_review_mode,
        failed_attempts=attempts,
        root_cause_known=root_cause_known,
        allow_xhigh=bool(config["allow_xhigh"]),
    )

    if preset_name is None:
        return {
            "strategy": resolved_strategy,
            "phase": resolved_phase,
            "automatic": False,
            "recommendation": None,
            "reviewer_agent": None,
            "signals": signals,
            "reasons": reasons,
            "warnings": warnings,
        }

    preset = dict(PRESETS[preset_name])
    switch_recommended = resolved_phase in {
        "planning",
        "implementation",
        "correction",
        "investigation",
    }
    if resolved_phase == "review":
        switch_recommended = False
        reasons.append("use the dedicated reviewer subagent instead of changing the writer model")
    if resolved_phase in {"validation", "operational", "closure"}:
        switch_recommended = False
        reasons.append("do not switch models for a short mechanical phase")

    if preset_name != "sol_xhigh":
        reasons.append("xhigh is reserved for an explicitly unknown root cause after two bounded failures")

    recommendation = {
        **preset,
        "preset": preset_name,
        "switch_recommended": switch_recommended,
        "apply_at": "new session or major-phase boundary" if switch_recommended else "keep current writer; apply to specialized subagent when applicable",
        "adapters": _adapter_hints(preset["model"], preset["reasoning_effort"]),
    }
    return {
        "strategy": resolved_strategy,
        "phase": resolved_phase,
        "automatic": True,
        "strict": strict,
        "review_mode": resolved_review_mode,
        "failed_attempts": attempts,
        "root_cause_known": root_cause_known,
        "recommendation": recommendation,
        "reviewer_agent": _reviewer_agent(
            preset_name,
            strict=strict,
            review_mode=resolved_review_mode,
        ),
        "signals": signals,
        "reasons": reasons,
        "warnings": warnings,
        "quality_floor": {
            "writer": "Terra medium for ordinary implementation; Sol medium or higher for strict implementation",
            "review": "Terra high for narrow incremental review; Sol high for full or sensitive review",
            "xhigh": "never automatic without an explicitly unknown root cause and two bounded failed attempts",
        },
    }
