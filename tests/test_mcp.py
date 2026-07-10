from tide.mcp import INSTRUCTIONS, tools


def test_mcp_exposes_small_quality_surface() -> None:
    names = {tool["name"] for tool in tools()}
    assert names == {
        "prepare",
        "revise",
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
    assert "Do not edit while mutation_allowed is false" in INSTRUCTIONS
    assert "The writer must not relay or rewrite reviewer findings" in INSTRUCTIONS
