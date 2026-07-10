from tide.mcp import INSTRUCTIONS, _tool_summary, tools


def test_mcp_exposes_small_quality_surface() -> None:
    surface = tools()
    names = {tool["name"] for tool in surface}
    assert names == {
        "prepare",
        "revise",
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
        "lock_list",
        "lock_template",
        "status",
    }
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in surface)
    assert "Do not edit while mutation_allowed is false" in INSTRUCTIONS
    assert "The writer must not relay or rewrite reviewer findings" in INSTRUCTIONS
    assert "Do not absorb unrelated changed files" in INSTRUCTIONS


def test_mcp_text_summary_does_not_duplicate_structured_payload() -> None:
    value = {
        "command": ["pytest"],
        "passed": True,
        "exit_code": 0,
        "log_id": "validation-123",
        "stdout_tail": ["x" * 4_000],
    }
    summary = _tool_summary("validate", value)
    assert len(summary) < 200
    assert "stdout_tail" not in summary
    assert "validation-123" in summary
