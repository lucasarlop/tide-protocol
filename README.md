# Tide Protocol — experimental core

Tide is a minimal quality protocol for AI coding agents.

It does not document development history. It controls whether an implementation may be accepted by the supervisor.

## Thesis

```text
live code
→ smallest safe boundary
→ Module Locks and hardgates
→ one writer
→ real validation
→ optional independent review
→ deterministic quality gate
→ supervisor
```

## What is durable

Only policy that must influence future work:

- the global Tide Skill;
- quality and hardgate rules;
- engine adapters;
- short Module Locks for mature modules;

## What is temporary

Execution evidence is stored under `<git-dir>/tide/current.json`:

- current task and boundary;
- authorized hardgates;
- validations tied to the exact diff fingerprint;
- reviewer verdict tied to the exact diff fingerprint.

It is not versioned. If code changes after validation or review, that evidence becomes stale and `tide check` blocks completion. Pre-existing changes outside the task boundary are tolerated only while their diff remains unchanged.

## Components

- **Tide Core** — boundaries, hardgates, Module Locks, validation, review requirement, final gate.
- **CLI** — deterministic human/CI interface.
- **MCP** — the same Core exposed to Codex, OpenCode, and future engines.
- **Agent Skill** — canonical behavior loaded progressively.
- **Adapters** — short bootstrap and one read-only reviewer per engine.
- **code-review-graph** — optional, separate MCP for structural context. Tide does not duplicate it.

## Install this experiment

```bash
pipx install 'git+https://github.com/lucasarlop/tide-protocol.git@experiment/tide-core'
tide setup --codex --opencode
tide doctor
```

`uv tool install` works too.

`setup` installs globally:

```text
~/.agents/skills/tide/
~/.codex/AGENTS.md
~/.codex/agents/tide-reviewer.toml
~/.codex/config.toml
~/.config/opencode/AGENTS.md
~/.config/opencode/agents/tide-reviewer.md
~/.config/opencode/opencode.json
```

Existing OpenCode JSONC settings are preserved as values. Before normalization, Tide creates `opencode.json.tide-backup` once.

When `code-review-graph` is installed, Tide registers its official local MCP command alongside the Tide MCP. Otherwise, Tide keeps a direct-search fallback.

Inspect without changing files:

```bash
tide setup --codex --opencode --dry-run
```

## Initialize a project

```bash
cd my-project
tide init
```

This creates only:

```text
.tide/
  locks/
```

## Normal agent flow

The user opens Codex or OpenCode normally and describes the change.

The engine must:

1. load the Tide Skill;
2. call Tide `prepare` with the smallest likely boundary;
3. use code-review-graph MCP tools when available;
4. not edit while `mutation_allowed` is false;
5. request supervisor authorization for pending hardgates;
6. implement with one writer;
7. validate through Tide;
8. use `tide-reviewer` only when required;
9. call Tide `check`;
10. report completion only when `ready` is true.

## Manual equivalent

```bash
tide prepare 'Fix EPUB footnote backlinks' \
  --file 'src/epub/**' \
  --file 'tests/epub/**'

# Only when prepare reports pending hardgates and the supervisor approves:
tide authorize --all

tide context 'footnote backlink'

tide validate -- pytest tests/epub -x

# Only when review_required=true:
tide review-packet
tide review --approved

tide check
```

`tide check` exits with status `2` when the implementation is not ready.

## Hardgates

Hardgates stop mutation for sensitive work such as production, migrations, auth, secrets, real data, infrastructure, public API contracts, dependencies, or protected Module Lock contracts.

`prepare` returns:

```json
{
  "pending_hardgates": ["database", "production"],
  "mutation_allowed": false
}
```

The MCP `authorize` and `validate` tools are configured to require host approval.

## Module Locks

A Module Lock protects a mature module. It records only what is expensive or unsafe to rediscover:

- stable responsibility;
- invariants;
- external contracts;
- mandatory validations;
- sensitive changes.

Create a draft:

```bash
tide lock draft src/epub --name epub-generation
tide lock validate .tide/locks/epub-generation.md
```

Example:

```markdown
+++
name = "epub-generation"
paths = ["src/epub/**", "tests/epub/**"]
criticality = "production"
review_required = true
validations = ["pytest tests/epub -x", "epubcheck tests/fixtures/book.epub"]
invariants = ["Output passes EPUBCheck", "Footnotes keep bidirectional links"]
sensitive_changes = ["identifier strategy", "reading order", "persistence"]
+++
# EPUB generation

## Responsibility

Generate a valid EPUB from the normalized book model.

## Contracts

Input is the normalized book. Persistence belongs to another service.
```

Do not document every class, file, or function.

## MCP surface

Tide exposes ten tools:

- `prepare`
- `authorize`
- `context`
- `check`
- `validate`
- `review_packet`
- `record_review`
- `lock_list`
- `lock_template`
- `status`

OpenCode prefixes MCP tools with the server name, for example `tide_prepare`.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```

## Deliberate omissions

This experiment does not include:

- versioned Waves;
- persistent evidence;
- Taiga integration;
- report agents;
- a fleet of specialized reviewers;
- automatic commits;
- a second implementation of code-review-graph.

The experiment validates a smaller idea:

> live code + Module Locks + explicit hardgates + real validation + one optional reviewer.
