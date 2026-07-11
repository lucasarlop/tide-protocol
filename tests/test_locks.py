from pathlib import Path

from tide.locks import matching_locks, parse_lock


def test_parse_and_match_lock(tmp_path: Path) -> None:
    root = tmp_path
    path = root / ".tide" / "locks" / "epub.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        '''+++
name = "epub"
paths = ["src/epub/**"]
criticality = "production"
review_required = true
validations = ["pytest tests/epub -x"]
invariants = ["valid epub"]
sensitive_changes = ["reading order"]
+++
# EPUB
''',
        encoding="utf-8",
    )
    lock = parse_lock(path)
    assert lock.name == "epub"
    assert lock.matches("src/epub/generator.py")
    assert not lock.matches("src/docx/generator.py")
    assert matching_locks(root, ["src/epub/generator.py"]) == [lock]


def test_broad_boundary_discovers_nested_lock(tmp_path: Path) -> None:
    root = tmp_path
    path = root / ".tide" / "locks" / "epub.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        '''+++
name = "epub"
paths = ["src/epub/**"]
criticality = "production"
review_required = true
validations = []
invariants = []
sensitive_changes = []
+++
# EPUB
''',
        encoding="utf-8",
    )
    assert matching_locks(root, ["src/**"])[0].name == "epub"
    assert matching_locks(root, ["tests/**"]) == []
