from __future__ import annotations

import pytest

from tide import mcp_model_policy


def test_review_packet_uses_actual_full_mode_returned_by_tide(monkeypatch) -> None:
    monkeypatch.setattr(
        mcp_model_policy,
        "_ORIGINAL_CALL_TOOL",
        lambda name, arguments: {
            "review_id": "review-123",
            "review_mode": "full",
            "files": ["app.py"],
        },
    )
    observed: dict[str, object] = {}

    def fake_policy(arguments=None, *, phase=None, review_mode=None):
        observed.update({"phase": phase, "review_mode": review_mode})
        return {
            "phase": phase,
            "reviewer_agent": "tide-reviewer-critical",
            "recommendation": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "switch_recommended": False,
            },
        }

    monkeypatch.setattr(mcp_model_policy, "_policy", fake_policy)

    result = mcp_model_policy.call_tool("review_packet", {})

    assert observed == {"phase": "review", "review_mode": "full"}
    assert result["reviewer_agent"] == "tide-reviewer-critical"


@pytest.mark.parametrize(
    "report,expected_phase",
    [
        ({"ready": True, "primary_blocker": None}, "closure"),
        (
            {
                "ready": False,
                "primary_blocker": "independent review required",
            },
            "review",
        ),
        (
            {
                "ready": False,
                "primary_blocker": "changed files lack current validation coverage",
            },
            "validation",
        ),
        (
            {
                "ready": False,
                "primary_blocker": "fix the listed blocking finding",
            },
            "correction",
        ),
    ],
)
def test_check_routes_policy_from_actual_blocker(
    monkeypatch,
    report: dict,
    expected_phase: str,
) -> None:
    monkeypatch.setattr(
        mcp_model_policy,
        "_ORIGINAL_CALL_TOOL",
        lambda name, arguments: dict(report),
    )
    observed: list[str | None] = []

    def fake_policy(arguments=None, *, phase=None, review_mode=None):
        observed.append(phase)
        return {
            "phase": phase,
            "reviewer_agent": None,
            "recommendation": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
                "switch_recommended": phase in {"correction"},
            },
        }

    monkeypatch.setattr(mcp_model_policy, "_policy", fake_policy)

    result = mcp_model_policy.call_tool("check", {})

    assert observed == [expected_phase]
    assert result["model_policy"]["phase"] == expected_phase
