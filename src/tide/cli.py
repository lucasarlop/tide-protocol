from __future__ import annotations

import argparse
import shutil
import sys

from . import __version__
from .context import graph_status, query_context
from .core import (
    authorize,
    check,
    create_review_packet,
    get_review_packet,
    prepare,
    preparation_report,
    record_review,
    record_validation,
    revise,
    validation_log,
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
        result.update(
            {
                "project": str(root),
                "runtime": str(runtime_dir(root)),
                "locks": len(load_locks(root)),
                "context": graph_status(root),
            }
        )
    except TideError as exc:
        result["project"] = None
        result["project_warning"] = str(exc)
    out(args, result, title="Tide doctor")


def cmd_init(args: argparse.Namespace) -> None:
    root = project_root()
    directory = root / ".tide" / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    out(args, {"project": str(root), "locks": str(directory.relative_to(root))}, title="Projeto inicializado")


def cmd_prepare(args: argparse.Namespace) -> None:
    out(args, prepare(project_root(), args.task, args.file or []), title="Tide preparado")


def cmd_revise(args: argparse.Namespace) -> None:
    out(
        args,
        revise(
            project_root(),
            task=args.task,
            add_files=args.add_file or [],
            remove_files=args.remove_file or [],
        ),
        title="Tide revisado",
    )


def cmd_boundary(args: argparse.Namespace) -> None:
    add_files = args.file if args.boundary_action == "add" else []
    remove_files = args.file if args.boundary_action == "remove" else []
    out(
        args,
        revise(project_root(), add_files=add_files, remove_files=remove_files),
        title="Fronteira revisada",
    )


def cmd_status(args: argparse.Namespace) -> None:
    out(args, preparation_report(project_root()), title="Estado atual")


def cmd_context(args: argparse.Namespace) -> None:
    out(args, query_context(project_root(), args.query), title="Contexto")


def cmd_check(args: argparse.Namespace) -> None:
    report = check(project_root())
    title = "Quality gate: pronto" if report["ready"] else "Quality gate: bloqueado"
    out(args, report, title=title)
    if not report["ready"]:
        raise SystemExit(2)


def cmd_validate(args: argparse.Namespace) -> None:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise TideError("provide a command after --")
    root = project_root()
    result = record_validation(root, command, args.timeout)
    value: object = result
    if args.verbose:
        value = {**result, "full_log": validation_log(root, str(result["log_id"]))["content"]}
    out(args, value, title="Validação")
    if not result["passed"]:
        raise SystemExit(result["exit_code"] or 1)


def cmd_validation_log(args: argparse.Namespace) -> None:
    out(args, validation_log(project_root(), args.log_id), title="Log de validação")


def cmd_authorize(args: argparse.Namespace) -> None:
    out(args, authorize(project_root(), args.gate or [], all_gates=args.all), title="Hardgates atualizados")


def cmd_review_packet(args: argparse.Namespace) -> None:
    out(args, create_review_packet(project_root()), title="Pacote de review criado")


def cmd_review_show(args: argparse.Namespace) -> None:
    out(args, get_review_packet(project_root(), args.review_id), title="Pacote de review")


def cmd_review(args: argparse.Namespace) -> None:
    out(
        args,
        record_review(
            project_root(),
            approved=args.approved,
            findings=args.finding or [],
            review_id=args.review_id,
        ),
        title="Review registrada",
    )


def cmd_lock_list(args: argparse.Namespace) -> None:
    root = project_root()
    result = [
        {
            "name": lock.name,
            "file": str(lock.file.relative_to(root)),
            "paths": list(lock.paths),
            "criticality": lock.criticality,
            "review_required": lock.review_required,
        }
        for lock in load_locks(root)
    ]
    out(args, result, title="Module Locks")


def cmd_lock_show(args: argparse.Namespace) -> None:
    root = project_root()
    locks = matching_locks(root, [args.target])
    if not locks:
        raise TideError(f"no Module Lock matches {args.target}")
    result = [
        {
            "name": lock.name,
            "file": str(lock.file.relative_to(root)),
            "paths": list(lock.paths),
            "criticality": lock.criticality,
            "validations": list(lock.validations),
            "invariants": list(lock.invariants),
            "sensitive_changes": list(lock.sensitive_changes),
            "body": lock.body,
        }
        for lock in locks
    ]
    out(args, result, title="Module Lock")


def cmd_lock_draft(args: argparse.Namespace) -> None:
    root = project_root()
    target = root / ".tide" / "locks" / f"{args.name}.md"
    if target.exists() and not args.force:
        raise TideError(f"lock already exists: {target.relative_to(root)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_draft(name=args.name, scope=args.scope, criticality=args.criticality), encoding="utf-8")
    out(
        args,
        {
            "created": str(target.relative_to(root)),
            "status": "draft; analyze live code, fill invariants and validations, then run tide lock validate",
        },
        title="Module Lock criado",
    )


def cmd_lock_validate(args: argparse.Namespace) -> None:
    root = project_root()
    lock = parse_lock((root / args.file).resolve())
    out(
        args,
        {
            "valid": True,
            "name": lock.name,
            "paths": list(lock.paths),
            "criticality": lock.criticality,
            "review_required": lock.review_required,
        },
        title="Module Lock válido",
    )


def cmd_reset(args: argparse.Namespace) -> None:
    save_runtime(project_root(), {})
    out(args, {"reset": True}, title="Runtime limpo")


def cmd_setup(args: argparse.Namespace) -> None:
    codex = args.codex or not (args.codex or args.opencode)
    opencode = args.opencode or not (args.codex or args.opencode)
    out(
        args,
        {
            "dry_run": args.dry_run,
            "actions": setup_global(codex=codex, opencode=opencode, dry_run=args.dry_run),
        },
        title="Configuração global",
    )


def cmd_update(args: argparse.Namespace) -> None:
    out(args, update_tool(dry_run=args.dry_run), title="Atualização do Tide")


def cmd_uninstall(args: argparse.Namespace) -> None:
    installed = detect_adapters()
    explicit = args.codex or args.opencode
    codex = args.codex if explicit else installed["codex"]
    opencode = args.opencode if explicit else installed["opencode"]
    remaining = {
        "codex": installed["codex"] and not codex,
        "opencode": installed["opencode"] and not opencode,
    }
    remove_shared = not any(remaining.values())
    remove_package = not args.keep_tool and remove_shared
    if not args.yes and not args.dry_run:
        preview = uninstall_tool(
            codex=codex,
            opencode=opencode,
            dry_run=True,
            remove_package=remove_package,
            remove_shared=remove_shared,
        )
        out(args, preview, title="Desinstalação planejada")
        raise TideError("repeat with --yes to uninstall")
    result = uninstall_tool(
        codex=codex,
        opencode=opencode,
        dry_run=args.dry_run,
        remove_package=remove_package,
        remove_shared=remove_shared,
    )
    out(args, result, title="Simulação de remoção" if args.dry_run else "Tide removido")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tide", description="Minimal quality protocol for AI coding agents")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--json", action="store_true", help="output machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)
    init = sub.add_parser("init")
    init.set_defaults(func=cmd_init)

    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("task")
    prepare_parser.add_argument("--file", action="append")
    prepare_parser.set_defaults(func=cmd_prepare)

    revise_parser = sub.add_parser("revise")
    revise_parser.add_argument("--task")
    revise_parser.add_argument("--add-file", action="append")
    revise_parser.add_argument("--remove-file", action="append")
    revise_parser.set_defaults(func=cmd_revise)

    boundary = sub.add_parser("boundary")
    boundary_sub = boundary.add_subparsers(dest="boundary_action", required=True)
    for action in ("add", "remove"):
        command = boundary_sub.add_parser(action)
        command.add_argument("file", nargs="+")
        command.set_defaults(func=cmd_boundary)

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
    validate.add_argument("--verbose", action="store_true")
    validate.add_argument("command", nargs=argparse.REMAINDER)
    validate.set_defaults(func=cmd_validate)
    validation_log_parser = sub.add_parser("validation-log")
    validation_log_parser.add_argument("log_id")
    validation_log_parser.set_defaults(func=cmd_validation_log)

    review_packet_parser = sub.add_parser("review-packet")
    review_packet_parser.set_defaults(func=cmd_review_packet)
    review_show = sub.add_parser("review-show")
    review_show.add_argument("review_id")
    review_show.set_defaults(func=cmd_review_show)
    review = sub.add_parser("review")
    verdict = review.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--approved", action="store_true")
    verdict.add_argument("--blocked", dest="approved", action="store_false")
    review.add_argument("--review-id")
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
    update = sub.add_parser("update", help="update the uv tool and refresh installed adapters")
    update.add_argument("--dry-run", action="store_true")
    update.set_defaults(func=cmd_update)
    uninstall = sub.add_parser("uninstall", help="remove Tide integrations and the uv tool")
    uninstall.add_argument("--codex", action="store_true")
    uninstall.add_argument("--opencode", action="store_true")
    uninstall.add_argument("--keep-tool", action="store_true", help="remove integrations but keep the uv tool")
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--yes", action="store_true")
    uninstall.set_defaults(func=cmd_uninstall)

    mcp = sub.add_parser("mcp")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser("serve")
    mcp_serve.set_defaults(func=lambda args: raise_exit(serve()))
    return parser


def raise_exit(code: int) -> None:
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in raw
    raw = [item for item in raw if item != "--json"]
    parser = build_parser()
    args = parser.parse_args(raw)
    args.json = as_json
    try:
        args.func(args)
    except TideError as exc:
        if as_json:
            emit({"error": str(exc)}, as_json=True)
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
