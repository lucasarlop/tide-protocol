from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TIDE = ROOT / "bin" / "tide"


class TideCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cmd(["git", "init"])
        self.cmd(["git", "config", "user.email", "test@example.com"])
        self.cmd(["git", "config", "user.name", "Tide Test"])
        (self.root / "README.md").write_text("hello\n", encoding="utf-8")
        self.cmd(["git", "add", "README.md"])
        self.cmd(["git", "commit", "-m", "init"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cmd(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        result = subprocess.run(args, cwd=self.root, text=True, capture_output=True, env=env)
        if check and result.returncode != 0:
            raise AssertionError(f"command failed: {args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def tide(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.cmd(["python3", str(TIDE), *args], check=check)

    def test_wave_create_park_approve(self) -> None:
        self.tide(["init"])
        wave_id = self.tide(["wave", "create", "--title", "Add file", "--risk", "low"]).stdout.strip()

        (self.root / "foo.txt").write_text("x\n", encoding="utf-8")
        self.tide(["wave", "park", wave_id])
        listing = self.tide(["wave", "list"]).stdout

        self.assertIn(wave_id, listing)
        self.assertIn("parked", listing)

        approved = self.tide(["approve", wave_id]).stdout
        self.assertIn("commit criado", approved)

        log = self.cmd(["git", "log", "-1", "--pretty=%B"]).stdout
        self.assertIn(wave_id, log)

    def test_wave_reject_reverts_patch(self) -> None:
        self.tide(["init"])
        wave_id = self.tide(["wave", "create", "--title", "Change README"]).stdout.strip()

        (self.root / "README.md").write_text("changed\n", encoding="utf-8")
        self.tide(["wave", "park", wave_id])
        self.tide(["reject", wave_id])

        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "hello\n")

    def test_project_catalog_and_run(self) -> None:
        catalog = {
            "commands": {
                "echo_case": {
                    "description": "Echo case",
                    "command": "echo {case_id}",
                    "safety": "read",
                    "requires_ok": False,
                    "timeout": {"hard_sec": 5, "silence_sec": 2},
                    "args": {"case_id": {"required": True, "description": "case"}},
                }
            }
        }
        (self.root / ".tide.commands.json").write_text(json.dumps(catalog), encoding="utf-8")

        commands = self.tide(["project", "commands"]).stdout
        self.assertIn("echo_case", commands)

        detail = self.tide(["project", "command", "echo_case"]).stdout
        self.assertIn("Echo case", detail)

        run = self.tide(["project", "run", "echo_case", "--arg", "case_id=123"]).stdout
        self.assertIn("123", run)

    def test_sensitive_project_run_requires_yes(self) -> None:
        catalog = {
            "commands": {
                "mutate": {
                    "description": "Mutating command",
                    "command": "echo mutate",
                    "safety": "mutating",
                    "requires_ok": True,
                    "timeout": {"hard_sec": 5, "silence_sec": 2},
                }
            }
        }
        (self.root / ".tide.commands.json").write_text(json.dumps(catalog), encoding="utf-8")

        result = self.tide(["project", "run", "mutate"], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OK explícito", result.stderr)

        dry_run = self.tide(["project", "run", "mutate", "--dry-run"]).stdout
        self.assertIn("dry-run", dry_run)

    def test_run_timeout_returns_125_for_silence_guard(self) -> None:
        result = self.tide(["run", "--timeout-sec", "1", "--silence-sec", "1", "--", "bash", "-lc", "sleep 2"], check=False)
        self.assertEqual(result.returncode, 125)
        self.assertIn("inconclusiva", result.stderr)


if __name__ == "__main__":
    unittest.main()
