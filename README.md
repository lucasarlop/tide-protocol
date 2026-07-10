# Tide Protocol — experimental core

Tide is a minimal quality protocol for AI coding agents.

It controls implementation quality before work is accepted by the supervisor.

```text
live code
→ smallest safe boundary
→ explicit validation plan
→ Module Locks and hardgates
→ one writer
→ current validation evidence
→ optional independent review
→ deterministic quality gate
→ supervisor
```

## Install

```bash
uv tool install --python 3.12 \
  'git+https://github.com/lucasarlop/tide-protocol.git@experiment/tide-core'

tide setup --codex --opencode
tide doctor
```

Update later with:

```bash
tide update
```

## State

Durable state:

- global Tide Skill;
- quality and hardgate rules;
- engine adapters;
- short Module Locks under `.tide/locks/`.

Temporary state lives under `<git-dir>/tide/`:

- current task, boundary, and required validation plan;
- acknowledged external worktree changes;
- validation evidence, background jobs, and full logs;
- review packets;
- reviewer verdict and receipt.

Temporary evidence is not versioned. Validation and review are tied to the exact diff fingerprint.

## Normal flow

```bash
tide prepare 'Fix EPUB footnote backlinks' \
  --file 'src/epub/**' \
  --file 'tests/epub/**' \
  --require-validation 'pytest tests/epub -x'

# Only after explicit supervisor approval:
tide authorize --all

tide validate -- pytest tests/epub -x

# Only when review_required=true:
tide review-packet
# pass only the returned review_id to tide-reviewer;
# the reviewer reads the packet and submits its own verdict

tide check
```

The agent normally calls these operations through MCP.

## Change scope or validation plan without restarting

Do not call a new `prepare` when implementation reveals another file, another mandatory check, or the review requests a correction.

```bash
tide boundary add .gitlab-ci.yml
tide boundary remove old-file.py

tide revise \
  --task 'Correct review findings' \
  --add-file .gitlab-ci.yml \
  --add-required-validation './scripts/run_tests.sh'
```

`revise` preserves the original working-tree baseline, recalculates policy and Module Locks, and invalidates previous validation and review evidence. It does not create a false `dirty_boundary` for changes produced by the current task.

Adding a file that is already changed when `revise` expands the boundary creates a `scope_expansion` hardgate. The agent cannot silently absorb an existing worktree change into the task; explicit supervisor authorization is required.

## External worktree changes

An unrelated file created or modified during the session must not be added to the task boundary merely to make `outside_boundary` disappear.

Use the MCP tool `external_acknowledge` with the exact file and a concrete reason:

```json
{
  "files": ["session-export.md"],
  "reason": "session export created by the client"
}
```

The file remains outside the task boundary, diff, validation fingerprint, and review packet. Tide stores its current fingerprint and ignores it only while it remains unchanged. A later modification makes it an outside-boundary violation again.

## Required validations

Task-level required validations complement Module Lock validations. `tide check` is ready only when every exact required command has passed against the current diff fingerprint.

A passing targeted test no longer substitutes for a declared full suite:

```text
required_validations:
- ./scripts/run_tests.sh
- python scripts/validate_epub.py output.epub

missing_validations:
- ./scripts/run_tests.sh
```

## Long validations

Validation returns compact evidence by default. Commands likely to outlive the MCP request can run in the background:

```bash
tide validate --background --timeout 1800 -- ./scripts/run_tests.sh
# returns validation_id

tide validation-status <validation-id>
```

The worker stores its result under `<git-dir>/tide/validation-jobs/`. When collected, the evidence remains tied to the diff fingerprint captured when the job started. A code change while the command runs makes that evidence stale rather than current.

Full stdout and stderr stay under `<git-dir>/tide/logs/` and are loaded only when needed:

```bash
tide validation-log <log-id>
tide validate --verbose -- pytest -q
```

Compact evidence limits both the number of lines and total bytes. Very long coverage lines are clipped; the complete output remains available through `validation_log`.

## Independent review

`tide review-packet` stores the detailed packet and returns only:

- `review_id`;
- resource URI;
- files and diff size;
- current and missing validation counts;
- review focus;
- whether the diff was truncated.

The main writer passes only `review_id` to `tide-reviewer`. The reviewer reads the packet directly with Tide `review_get` or the MCP resource:

```text
tide://reviews/<review-id>
```

The detailed packet contains a one-time submission token. The reviewer submits the verdict directly through `review_submit`; Tide stores a receipt and rejects a second submission for the same packet. This removes the normal writer relay from the review flow.

A packet with `diff_truncated=true` cannot be approved. The task boundary must be reduced or unrelated external changes must be acknowledged before a new packet is created.

## Simplicity signals

Tide reviews simplicity changes caused by the current diff instead of listing every large legacy function in a touched file. It signals:

- a new source file above 400 lines;
- a new Python function above 100 lines;
- an existing Python function above 100 lines that grows by more than 40 lines.

## Context and code-review-graph

Tide treats current code, Git state, current diff, and real validations as truth.

When `code-review-graph` is available, Tide recommends a sequence based on context quality:

- build the graph if the index is missing;
- use architecture overview and semantic search for broad or weak results;
- use minimal context and impact analysis for focused tasks;
- ignore irrelevant graph results and confirm all findings against current code.

Adapters instruct agents to use graph context before implementation, not only before final review.

## Hardgates

Hardgates stop mutation until explicit supervisor authorization for sensitive work such as:

- production and deploy;
- database and migrations;
- auth and secrets;
- real data or reprocessing;
- infrastructure and CI/CD;
- public API contracts;
- dependencies and package manifests;
- protected Module Lock contracts;
- pre-existing changes inside the task boundary;
- late expansion of the task boundary over already-changed files.

Dependency detection includes `pyproject.toml`, `setup.py`, `setup.cfg`, requirements files, lock files, Node, Go, Rust, Ruby, Java/Gradle, and Composer manifests.

## Module Locks

A Module Lock protects a mature production module. It records only what is expensive or unsafe to rediscover:

- stable responsibility;
- invariants;
- external contracts;
- mandatory validations;
- sensitive changes.

```bash
tide lock draft src/epub --name epub-generation
tide lock validate .tide/locks/epub-generation.md
```

Do not document every class, file, or function.

## CLI output

Human-readable output is the default. Use `--json` for scripts:

```bash
tide status
tide status --json
```

## MCP surface

Tide exposes:

- `prepare` and `revise` with required validation plans;
- `external_acknowledge` for stable unrelated worktree changes;
- `authorize`;
- `context`;
- `validate`, `validation_status`, and `validation_log`;
- `review_packet`, `review_get`, and `review_submit`;
- `check` and `status`;
- `lock_list` and `lock_template`.

Every tool schema rejects unknown arguments. MCP text content is a short human summary while full data remains in `structuredContent`, avoiding duplicate large JSON payloads in clients such as Codex.

Review packets are also MCP resources under `tide://reviews/`.

## Communication

Adapters require short, direct communication. Agents should not announce routine steps or maintain visible todos unless requested. They should interrupt only for authorization, a real blocker, or the final checkpoint.

## Uninstall

```bash
tide uninstall --dry-run
tide uninstall --yes
```

Tide removes only its managed blocks, reviewer files, MCP registration, shared Skill, and package. It preserves unrelated Codex/OpenCode settings and independent `code-review-graph` configuration.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```

Deliberate omissions:

- versioned Waves;
- persistent execution history;
- Taiga integration;
- report agents;
- fleets of specialized reviewers;
- automatic commits;
- a second implementation of code-review-graph.
