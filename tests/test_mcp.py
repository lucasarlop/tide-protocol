from tide.mcp import INSTRUCTIONS, _tool_summary, tools


def test_mcp_exposes_tide_1_quality_surface() -> None:
    surface = tools()
    names = {tool["name"] for tool in surface}
    assert names == {
        "prepare",
        "revise",
        "split",
        "reopen",
        "external_acknowledge",
        "authorize",
        "context",
        "check",
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
    assert "resume" in INSTRUCTIONS


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
