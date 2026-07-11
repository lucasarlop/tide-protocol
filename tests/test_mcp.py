from tide.mcp import INSTRUCTIONS, _tool_summary, tools


def test_mcp_exposes_small_quality_surface() -> None:
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
        "validation_log",
        "review_packet",
        "review_get",
        "review_submit",
        "handoff",
        "lock_list",
        "lock_template",
        "status",
    }
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in surface)
    assert "targeted validations" in INSTRUCTIONS
    assert "incremental by default" in INSTRUCTIONS
    assert "Only blocking findings stay in the current task" in INSTRUCTIONS
    assert "split_required" in INSTRUCTIONS
    assert "Use split" in INSTRUCTIONS
    assert "handoff" in INSTRUCTIONS


def test_mcp_validate_schema_exposes_coverage_and_phase() -> None:
    validate = next(tool for tool in tools() if tool["name"] == "validate")
    properties = validate["inputSchema"]["properties"]
    assert properties["phase"]["enum"] == ["targeted", "final"]
    assert "covers" in properties


def test_mcp_review_schema_supports_ids_severity_and_full_reason() -> None:
    submit = next(tool for tool in tools() if tool["name"] == "review_submit")
    finding = submit["inputSchema"]["properties"]["findings"]["items"]
    structured = finding["oneOf"][1]
    assert structured["properties"]["severity"]["enum"] == [
        "blocking",
        "follow_up",
        "info",
    ]
    assert "id" in structured["properties"]

    packet = next(tool for tool in tools() if tool["name"] == "review_packet")
    assert "full_reason" in packet["inputSchema"]["properties"]


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


def test_check_summary_exposes_primary_blocker_and_next_action() -> None:
    summary = _tool_summary(
        "check",
        {
            "ready": False,
            "primary_blocker": "hardgates not authorized",
            "pending_hardgates": ["closure_reopen"],
            "next_action": "authorize pending hardgates: closure_reopen",
            "follow_up_tasks": [],
        },
    )
    assert "hardgates not authorized" in summary
    assert "closure_reopen" in summary
    assert "authorize pending hardgates" in summary
