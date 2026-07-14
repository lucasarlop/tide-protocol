from __future__ import annotations

import json
from pathlib import Path

import pytest

from tide.core import abandon, check, prepare, resume
from tide.project import TideError, load_runtime, runtime_path, save_runtime
from tide.state import SCHEMA_VERSION


def test_resume_without_task_is_safe_and_actionable(repo: Path) -> None:
    report = resume(repo)
    assert report["active"] is False
    assert report["lifecycle"] == "idle"
    assert report["next_action"].startswith("prepare")
    assert report["agent_should_continue"] is True


def test_prepare_creates_versioned_state_and_resume_is_compact(repo: Path) -> None:
    prepare(repo, "change helper", ["app.py"])
    state = load_runtime(repo)
    resumed = resume(repo)
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["task"] == "change helper"
    assert resumed["task"] == "change helper"
    assert resumed["boundary"] == ["app.py"]
    assert "validations" not in resumed


def test_prepare_does_not_replace_active_task(repo: Path) -> None:
    prepare(repo, "first task", ["app.py"])
    with pytest.raises(TideError, match="another Tide task is active"):
        prepare(repo, "second task", ["helper.py"])


def test_prepare_same_task_is_idempotent(repo: Path) -> None:
    prepare(repo, "same task", ["app.py"])
    result = prepare(repo, "same task", ["app.py"])
    assert result["reused"] is True


def test_abandon_allows_new_task_and_archives_previous(repo: Path) -> None:
    prepare(repo, "first task", ["app.py"])
    abandon(repo, reason="user changed priority")
    prepare(repo, "second task", ["helper.py"])
    state = load_runtime(repo)
    assert state["task"] == "second task"
    assert state["archive"][-1]["task"] == "first task"
    assert state["archive"][-1]["outcome"] == "abandoned"


def test_corrupted_runtime_fails_explicitly(repo: Path) -> None:
    runtime_path(repo).write_text("{not-json", encoding="utf-8")
    with pytest.raises(TideError, match="invalid JSON"):
        load_runtime(repo)


def test_legacy_state_is_migrated(repo: Path) -> None:
    path = runtime_path(repo)
    path.write_text(
        json.dumps(
            {
                "version": 3,
                "task": "legacy task",
                "status": "revising",
                "boundary": ["app.py"],
                "validations": [],
            }
        ),
        encoding="utf-8",
    )
    state = load_runtime(repo)
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["lifecycle"] == "active"
    assert state["task_id"].startswith("task-")


def test_atomic_save_leaves_no_temporary_file(repo: Path) -> None:
    prepare(repo, "atomic", ["app.py"])
    state = load_runtime(repo)
    state["revision"] = 2
    save_runtime(repo, state)
    assert not runtime_path(repo).with_name("current.json.tmp").exists()
    assert check(repo)["task"] == "atomic"
