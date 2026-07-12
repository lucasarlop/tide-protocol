from __future__ import annotations

from . import mcp

_AUTONOMY_INSTRUCTIONS = """
Validation, review, blocker correction, and local operational verification are autonomous work. Never end a turn merely because one of them remains.
When a Tide result contains authorization_request, call authorize with exactly those gates. The client permission prompt is the user interaction; do not replace it with a vague prose request.
Only stop for user input when user_action_required=true, the user denies the permission prompt, a genuine requirement choice remains, or an external dependency makes progress impossible.
When agent_should_continue=true, continue to the exact next_action before producing a final response.
""".strip()


def install() -> None:
    if _AUTONOMY_INSTRUCTIONS not in mcp.INSTRUCTIONS:
        mcp.INSTRUCTIONS = mcp.INSTRUCTIONS.rstrip() + "\n" + _AUTONOMY_INSTRUCTIONS
