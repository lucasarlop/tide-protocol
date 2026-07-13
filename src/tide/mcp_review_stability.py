from __future__ import annotations

from typing import Any

from . import mcp
from .artifacts import read_review_packet
from .project import TideError, project_root

_ORIGINAL_CALL_TOOL = mcp.call_tool


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    try:
        value = _ORIGINAL_CALL_TOOL(name, arguments)
        if name == "review_submit" and isinstance(value, dict):
            return {
                **value,
                "verdict_submitted": True,
                "idempotent": False,
            }
        return value
    except TideError as exc:
        if name != "review_submit" or "already has a submitted verdict" not in str(exc):
            raise
        packet = read_review_packet(project_root(), str(arguments.get("review_id") or ""))
        submission = packet.get("submission")
        if not isinstance(submission, dict):
            raise
        return {
            **submission,
            "verdict_submitted": True,
            "idempotent": True,
        }


def install() -> None:
    mcp.call_tool = call_tool
