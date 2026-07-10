from __future__ import annotations

import argparse
import json
import shutil
import sys

from . import __version__
from .context import graph_status, query_context
from .core import authorize, check, prepare, preparation_report, record_review, record_validation, review_packet
from .locks import load_locks, matching_locks, parse_lock, render_draft
from .mcp import serve
from .project import TideError, project_root, runtime_dir, save_runtime
from .setup_tools import setup_global


def emit(value: object, *, as_json: bool = False) -> None:
    if as_json or isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def cmd_doctor(args: argparse.Namespace) -> None:
    result: dict[str, object] = {"version": __version__, "python": sys.version.split()[0], "tide_command": shutil.which("tide")}
    try:
        root = project_root()
        result.update({"project": str(root), "runtime": str(runtime_dir(root)), "locks": len(load_locks(root)), "context": graph_status(root)})
    except TideError as exc:
        result["project"] = None
        result["project_warning"] = str(exc)
    emit(result, as_json=True)


def cmd_init(args: argparse.Namespace) -> None:
    root = project_root()
    directory = root / ".tide" / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    emit({"project": str(root), "locks": str(directory.relative_to(root))})


def cmd_prepare(args: argparse.Namespace) -> None:
    emit(prepare(project_root(), args.task, args.file or []), as_json=True)


def cmd_status(args: argparse.Namespace) -> None:
    emit(preparation_report(project_root()), as_json=True)


def cmd_context(args: argparse.Namespace) -> None:
    emit(query_context(project_root(), args.query), as_json=True)


def cmd_check(args: argparse.Namespace) -> None:
    report = check(project_root())
    emit(report, as_json=True)
    if not report["ready"]:
        raise SystemExit(2)


def cmd_validate(args: argparse.Namespace) -> None:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise TideError("provide a command after --")
    result = record_validation(project_root(), command, args.timeout)
    emit(result, as_json=True)
    if not result["passed"]:
        raise SystemExit(result["exit_code"] or 1)


def cmd_authorize(args: argparse.Namespace) -> None:
    emit(authorize(project_root(), args.gate or [], all_gates=args.all), as_json=True)


def cmd_review_packet(args: argparse.Namespace) -> None:
    emit(review_packet(project_root()), as_json=True)


def cmd_review(args: argparse.Namespace) -> None:
    findings = args.finding or []
    emit(record_review(project_root(), approved=args.approved, findings=findings), as_json=True)


def cmd_lock_list(args: argparse.Namespace) -> None:
    root = project_root()
    emit([{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required} for lock in load_locks(root)], as_json=True)


def cmd_lock_show(args: argparse.Namespace) -> None:
    root = project_root()
    locks = matching_locks(root, [args.target])
    if not locks:
        raise TideError(f"no Module Lock matches {args.target}")
    emit([{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "validations": list(lock.validations), "invariants": list(lock.invariants), "sensitive_changes": list(lock.sensitive_changes), "body": lock.body} for lock in locks], as_json=True)


def cmd_lock_draft(args: argparse.Namespace) -> None:
    root = project_root()
    target = root / ".tide" / "locks" / f"{args.name}.md"
    if target.exists() and not args.force:
        raise TideError(f"lock already exists: {target.relative_to(root)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_draft(name=args.name, scope=args.scope, criticality=args.criticality), encoding="utf-8")
    emit({"created": str(target.relative_to(root)), "status": "draft; analyze live code, fill invariants and validations, then run tide lock validate"})


def cmd_lock_validate(args: argparse.Namespace) -> None:
    root = project_root()
    path = (root / args.file).resolve()
    lock = parse_lock(path)
    emit({"valid": True, "name": lock.name, "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required}, as_json=True)


def cmd_reset(args: argparse.Namespace) -> None:
    root = project_root()
    save_runtime(root, {})
    emit({"reset": True})


def cmd_setup(args: argparse.Namespace) -> None:
    codex = args.codex or not (args.codex or args.opencode)
    opencode = args.opencode or not (args.codex or args.opencode)
    emit({"dry_run": args.dry_run, "actions": setup_global(codex=codex, opencode=opencode, dry_run=args.dry_run)}, as_json=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tide", description="Minimal quality protocol for AI coding agents")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    init = sub.add_parser("init")
    init.set_defaults(func=cmd_init)

    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("task")
    prepare_parser.add_argument("--file", action="append")
    prepare_parser.set_defaults(func=cmd_prepare)

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)

    authorize_parser = sub.add_parser("authorize")
    authorize_parser.add_argument("--gate", action="append")
    authorize_parser.add_argument("--all", action="store_true")
    authorize_parser.set_defaults(func=cmd_authorize)

    context = sub.add_parser("context")
    context.add_argument("query")
    context.set_defaults(func=cmd_context)

    check_parser = sub.add_parser("check")
    check_parser.set_defaults(func=cmd_check)

    validate = sub.add_parser("validate")
    validate.add_argument("--timeout", type=int, default=300)
    validate.add_argument("command", nargs=argparse.REMAINDER)
    validate.set_defaults(func=cmd_validate)

    review_packet_parser = sub.add_parser("review-packet")
    review_packet_parser.set_defaults(func=cmd_review_packet)

    review = sub.add_parser("review")
    verdict = review.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--approved", action="store_true")
    verdict.add_argument("--blocked", dest="approved", action="store_false")
    review.add_argument("--finding", action="append")
    review.set_defaults(func=cmd_review)

    lock = sub.add_parser("lock")
    lock_sub = lock.add_subparsers(dest="lock_command", required=True)
    lock_list = lock_sub.add_parser("list")
    lock_list.set_defaults(func=cmd_lock_list)
    lock_show = lock_sub.add_parser("show")
    lock_show.add_argument("target")
    lock_show.set_defaults(func=cmd_lock_show)
    lock_draft = lock_sub.add_parser("draft")
    lock_draft.add_argument("scope")
    lock_draft.add_argument("--name", required=True)
    lock_draft.add_argument("--criticality", default="production")
    lock_draft.add_argument("--force", action="store_true")
    lock_draft.set_defaults(func=cmd_lock_draft)
    lock_validate = lock_sub.add_parser("validate")
    lock_validate.add_argument("file")
    lock_validate.set_defaults(func=cmd_lock_validate)

    reset = sub.add_parser("reset")
    reset.set_defaults(func=cmd_reset)

    setup = sub.add_parser("setup")
    setup.add_argument("--codex", action="store_true")
    setup.add_argument("--opencode", action="store_true")
    setup.add_argument("--dry-run", action="store_true")
    setup.set_defaults(func=cmd_setup)

    mcp = sub.add_parser("mcp")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser("serve")
    mcp_serve.set_defaults(func=lambda args: raise_exit(serve()))
    return parser


def raise_exit(code: int) -> None:
    raise SystemExit(code)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except TideError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
