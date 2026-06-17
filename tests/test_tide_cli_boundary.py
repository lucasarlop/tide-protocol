from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TIDE = ROOT / "bin" / "tide"


class TideCliBoundaryTests(unittest.TestCase):
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

    def test_finish_with_file_blocks_dirty_file_outside_boundary(self) -> None:
        self.tide(["init"])
        wave_id = self.tide(["wave", "create", "--title", "Bounded change", "--risk", "low"]).stdout.strip()
        (self.root / "foo.txt").write_text("x\n", encoding="utf-8")
        (self.root / "outside.txt").write_text("outside\n", encoding="utf-8")

        result = self.tide([
            "wave", "finish", wave_id,
            "--file", "foo.txt",
            "--summary", "validated",
            "--command", "tide run -- echo ok",
        ], check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fora da fronteira", result.stderr)
        self.assertIn("outside.txt", result.stderr)
        self.assertEqual(self.tide(["wave", "status", wave_id]).stdout.strip(), "running")

    def test_finish_with_file_and_override_snapshots_only_boundary(self) -> None:
        self.tide(["init"])
        wave_id = self.tide(["wave", "create", "--title", "Bounded change", "--risk", "low"]).stdout.strip()
        (self.root / "foo.txt").write_text("x\n", encoding="utf-8")
        (self.root / "outside.txt").write_text("outside\n", encoding="utf-8")

        self.tide([
            "wave", "finish", wave_id,
            "--file", "foo.txt",
            "--allow-outside-boundary",
            "--summary", "validated",
            "--command", "tide run -- echo ok",
        ])

        files = self.tide(["wave", "files", wave_id]).stdout.splitlines()
        self.assertEqual(files, ["foo.txt"])
        approved = self.tide(["approve", wave_id]).stdout
        self.assertIn("commit criado", approved)
        self.assertIn("Working tree: há mudanças não commitadas", approved)
        self.assertIn("?? outside.txt", self.cmd(["git", "status", "--short"]).stdout)

    def test_finish_uses_wave_allowed_as_boundary(self) -> None:
        self.tide(["init"])
        wave_id = self.tide([
            "wave", "create",
            "--title", "Allowed file",
            "--risk", "low",
            "--allow", "foo.txt",
        ]).stdout.strip()
        (self.root / "foo.txt").write_text("x\n", encoding="utf-8")

        self.tide(["wave", "finish", wave_id, "--summary", "validated", "--command", "tide run -- echo ok"])

        files = self.tide(["wave", "files", wave_id]).stdout.splitlines()
        self.assertEqual(files, ["foo.txt"])
        wave = json.loads(self.tide(["wave", "show", wave_id, "--json"]).stdout)
        self.assertEqual(wave.get("boundary_source"), "wave.allowed")

    def test_stacked_wave_without_boundary_blocks_finish(self) -> None:
        self.tide(["init"])
        (self.root / "preexisting.txt").write_text("dirty before wave\n", encoding="utf-8")
        wave_id = self.tide(["wave", "create", "--title", "Stacked", "--risk", "low"]).stdout.strip()
        (self.root / "foo.txt").write_text("x\n", encoding="utf-8")

        result = self.tide(["wave", "finish", wave_id, "--summary", "validated", "--command", "tide run -- echo ok"], check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("working tree sujo", result.stderr)
        self.assertIn("--file", result.stderr)


if __name__ == "__main__":
    unittest.main()
