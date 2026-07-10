---
name: tide
description: Mandatory quality protocol for code changes. Use before editing code, configuration, tests, dependencies, infrastructure, or project files.
---

# Tide

Control implementation quality. Do not track development history.

## Before editing

1. Treat current code, Git state, current diff, and real validations as truth.
2. Call Tide `prepare` with the smallest likely file boundary.
3. Declare the exact validation commands that must pass for the final diff.
4. Use code-review-graph MCP tools when available. Confirm results against current code.
5. Do not edit while `mutation_allowed` is false.
6. Pending hardgates require explicit supervisor authorization through Tide `authorize`.

## While implementing

- One writer.
- Smallest safe change.
- Do not expand scope silently.
- Respect Module Locks.
- Use Tide `revise` when the task, boundary, or validation plan changes. Do not call a new `prepare`; revise preserves the original baseline and invalidates old evidence.
- Use `tide-reviewer` only when Tide says review is required.

## Before completion

1. Run exact validations through Tide `validate`.
2. For commands likely to exceed the MCP request window, use `background=true` and poll `validation_status` until completion.
3. Use compact validation evidence. Read a full `validation_log` only when a failure or warning needs diagnosis.
4. When review is required, call Tide `review_packet` and pass only its `review_id` to `tide-reviewer`.
5. The reviewer reads the packet with `review_get` and submits its own verdict with `review_submit`. The writer must not relay or rewrite reviewer findings.
6. Call Tide `check`.
7. Do not report completion unless `ready` is true and every required validation is current.
8. Never commit or push without explicit supervisor approval.

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
- required validations;
- validation evidence;
- review;
- residual risk;
- waiting for supervisor approval.

Load references only when relevant:

- `references/quality.md`
- `references/hardgates.md`
- `references/module-locks.md`
- `references/review.md`
