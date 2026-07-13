from tide.mcp import INSTRUCTIONS, _tool_summary, tools


def test_mcp_exposes_tide_1_1_quality_surface() -> None:
    surface = tools()
    names = {tool["name"] for tool in surface}
    assert names == {
        "prepare",
        "revise",
        "split",
        "reopen",
        "external_acknowledge",
        "authorize",
        "model_policy",
        "context",
        "check",
        "commit_check",
        "validate",
        "validation_status",
        "validation_wait",
        "validation_log",
        "review_packet",
        "review_get",
        "review_submit",
        "operational_verify",
        "resume",
        "handoff",
        "lock_list",
        "lock_template",
        "status",
    }
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in surface)
    assert "trusted autonomy" in INSTRUCTIONS
    assert "validation_wait" in INSTRUCTIONS
    assert "approved fingerprint is immutable" in INSTRUCTIONS
    assert "Caveman-lite" in INSTRUCTIONS
    assert "model_policy" in INSTRUCTIONS
    assert "xhigh" in INSTRUCTIONS
    assert "commit_check" in INSTRUCTIONS


def test_mcp_model_policy_schema_exposes_only_supported_controls() -> None:
    policy = next(tool for tool in tools() if tool["name"] == "model_policy")
    properties = policy["inputSchema"]["properties"]

    assert properties["strategy"]["enum"] == [
        "economy",
        "balanced",
        "quality",
        "manual",
    ]
    assert properties["review_mode"]["enum"] == ["incremental", "full"]
    assert "failed_attempts" in properties
    assert "root_cause_known" in properties


def test_mcp_validate_schema_exposes_coverage_phase_and_wait() -> None:
    validate = next(tool for tool in tools() if tool["name"] == "validate")
    properties = validate["inputSchema"]["properties"]
    assert properties["phase"]["enum"] == ["targeted", "final"]
    assert "covers" in properties

    wait = next(tool for tool in tools() if tool["name"] == "validation_wait")
    assert wait["inputSchema"]["properties"]["wait_seconds"]["maximum"] == 60


def test_mcp_review_schema_requires_complete_findings() -> None:
    submit = next(tool for tool in tools() if tool["name"] == "review_submit")
    finding = submit["inputSchema"]["properties"]["findings"]["items"]
    structured = finding["oneOf"][1]
    assert structured["properties"]["severity"]["enum"] == [
        "blocking",
        "follow_up",
        "info",
    ]
    assert structured["required"] == ["id", "severity", "message"]
    assert "paths" in structured["properties"]
    assert "expected_action" in structured["properties"]


def test_mcp_text_summary_does_not_duplicate_structured_payload() -> None:
    value = {
        "command": ["pytest"],
        "passed": True,
        "exit_code": 0,
        "log_id": "validation-123",
        "stdout_tail": ["x" * 4_000],
        "phase": "targeted",
    }
    summary = _tool_summary("validate", value)
    assert len(summary) < 200
    assert "stdout_tail" not in summary
    assert "validation-123" in summary


def test_model_policy_summary_is_compact_and_actionable() -> None:
    summary = _tool_summary(
        "model_policy",
        {
            "phase": "implementation",
            "reviewer_agent": "tide-reviewer",
            "recommendation": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
                "switch_recommended": True,
            },
        },
    )

    assert "gpt-5.6-terra" in summary
    assert "reasoning=medium" in summary
    assert "reviewer=tide-reviewer" in summary
    assert len(summary) < 220


def test_review_packet_summary_exposes_selected_reviewer() -> None:
    summary = _tool_summary(
        "review_packet",
        {
            "review_id": "review-123",
            "review_mode": "full",
            "files": ["app.py"],
            "reused": False,
            "reviewer_agent": "tide-reviewer-critical",
        },
    )

    assert "tide-reviewer-critical" in summary


def test_running_validation_summary_says_pending_not_failed() -> None:
    summary = _tool_summary(
        "validation_wait",
        {"status": "running", "passed": None},
    )
    assert "passed=pending" in summary
    assert "false" not in summary


def test_check_summary_exposes_lifecycle_blocker_and_next_action() -> None:
    summary = _tool_summary(
        "check",
        {
            "ready": False,
            "lifecycle": "active",
            "primary_blocker": "independent review required",
            "next_action": "complete incremental review",
        },
    )
    assert "lifecycle=active" in summary
    assert "independent review required" in summary
    assert "complete incremental review" in summary
