# Tide Protocol 1.1

Tide is a quality and model-allocation protocol for autonomous AI coding agents.

```text
resume state
→ model profile for the current phase
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

## Model policy

Tide 1.1 adds deterministic, auditable model recommendations. The policy never silently changes the active writer and never escalates merely because a task is long or touches many files.

Default `balanced` strategy:

| Phase | Ordinary change | Sensitive change |
|---|---|---|
| Planning | Terra medium | Sol high |
| Exploration | Terra medium | Terra medium |
| Implementation | Terra medium | Sol medium |
| Known-root-cause correction | Terra medium | Sol high |
| Unresolved investigation | Sol high | Sol high |
| Incremental review | Terra high reviewer | Sol high critical reviewer |
| Full review | Sol high critical reviewer | Sol high critical reviewer |
| Validation | Keep writer; Terra medium guidance | Keep writer; Terra medium guidance |
| Operational/closure | Keep writer; no escalation | Keep writer; no escalation |

`xhigh` is reserved for one narrow condition: `root_cause_known=false` after at least two bounded failed attempts. File count, elapsed time, and token consumption do not trigger it.

Call the MCP tool:

```json
{
  "phase": "implementation"
}
```

For a difficult unresolved investigation:

```json
{
  "phase": "investigation",
  "failed_attempts": 2,
  "root_cause_known": false
}
```

The response includes:

- model and reasoning recommendation;
- whether a writer switch is worthwhile;
- the safe boundary where a switch may occur;
- exact signals and reasons;
- the reviewer agent for the current review mode;
- Codex and OpenCode adapter hints.

Writer-model changes should occur only in a new session or a real major-phase boundary. Validation, operational checks, and closure never justify model thrashing.

### Reviewers

`tide setup` installs two read-only reviewers:

- `tide-reviewer`: Terra high for narrow, validated incremental packets;
- `tide-reviewer-critical`: Sol high for full reviews and sensitive changes.

`review_packet` returns the exact `reviewer_agent` to use.

### Project configuration

Optional `.tide/model-policy.json`:

```json
{
  "strategy": "balanced",
  "allow_xhigh": true
}
```

Supported strategies:

- `economy`: uses the same quality floors as balanced, with Luna for deterministic operational phases;
- `balanced`: recommended default;
- `quality`: raises ordinary planning, implementation, and review capability;
- `manual`: reports context but leaves selection entirely to the user.

## Tide 1.x behavior

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
- exact code, commands, paths, API names, model names, and error strings;
- normal prose for risk, ambiguity, model escalation, ordered procedures, and irreversible actions.

The external Caveman skill is optional. Tide does not require it because its full rules add per-turn input overhead and do not compress tool stdout or reasoning.

## MCP surface

Tide exposes:

- `prepare`, `revise`, `split`;
- `model_policy`;
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
