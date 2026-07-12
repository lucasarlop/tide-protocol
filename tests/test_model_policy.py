from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tide.model_policy import model_policy
from tide.project import save_runtime


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


def make_repo(tmp_path: Path, runtime: dict | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    save_runtime(
        root,
        {
            "task": "change app",
            "boundary": ["app.py"],
            "mode": "fast",
            "hardgates": [],
            "authorized_hardgates": [],
            "workflow_metrics": {"review_cycles": 0, "reopens": 0},
            "review_history": [],
            **(runtime or {}),
        },
    )
    return root


def recommendation(result: dict) -> dict:
    value = result.get("recommendation")
    assert isinstance(value, dict)
    return value


def test_balanced_ordinary_planning_uses_terra_medium(tmp_path: Path) -> None:
    result = model_policy(make_repo(tmp_path), phase="planning")

    assert recommendation(result)["model"] == "gpt-5.6-terra"
    assert recommendation(result)["reasoning_effort"] == "medium"
    assert recommendation(result)["switch_recommended"] is True


def test_balanced_ordinary_implementation_uses_terra_medium(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    result = model_policy(root)

    assert result["phase"] == "implementation"
    assert recommendation(result)["preset"] == "terra_medium"


def test_sensitive_planning_uses_sol_high(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"mode": "strict", "hardgates": ["database"]})

    result = model_policy(root, phase="planning")

    assert recommendation(result)["preset"] == "sol_high"


def test_sensitive_implementation_uses_sol_medium(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"mode": "strict", "hardgates": ["public_api"]})

    result = model_policy(root, phase="implementation")

    assert recommendation(result)["preset"] == "sol_medium"


def test_incremental_review_uses_terra_high_reviewer(tmp_path: Path) -> None:
    result = model_policy(
        make_repo(tmp_path),
        phase="review",
        review_mode="incremental",
    )

    assert recommendation(result)["preset"] == "terra_high"
    assert recommendation(result)["switch_recommended"] is False
    assert result["reviewer_agent"] == "tide-reviewer"


def test_full_review_uses_sol_high_critical_reviewer(tmp_path: Path) -> None:
    result = model_policy(
        make_repo(tmp_path),
        phase="review",
        review_mode="full",
    )

    assert recommendation(result)["preset"] == "sol_high"
    assert result["reviewer_agent"] == "tide-reviewer-critical"


def test_sensitive_incremental_review_uses_critical_reviewer(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"mode": "strict", "hardgates": ["auth"]})

    result = model_policy(root, phase="review", review_mode="incremental")

    assert recommendation(result)["preset"] == "sol_high"
    assert result["reviewer_agent"] == "tide-reviewer-critical"


def test_operational_phase_does_not_recommend_writer_switch(tmp_path: Path) -> None:
    result = model_policy(make_repo(tmp_path), phase="operational")

    assert recommendation(result)["preset"] == "luna_low"
    assert recommendation(result)["switch_recommended"] is False


def test_xhigh_requires_unknown_root_cause_after_two_bounded_failures(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)

    before_threshold = model_policy(
        root,
        phase="investigation",
        failed_attempts=1,
        root_cause_known=False,
    )
    known_cause = model_policy(
        root,
        phase="correction",
        failed_attempts=3,
        root_cause_known=True,
    )
    escalated = model_policy(
        root,
        phase="investigation",
        failed_attempts=2,
        root_cause_known=False,
    )

    assert recommendation(before_threshold)["preset"] == "sol_high"
    assert recommendation(known_cause)["preset"] == "terra_medium"
    assert recommendation(escalated)["preset"] == "sol_xhigh"


def test_project_config_can_disable_xhigh(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    config = root / ".tide" / "model-policy.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"strategy": "balanced", "allow_xhigh": False}),
        encoding="utf-8",
    )

    result = model_policy(
        root,
        phase="investigation",
        failed_attempts=4,
        root_cause_known=False,
    )

    assert recommendation(result)["preset"] == "sol_high"


def test_manual_strategy_returns_no_automatic_recommendation(tmp_path: Path) -> None:
    result = model_policy(make_repo(tmp_path), phase="planning", strategy="manual")

    assert result["automatic"] is False
    assert result["recommendation"] is None
