# Tide Protocol — experimental core

Tide is a minimal quality protocol for AI coding agents.

It does not track development history. It controls whether an implementation is good enough to reach the supervisor.

## Design

- live code is the source of truth;
- `code-review-graph` accelerates context when available;
- one writer by default;
- one read-only reviewer only when required;
- Module Locks protect mature production modules;
- hardgates stop sensitive mutations;
- validation evidence is temporary and stored under the Git directory;
- Codex, OpenCode, and future engines use the same Core through MCP;
- CLI and MCP call the same Python implementation.

## Install from this branch

```bash
pipx install 'git+https://github.com/lucasarlop/tide-protocol.git@experiment/tide-core'
tide setup --codex --opencode
tide doctor
```

`uv tool install` works too.

## Global installation

`tide setup` installs:

- the shared Agent Skill at `~/.agents/skills/tide`;
- a short managed bootstrap in Codex and OpenCode global instructions;
- one read-only reviewer for each engine;
- the Tide MCP server as `tide mcp serve`.

Use `--dry-run` to inspect changes.

## Project setup

```bash
cd my-project
tide init
```

This creates only versioned project policy:

```text
.tide/
  project.toml
  locks/
```

Temporary execution state is stored in `<git-dir>/tide/current.json`, never in the repository.

## Daily flow

Normally, open Codex or OpenCode and ask for the change. The global bootstrap makes the engine load Tide and call the MCP tools.

Manual equivalent:

```bash
tide prepare 'Fix EPUB footnote backlinks' \
  --file 'src/epub/**' \
  --file 'tests/epub/**'

tide context 'footnote backlink'

tide validate -- pytest tests/epub -x

tide review --approved

tide check
```

`tide check` exits with status 2 when the implementation is not ready.

## Module Locks

Create a draft only after a module is mature:

```bash
tide lock draft src/epub --name epub-generation
tide lock validate .tide/locks/epub-generation.md
```

Then use the agent to analyze live code, tests, callers, and production constraints. Keep the lock short.

Example:

```markdown
+++
name = "epub-generation"
paths = ["src/epub/**", "tests/epub/**"]
criticality = "production"
review_required = true
validations = ["pytest tests/epub -x", "epubcheck tests/fixtures/book.epub"]
invariants = ["Output must pass EPUBCheck", "Footnotes keep bidirectional links"]
sensitive_changes = ["identifier strategy", "reading order", "persistence"]
+++
# EPUB generation

## Responsibility

Generate a valid EPUB from the normalized book model.

## Contracts

Input is the normalized book. Persistence belongs to another service.
```

## MCP tools

- `tide_prepare`
- `tide_context`
- `tide_check`
- `tide_validate`
- `tide_lock_list`
- `tide_status`

The MCP server also returns compact mandatory instructions during initialization.

## Scope of this experiment

This branch intentionally removes the previous Wave-heavy runtime, Taiga integration, report agents, specialized reviewer fleet, and persistent evidence model.

The experiment validates a smaller thesis:

> live code + Module Locks + deterministic quality gates + one optional reviewer.
