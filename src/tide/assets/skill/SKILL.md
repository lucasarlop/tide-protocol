---
name: tide
description: Mandatory quality protocol for code changes. Use before editing code, configuration, tests, dependencies, infrastructure, or project files.
---

# Tide

Control implementation quality. Do not track development history.

## Before editing

1. Treat current code, Git state, current diff, and real validations as truth.
2. Call Tide `prepare` with the smallest likely file boundary.
3. Use code-review-graph MCP tools when available. Confirm results against current code.
4. Do not edit while `mutation_allowed` is false.
5. Pending hardgates require explicit supervisor authorization through Tide `authorize`.

## While implementing

- One writer.
- Smallest safe change.
- Do not expand scope.
- Respect Module Locks.
- Call Tide `prepare` again if the boundary must change. This resets prior evidence.
- Use `tide-reviewer` only when Tide says review is required.

## Before completion

1. Run exact validations through Tide `validate`.
2. When review is required, call Tide `review_packet`, delegate to `tide-reviewer`, then record the verdict with Tide `record_review`.
3. Call Tide `check`.
4. Do not report completion unless `ready` is true.
5. Never commit or push without explicit supervisor approval.

## Communication

Caveman style:

- short sentences;
- concrete decisions;
- no ceremonial preamble;
- do not repeat the request;
- do not narrate intentions;
- explain only decisions, risks, blockers, and evidence.

## Completion checkpoint

- change;
- files;
- Module Locks;
- validation;
- review;
- residual risk;
- waiting for supervisor approval.

Load references only when relevant:

- `references/quality.md`
- `references/hardgates.md`
- `references/module-locks.md`
- `references/review.md`
