from __future__ import annotations

import sys
from pathlib import Path

from tide.core import check, prepare, record_validation
from tide.locks import matching_locks, parse_lock
from tide.model_policy import model_policy


def test_balanced_ordinary_work_uses_terra_medium(repo: Path) -> None:
    prepare(repo, "change helper", ["app.py"])
    policy = model_policy(repo, phase="implementation")
    assert policy["recommendation"]["preset"] == "terra_medium"


def test_sensitive_implementation_uses_sol_medium(repo: Path) -> None:
    prepare(repo, "change auth", ["src/auth/service.py"])
    policy = model_policy(repo, phase="implementation")
    assert policy["recommendation"]["preset"] == "sol_medium"


def test_unknown_root_cause_after_two_failures_allows_xhigh(repo: Path) -> None:
    prepare(repo, "hard issue", ["app.py"])
    policy = model_policy(repo, phase="investigation", failed_attempts=2, root_cause_known=False)
    assert policy["recommendation"]["preset"] == "sol_xhigh"


def test_incremental_and_critical_reviewers(repo: Path) -> None:
    prepare(repo, "ordinary", ["app.py"])
    ordinary = model_policy(repo, phase="review", review_mode="incremental")
    assert ordinary["reviewer_agent"] == "tide-reviewer"


def test_module_lock_requires_validation_and_critical_review(repo: Path) -> None:
    lock_path = repo / ".tide" / "locks" / "app.md"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        '''+++\nname = "app"\npaths = ["app.py"]\ncriticality = "production"\nreview_required = true\nvalidations = ["python -c 'assert True'"]\ninvariants = ["VALUE remains numeric"]\nsensitive_changes = []\n+++\n# App\n''',
        encoding="utf-8",
    )
    import subprocess
    subprocess.run(["git", "add", ".tide/locks/app.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "lock"], cwd=repo, check=True, capture_output=True)
    lock = parse_lock(lock_path)
    assert lock.name == "app"
    assert matching_locks(repo, ["app.py"])[0].name == "app"
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"])
    report = check(repo)
    assert report["review_level"] == "critical"
    assert report["missing_required_validations"] == ["python -c 'assert True'"]
