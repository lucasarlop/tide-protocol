from pathlib import Path

from tide.commands import run_validation


def test_missing_validation_command_is_recorded_as_failure(tmp_path: Path) -> None:
    result = run_validation(tmp_path, ["definitely-not-a-real-command"])
    assert not result["passed"]
    assert result["exit_code"] == 127
    assert result["stderr"]
