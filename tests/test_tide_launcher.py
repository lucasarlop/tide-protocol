from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TideLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.bin = self.root / "bin"
        self.config = self.root / "opencode-tide"
        self.bin.mkdir()

        self.cmd(["git", "init"], cwd=self.repo)
        self.cmd(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        self.cmd(["git", "config", "user.name", "Tide Test"], cwd=self.repo)
        (self.repo / "README.md").write_text("hello\n", encoding="utf-8")
        self.cmd(["git", "add", "README.md"], cwd=self.repo)
        self.cmd(["git", "commit", "-m", "init"], cwd=self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cmd(self, args: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(args, cwd=cwd or self.root, text=True, capture_output=True, env=env)
        if check and result.returncode != 0:
            raise AssertionError(f"command failed: {args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def install(self) -> None:
        self.cmd([
            "bash",
            str(ROOT / "install.sh"),
            "--force",
            f"--config-dir={self.config}",
            f"--bin-dir={self.bin}",
        ], cwd=ROOT)

    def env_with_fake_opencode(self) -> dict[str, str]:
        fake_opencode = self.bin / "opencode"
        marker = self.root / "opencode-env.txt"
        fake_opencode.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s' \"$OPENCODE_CONFIG_DIR\" > {marker}\n",
            encoding="utf-8",
        )
        fake_opencode.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env.get('PATH', '')}"
        return env

    def test_launcher_delegates_regular_tide_commands(self) -> None:
        self.install()
        tide = self.bin / "tide"
        result = self.cmd([str(tide), "--version"], cwd=self.repo)
        self.assertEqual(result.stdout.strip(), "0.5.0")

    def test_launcher_opencode_uses_isolated_config_and_runs_init(self) -> None:
        self.install()
        env = self.env_with_fake_opencode()
        marker = self.root / "opencode-env.txt"
        tide = self.bin / "tide"
        self.cmd([str(tide), "opencode"], cwd=self.repo, env=env)

        self.assertEqual(marker.read_text(encoding="utf-8"), str(self.config))
        self.assertTrue((self.repo / ".opencode" / "waves" / "registry.json").exists())

    def test_launcher_doctor_reports_ok_when_installed(self) -> None:
        self.install()
        env = self.env_with_fake_opencode()
        tide = self.bin / "tide"
        self.cmd([str(tide), "init"], cwd=self.repo)

        result = self.cmd([str(tide), "doctor"], cwd=self.repo, env=env)

        self.assertIn("Tide Doctor", result.stdout)
        self.assertIn("Doctor: ok", result.stdout)
        self.assertIn(str(self.config), result.stdout)


if __name__ == "__main__":
    unittest.main()
