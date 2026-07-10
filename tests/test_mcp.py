from tide.mcp import INSTRUCTIONS, tools


def test_mcp_exposes_small_quality_surface() -> None:
    names = {tool["name"] for tool in tools()}
    assert names == {
        "prepare",
        "authorize",
        "context",
        "check",
        "validate",
        "review_packet",
        "record_review",
        "lock_list",
        "lock_template",
        "status",
    }
    assert "Do not edit while mutation_allowed is false" in INSTRUCTIONS
