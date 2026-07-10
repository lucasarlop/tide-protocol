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
- Do not expand scope silently.
- Respect Module Locks.
- Use Tide `revise` when the task or boundary changes. Do not call a new `prepare`; revise preserves the original baseline and invalidates old evidence.
- Use `tide-reviewer` only when Tide says review is required.

## Before completion

1. Run exact validations through Tide `validate`.
2. Use compact validation evidence. Read a full `validation_log` only when a failure or warning needs diagnosis.
3. When review is required, call Tide `review_packet`, pass only its `review_id` to `tide-reviewer`, and let the reviewer read the packet directly with `review_get`.
4. Record the verdict with Tide `record_review`, including the same `review_id`.
5. Call Tide `check`.
6. Do not report completion unless `ready` is true.
7. Never commit or push without explicit supervisor approval.

## Communication

Caveman style:

- short sentences;
- concrete decisions;
- no ceremonial preamble;
- do not repeat the request;
- do not narrate routine next steps;
- do not maintain visible todos unless requested;
- interrupt only for authorization, a real blocker, or the final checkpoint;
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
