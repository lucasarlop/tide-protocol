# Tide Protocol

Tide is a reliable local quality protocol for autonomous coding agents such as Codex and OpenCode.

It keeps agent work bounded, validated, independently reviewed, resumable, and safe to commit without taking control of branches, worktrees, Docker, or the developer's daily workflow.

## Install

```bash
uv tool install --python 3.12 \
  'git+https://github.com/lucasarlop/tide-protocol.git@main'

tide setup --codex --opencode
tide doctor
```

## Daily use

Start Codex or OpenCode normally and describe the task. The installed Tide instructions make the agent call `resume` automatically at the beginning of a new session.

Human-facing commands are intentionally few:

```bash
tide resume
tide status
tide check
tide setup
tide doctor
tide update
tide lock --help
```

The agent uses validation, review, convergence, and commit tools internally.

## Protocol

```text
resume
→ prepare when no task exists
→ define a safe boundary
→ implement the smallest delta
→ validate
→ independent review
→ fix blockers
→ check
→ commit_check when authorized
```

A task can stop before `check.ready=true` only when a real user decision is required, continuation was declined, or an external dependency makes progress impossible.

After two bounded failed corrections with an unknown root cause, Tide stops speculative editing and enters investigation. New evidence without a root cause creates a user checkpoint: continue one bounded cycle or stop with the current diagnosis.

See [PROTOCOL.md](PROTOCOL.md) for the complete contract.

## Module Locks

Module Locks protect mature code contracts without documenting the obvious implementation:

```bash
tide lock draft src/epub --name epub-generation
tide lock validate .tide/locks/epub-generation.md
```

A lock records stable responsibility, invariants, mandatory validations, and sensitive changes.

## State and privacy

Tide stores compact technical state under the Git directory for the current worktree. It does not store the conversation or private model reasoning.

Validation logs and review packets remain local and are loaded only when needed.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```
