from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .core import (
    abandon,
    authorize,
    check,
    commit_check,
    create_review_packet,
    get_review_packet,
    prepare,
    preparation_report,
    record_review,
    record_validation,
    resume,
    revise,
    start_validation,
    validation_log,
    validation_status,
)
from .lifecycle import detect_adapters, uninstall_tool, update_tool
from .locks import load_locks, matching_locks, parse_lock, render_draft
from .mcp import serve
from .output import emit
from .project import TideError, project_root, runtime_dir, save_runtime
from .setup_tools import setup_global


def out(args: argparse.Namespace, value: object, *, title: str | None = None) -> None:
    emit(value, as_json=bool(getattr(args, "json", False)), title=title)


def cmd_doctor(args: argparse.Namespace) -> None:
    result: dict[str, object] = {
        "version": __version__,
        "python": sys.version.split()[0],
        "tide_command": shutil.which("tide"),
    }
    try:
        root = project_root()
        result.update({"project": str(root), "runtime": str(runtime_dir(root)), "locks": len(load_locks(root))})
    except TideError as exc:
        result["project"] = None
        result["project_warning"] = str(exc)
    out(args, result, title="Tide doctor")


def cmd_resume(args: argparse.Namespace) -> None:
    out(args, resume(project_root()), title="Tide resume")


def cmd_status(args: argparse.Namespace) -> None:
    out(args, preparation_report(project_root()), title="Tide status")


def cmd_check(args: argparse.Namespace) -> None:
    report = check(project_root())
    out(args, report, title="Tide ready" if report.get("ready") else "Tide blocked")
    if not report.get("ready"):
        raise SystemExit(2)


def cmd_commit_check(args: argparse.Namespace) -> None:
    report = commit_check(project_root())
    out(args, report, title="Commit allowed" if report.get("allowed") else "Commit blocked")
    if not report.get("allowed"):
        raise SystemExit(2)


def cmd_setup(args: argparse.Namespace) -> None:
    codex = args.codex or not (args.codex or args.opencode)
    opencode = args.opencode or not (args.codex or args.opencode)
    out(args, {"dry_run": args.dry_run, "actions": setup_global(codex=codex, opencode=opencode, dry_run=args.dry_run)}, title="Tide setup")


def cmd_update(args: argparse.Namespace) -> None:
    out(args, update_tool(dry_run=args.dry_run), title="Tide update")


def cmd_uninstall(args: argparse.Namespace) -> None:
    installed = detect_adapters()
    explicit = args.codex or args.opencode
    codex = args.codex if explicit else installed["codex"]
    opencode = args.opencode if explicit else installed["opencode"]
    remaining = {"codex": installed["codex"] and not codex, "opencode": installed["opencode"] and not opencode}
    remove_shared = not any(remaining.values())
    remove_package = not args.keep_tool and remove_shared
    if not args.yes and not args.dry_run:
        preview = uninstall_tool(codex=codex, opencode=opencode, dry_run=True, remove_package=remove_package, remove_shared=remove_shared)
        out(args, preview, title="Uninstall plan")
        raise TideError("repeat with --yes to uninstall")
    out(args, uninstall_tool(codex=codex, opencode=opencode, dry_run=args.dry_run, remove_package=remove_package, remove_shared=remove_shared), title="Tide uninstall")


def cmd_lock_list(args: argparse.Namespace) -> None:
    root = project_root()
    out(args, [{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required} for lock in load_locks(root)], title="Module Locks")


def cmd_lock_show(args: argparse.Namespace) -> None:
    root = project_root()
    locks = matching_locks(root, [args.target])
    if not locks:
        raise TideError(f"no Module Lock matches {args.target}")
    out(args, [{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "validations": list(lock.validations), "invariants": list(lock.invariants), "sensitive_changes": list(lock.sensitive_changes), "body": lock.body} for lock in locks], title="Module Lock")


