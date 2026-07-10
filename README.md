# Tide Protocol — experimental core

Tide is a minimal quality protocol for AI coding agents.

It controls implementation quality before work is accepted by the supervisor.

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

- current task and boundary;
- validation evidence and full logs;
- review packets;
- reviewer verdict.

Temporary evidence is not versioned. Validation and review are tied to the exact diff fingerprint.

## Normal flow

```bash
tide prepare 'Fix EPUB footnote backlinks' \
  --file 'src/epub/**' \
  --file 'tests/epub/**'

# Only after explicit supervisor approval:
tide authorize --all

tide validate -- pytest tests/epub -x

# Only when review_required=true:
tide review-packet
# pass only the returned review_id to tide-reviewer
tide review --review-id <review-id> --approved

tide check
```

The agent normally calls these operations through MCP.

## Change scope without restarting

Do not call a new `prepare` when implementation reveals another file or the review requests a correction.

```bash
tide boundary add .gitlab-ci.yml
tide boundary remove old-file.py

tide revise \
  --task 'Correct review findings' \
  --add-file .gitlab-ci.yml
```

`revise` preserves the original working-tree baseline, recalculates policy and Module Locks, and invalidates previous validation and review evidence. It does not create a false `dirty_boundary` for changes produced by the current task.

## Validation output

Validation returns compact evidence by default:

```text
Passou: sim
Código de saída: 0
Duração: 2.13s
Log ID: validation-...
```

Full stdout and stderr stay under `<git-dir>/tide/logs/` and are loaded only when needed:

```bash
tide validation-log <log-id>
tide validate --verbose -- pytest -q
```

## Independent review

`tide review-packet` stores the detailed packet and returns only:

- `review_id`;
- resource URI;
- files and diff size;
- validation count;
- review focus.

The main writer passes only `review_id` to `tide-reviewer`. The reviewer reads the packet directly with Tide `review_get` or the MCP resource:

```text
tide://reviews/<review-id>
```

This keeps the full diff out of the writer's context.

## Context and code-review-graph

Tide treats current code, Git state, current diff, and real validations as truth.

When `code-review-graph` is available, Tide recommends a sequence based on context quality:

- build the graph if the index is missing;
- use architecture overview and semantic search for broad or weak results;
- use minimal context and impact analysis for focused tasks;
- confirm all findings against current code.

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
- pre-existing changes inside the task boundary.

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

- `prepare` and `revise`;
- `authorize`;
- `context`;
- `validate` and `validation_log`;
- `review_packet`, `review_get`, and `record_review`;
- `check` and `status`;
- `lock_list` and `lock_template`.

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
