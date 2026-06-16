from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MCP = ROOT / "mcp" / "tide_mcp.py"


class TideMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("tide_mcp", MCP)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_tools_are_context_safe(self) -> None:
        names = {tool["name"] for tool in self.module.tools()}
        self.assertIn("tide_project_profile", names)
        self.assertIn("tide_wave_list", names)
        self.assertIn("tide_commands_list", names)
        self.assertIn("tide_command_plan", names)
        self.assertNotIn("tide_command_execute", names)

    def test_describes_project_profile(self) -> None:
        profile = self.module.project_profile()
        self.assertIn("root", profile)
        self.assertIn("code_review_graph_available", profile)

    def test_command_plan_does_not_run(self) -> None:
        is_error, text = self.module.call_tool("tide_command_plan", {"name": "example", "args": {"id": "123"}})
        self.assertFalse(is_error)
        self.assertIn("tide project run example", text)


if __name__ == "__main__":
    unittest.main()