def cmd_lock_draft(args: argparse.Namespace) -> None:
    root = project_root()
    target = root / ".tide" / "locks" / f"{args.name}.md"
    if target.exists() and not args.force:
        raise TideError(f"lock already exists: {target.relative_to(root)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_draft(name=args.name, scope=args.scope, criticality=args.criticality), encoding="utf-8")
    out(args, {"created": str(target.relative_to(root)), "status": "draft"}, title="Module Lock created")


def cmd_lock_validate(args: argparse.Namespace) -> None:
    root = project_root()
    lock = parse_lock((root / args.file).resolve())
    out(args, {"valid": True, "name": lock.name, "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required}, title="Module Lock valid")


def cmd_prepare(args: argparse.Namespace) -> None:
    out(args, prepare(project_root(), args.task, args.file or [], required_validations=args.require_validation or []), title="Tide prepared")


def cmd_revise(args: argparse.Namespace) -> None:
    out(args, revise(project_root(), task=args.task, add_files=args.add_file or [], remove_files=args.remove_file or [], add_required_validations=args.add_required_validation or [], remove_required_validations=args.remove_required_validation or []), title="Tide revised")


def cmd_validate(args: argparse.Namespace) -> None:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise TideError("provide a command after --")
    root = project_root()
    if args.background:
        out(args, start_validation(root, command, args.timeout), title="Validation started")
        return
    result = record_validation(root, command, args.timeout)
    out(args, result, title="Validation")
    if not result.get("passed"):
        raise SystemExit(int(result.get("exit_code") or 1))


def cmd_authorize(args: argparse.Namespace) -> None:
    out(args, authorize(project_root(), args.gate or [], all_gates=args.all), title="Authorization updated")


def cmd_review_packet(args: argparse.Namespace) -> None:
    out(args, create_review_packet(project_root()), title="Review packet")


def cmd_review_show(args: argparse.Namespace) -> None:
    out(args, get_review_packet(project_root(), args.review_id), title="Review packet")


def cmd_review(args: argparse.Namespace) -> None:
    out(args, record_review(project_root(), approved=args.approved, findings=args.finding or [], review_id=args.review_id), title="Manual review")


def cmd_abandon(args: argparse.Namespace) -> None:
    out(args, abandon(project_root(), reason=args.reason), title="Task abandoned")


def cmd_reset(args: argparse.Namespace) -> None:
    if not args.yes:
        raise TideError("recover reset discards the active runtime; repeat with --yes")
    save_runtime(project_root(), {})
    out(args, {"reset": True}, title="Runtime reset")



def _simple_help() -> str:
    return """Tide — reliable quality protocol for coding agents

Daily commands:
  tide resume       Show the current task checkpoint
  tide status       Show current task state
  tide check        Verify whether the task is ready
  tide setup        Configure Codex and OpenCode
  tide doctor       Diagnose installation and project state
  tide update       Update Tide and refresh adapters
  tide lock --help  Manage Module Locks

The agent calls resume and the internal workflow tools automatically.
Use `tide help --all` for recovery and internal commands.
"""

def build_parser(*, advanced: bool = False) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tide",
        description="Reliable quality protocol for autonomous coding agents",
        epilog="Agents use internal MCP tools automatically. Start a coding session normally; Tide resume is called by the agent.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command")

    for name, func, help_text in [
        ("resume", cmd_resume, "Show the current task checkpoint"),
        ("status", cmd_status, "Show current task state"),
        ("check", cmd_check, "Verify whether the task is ready"),
        ("doctor", cmd_doctor, "Diagnose installation and project state"),
    ]:
        command = sub.add_parser(name, help=help_text)
        command.set_defaults(func=func)

    setup = sub.add_parser("setup", help="Configure Codex and OpenCode")
    setup.add_argument("--codex", action="store_true")
    setup.add_argument("--opencode", action="store_true")
    setup.add_argument("--dry-run", action="store_true")
    setup.set_defaults(func=cmd_setup)

    update = sub.add_parser("update", help="Update Tide and refresh adapters")
    update.add_argument("--dry-run", action="store_true")
    update.set_defaults(func=cmd_update)

    lock = sub.add_parser("lock", help="Manage Module Locks")
    lock_sub = lock.add_subparsers(dest="lock_command", required=True)
    lock_list = lock_sub.add_parser("list", help="List locks")
    lock_list.set_defaults(func=cmd_lock_list)
    lock_show = lock_sub.add_parser("show", help="Show matching lock")
    lock_show.add_argument("target")
    lock_show.set_defaults(func=cmd_lock_show)
    lock_draft = lock_sub.add_parser("draft", help="Create a lock draft")
    lock_draft.add_argument("scope")
    lock_draft.add_argument("--name", required=True)
    lock_draft.add_argument("--criticality", default="production")
    lock_draft.add_argument("--force", action="store_true")
    lock_draft.set_defaults(func=cmd_lock_draft)
    lock_validate = lock_sub.add_parser("validate", help="Validate a lock file")
    lock_validate.add_argument("file")
    lock_validate.set_defaults(func=cmd_lock_validate)

    uninstall = sub.add_parser("uninstall", help="Remove Tide integrations")
    uninstall.add_argument("--codex", action="store_true")
    uninstall.add_argument("--opencode", action="store_true")
    uninstall.add_argument("--keep-tool", action="store_true")
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--yes", action="store_true")
    uninstall.set_defaults(func=cmd_uninstall)

    hidden = None if advanced else argparse.SUPPRESS
    prepare_parser = sub.add_parser("prepare", help=hidden)
    prepare_parser.add_argument("task")
    prepare_parser.add_argument("--file", action="append")
    prepare_parser.add_argument("--require-validation", action="append")
    prepare_parser.set_defaults(func=cmd_prepare)
    revise_parser = sub.add_parser("revise", help=hidden)
    revise_parser.add_argument("--task")
    revise_parser.add_argument("--add-file", action="append")
    revise_parser.add_argument("--remove-file", action="append")
    revise_parser.add_argument("--add-required-validation", action="append")
    revise_parser.add_argument("--remove-required-validation", action="append")
    revise_parser.set_defaults(func=cmd_revise)
    validate = sub.add_parser("validate", help=hidden)
    validate.add_argument("--timeout", type=int, default=300)
    validate.add_argument("--background", action="store_true")
    validate.add_argument("command", nargs=argparse.REMAINDER)
    validate.set_defaults(func=cmd_validate)
    authorize_parser = sub.add_parser("authorize", help=hidden)
    authorize_parser.add_argument("--gate", action="append")
    authorize_parser.add_argument("--all", action="store_true")
    authorize_parser.set_defaults(func=cmd_authorize)
    review_packet_parser = sub.add_parser("review-packet", help=hidden)
    review_packet_parser.set_defaults(func=cmd_review_packet)
    review_show = sub.add_parser("review-show", help=hidden)
    review_show.add_argument("review_id")
    review_show.set_defaults(func=cmd_review_show)
    review = sub.add_parser("review", help=hidden)
    verdict = review.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--approved", action="store_true")
    verdict.add_argument("--blocked", dest="approved", action="store_false")
    review.add_argument("--review-id")
    review.add_argument("--finding", action="append")
    review.set_defaults(func=cmd_review)
    abandon_parser = sub.add_parser("abandon", help=hidden)
    abandon_parser.add_argument("reason")
    abandon_parser.set_defaults(func=cmd_abandon)
    commit_parser = sub.add_parser("commit-check", help=hidden)
    commit_parser.add_argument("--hook", action="store_true")
    commit_parser.set_defaults(func=cmd_commit_check)
    recover = sub.add_parser("recover", help=hidden)
    recover_sub = recover.add_subparsers(dest="recover_command", required=True)
    reset = recover_sub.add_parser("reset")
    reset.add_argument("--yes", action="store_true")
    reset.set_defaults(func=cmd_reset)
    mcp = sub.add_parser("mcp", help=hidden)
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser("serve")
    mcp_serve.set_defaults(func=lambda args: raise_exit(serve()))
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    advanced = "--all" in raw
    raw = [item for item in raw if item != "--all"]
    if raw and raw[0] == "help":
        if len(raw) == 1 and not advanced:
            print(_simple_help())
            return 0
        raw = ["--help", *raw[1:]] if len(raw) == 1 else [raw[1], "--help", *raw[2:]]
    parser = build_parser(advanced=advanced)
    if not raw:
        print(_simple_help() if not advanced else parser.format_help())
        return 0
    as_json = "--json" in raw
    raw = [item for item in raw if item != "--json"]
    try:
        args = parser.parse_args(raw)
        args.json = as_json
        if not hasattr(args, "func"):
            parser.print_help()
            return 0
        args.func(args)
    except TideError as exc:
        if as_json:
            emit({"error": str(exc)}, as_json=True)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def raise_exit(code: int) -> None:
    raise SystemExit(code)


if __name__ == "__main__":
    raise SystemExit(main())
