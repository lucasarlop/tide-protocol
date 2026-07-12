---
name: tide
description: Mandatory quality protocol for autonomous code changes.
---

# Tide 1.0

Autonomy by default. Evidence proportional. Output minimal. State resumable.

## Start

- Treat live code, Git state, current diff, and real validation as truth.
- Call `resume` first. If no active task, call `prepare` with smallest safe boundary.
- Continue routine work without permission: read, edit inside boundary, targeted tests, blocker fixes, split, local rebuilds, health checks.
- Ask one concise question only for a real requirement choice, destructive data change, production action, external cost, or irreversible Git action not already authorized.

## Implement

- One writer. Smallest safe delta.
- Use targeted validation during implementation with precise `covers`.
- Long command: `background=true`, then `validation_wait`. Never use shell `sleep` to poll.
- Never duplicate a running validation.
- Use `revise` only inside current segment.
- Use `split` when scope stops converging. Approved parent segments become receipts automatically.
- Do not acknowledge parent-segment files manually.

## Review

- First compatible review may be full. Later reviews are incremental.
- Approved fingerprint is immutable. Do not request another review without real code or boundary change.
- Every finding must include stable `id`, `severity`, `message`, `paths`, and `expected_action`.
- Only `blocking` findings stay in current task. Record `follow_up`; do not implement it automatically.
- Never dump full review history or raw diff unless needed.

## Validate and close

- Targeted validation after each blocker fix.
- Final validation once per fingerprint. Tide reuses current final evidence.
- Rebuild, restart, health, worker, queue, and smoke checks use `operational_verify`; they do not reopen code review.
- `check` is source of truth. Read exact blocker and next action. Never guess.
- A commit matching approved files closes cleanly; do not request another review.
- Never commit, push, merge, deploy, or delete data without explicit or prior user authorization.

## Resume and handoff

- Tide continuously saves compact resume state.
- In a genuinely new session, call `resume` and continue from task, segment, blockers, evidence, and next action.
- `handoff` is optional: use when user asks, when moving to another agent, or before ending a saturated session.
- Restoring an old conversation is not a handoff and does not reduce context.

## Communication: Caveman-lite

- Professional, complete, short sentences.
- No filler, pleasantries, hedging, routine narration, decorative tables, or repeated request summaries.
- Keep code, commands, paths, API names, and error strings exact.
- Never paste long raw logs. Quote shortest decisive lines and reference saved log.
- Normal prose for security, ambiguity, ordered multi-step instructions, and irreversible actions.

Patterns:

- Progress: `Targeted tests passed. Review found one blocker in executor.py.`
- Finding: `BLOCKING — executor.py:80 — missing handler does not cancel successors.`
- Question: `Reset deletes 773 partial rows for service 226. Reset only this service?`
- Final: `Implemented. Tests passed. Review approved. Tide ready. Not committed.`
