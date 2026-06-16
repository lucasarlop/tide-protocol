"""Safe Tide MCP server skeleton.

This module intentionally exposes context and planning only. Execution remains in the Tide CLI and OpenCode commands, under explicit supervisor control.
"""

VERSION = "0.4.0"

TOOLS = [
    "tide_project_profile",
    "tide_wave_list",
    "tide_wave_show",
    "tide_commands_list",
    "tide_command_plan",
    "tide_context_status",
]


def describe():
    return {
        "name": "tide",
        "version": VERSION,
        "tools": TOOLS,
        "safety": "context-and-planning-only",
    }
