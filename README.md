# Tide Protocol 1.0

Tide is a quality protocol for autonomous AI coding agents.

```text
resume state
→ smallest safe boundary
→ targeted evidence
→ incremental independent review
→ final validation once
→ operational verification
→ commit or supervisor checkpoint
```

## Install

```bash
uv tool install --python 3.12 \
  'git+https://github.com/lucasarlop/tide-protocol.git@main'

tide setup --codex --opencode
tide doctor
```

Update later:

```bash
tide update
```

## Tide 1.0 behavior

### Trusted autonomy

Agents continue routine work without asking permission:

- read and edit inside the declared boundary;
- run targeted validations;
- fix blocking review findings;
- split a task into a smaller child segment;
- rebuild local containers;
- run health, worker, queue, and smoke checks.

Agents ask one concise question only for:

- a real requirement choice;
- destructive data changes;
- production actions;
- meaningful external cost;
- commit, push, merge, deploy, or another irreversible action not already authorized.

### Resume and handoff

Tide continuously stores a compact checkpoint containing:

- current task and segment;
- boundary and changed files;
- valid evidence;
- latest review and blockers;
- follow-ups and pending hardgates;
- exact next action.

In a genuinely new agent session, use MCP `resume`. `handoff` is optional and useful when explicitly moving work to another session or agent.

Restoring an old conversation is not a handoff. It keeps the old model context.

### Long validations without shell sleep

Use background validation and `validation_wait`:

```json
{
  "command": ["pytest"],
  "background": true,
  "phase": "targeted"
}
```

Then:

```json
{
  "validation_id": "validation-job-...",
  "wait_seconds": 20
}
```

While a job runs, `passed` is `null`, not `false`.

### Proportional evidence

- Use `targeted` during implementation.
- Use `final` once per unchanged fingerprint.
- Repeating the same final validation reuses current evidence.
- A code change invalidates only evidence covering the changed files.

### Incremental review

The first compatible review may be full. Later reviews include only the delta.

Every structured finding contains:

```json
{
  "id": "stable-finding-id",
  "severity": "blocking",
  "message": "Concrete defect and impact.",
  "paths": ["src/module.py:42-51"],
  "expected_action": "Concrete correction."
}
```

An approved fingerprint cannot be reviewed again without real code or boundary change.

### Segments and receipts

`split` creates a smaller child segment, resets child workflow budgets, and archives the parent.

If the parent review was approved, Tide stores a receipt containing its file fingerprints. Parent files do not need manual `external_acknowledge` in the child segment.

### Operational verification

Rebuilds, restarts, health checks, worker pings, queue checks, and smoke tests do not reopen code review.

Record them through `operational_verify`.

### Commit recognition

When committed files match the approved content, Tide recognizes the commit and closes without requesting another review.

### Communication

Tide adapters use a Caveman-lite policy:

- complete, professional, short sentences;
- no filler, pleasantries, hedging, or routine tool narration;
- no raw log dumps;
- exact code, commands, paths, API names, and error strings;
- normal prose for risk, ambiguity, ordered procedures, and irreversible actions.

The external Caveman skill is optional. Tide does not require it because its full rules add per-turn input overhead and do not compress tool stdout or reasoning.

## MCP surface

Tide exposes:

- `prepare`, `revise`, `split`;
- `resume`, `handoff`;
- `validate`, `validation_status`, `validation_wait`, `validation_log`;
- `review_packet`, `review_get`, `review_submit`;
- `operational_verify`;
- `external_acknowledge`, `authorize`;
- `check`, `status`;
- `context`, `lock_list`, `lock_template`.

MCP text output stays compact. Full structured state remains in `structuredContent`. Full validation logs remain lazy.

## Module Locks

Module Locks protect mature production contracts:

```bash
tide lock draft src/epub --name epub-generation
tide lock validate .tide/locks/epub-generation.md
```

A lock records only stable responsibility, invariants, external contracts, mandatory validations, and sensitive changes.

## State

Temporary state lives under `<git-dir>/tide/` and is not versioned:

- active task and segment receipts;
- validation evidence and background jobs;
- compact logs;
- review packets and receipts;
- resume checkpoint;
- operational checks.

Evidence is tied to exact file content or diff fingerprints.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```

## Uninstall

```bash
tide uninstall --dry-run
tide uninstall --yes
```
