---
name: tide
description: Mandatory quality protocol for code changes. Use before editing code, configuration, tests, dependencies, infrastructure, or project files.
---

# Tide

Protect quality without slowing the writer unnecessarily.

## Prepare

1. Treat live code, Git state, the current diff, and real validations as truth.
2. Call `prepare` with the smallest likely boundary and exact final validation commands.
3. Tide selects `fast` mode for ordinary changes and `strict` mode for sensitive hardgates or Module Locks.
4. Do not edit while `mutation_allowed` is false.
5. Use code-review-graph only when its results are relevant and confirm them against current code.

## Implement

- One writer.
- Smallest safe delta.
- Run targeted validations during implementation, using `covers` to name the changed files or patterns they validate.
- Do not rerun unaffected frontend, Compose, or full-suite checks after every small patch.
- Use `background=true` for long commands and poll `validation_status`; never start a duplicate while the first job may still be running.
- Use `revise` only for adjustments inside the current segment.
- Do not absorb unrelated worktree files into the boundary. Use `external_acknowledge` for stable client-generated files.
- Adding an already-changed file creates the `scope_expansion` hardgate.

## Converge

- `split_required=true` means the current segment is expanding faster than it is converging.
- Prefer `split` with a concrete child task and smaller boundary. It archives the parent, resets child review/scope budgets, and retains compatible validation evidence.
- Do not simulate a split through repeated `revise`; revise intentionally preserves the current segment budget.
- `extended_investigation` is bounded and expiring. Use it only with explicit supervisor authorization; it does not provide unlimited review retries.
- Findings are classified as:
  - `blocking`: correctness, data loss, security, contract, regression, or indispensable validation gaps;
  - `follow_up`: worthwhile improvement for a separate task;
  - `info`: non-blocking observation.
- Give findings stable IDs so the same issue is deduplicated across reviews and languages.
- Only blocking findings stay in the current task. Do not implement follow-ups automatically.
- After the first compatible review, use the default incremental packet.
- Force `full=true` only when central architecture, invariants, contracts, schema, security, or the boundary changed, and provide `full_reason`.
- Reuse an existing pending packet for an unchanged fingerprint. A repeated read of an unsubmitted packet counts as another review attempt.

## Close

1. Run final validations once, near closure, with `phase=final`.
2. Ensure every changed task file has current passing validation coverage.
3. Create `review_packet` only after validation coverage is complete.
4. A truncated packet cannot be approved.
5. Pass only `review_id` to `tide-reviewer`; the reviewer reads and submits directly.
6. An approved review locks closure. After that, only final validation and `check` are allowed.
7. Use `reopen` only for a concrete new blocking defect. `reopen` creates `closure_reopen`; authorize that gate after the reopen call.
8. Read the exact `primary_blocker`, `pending_hardgates`, and `next_action` returned by `check`. Do not guess the blocker.
9. Report completion only when `ready=true`.
10. Never commit or push without explicit supervisor approval.

## Session handoff

- Use `handoff` before moving to a fresh agent session.
- Continue from the returned task, segment, boundary, validation evidence, blockers, follow-ups, hardgates, and next action.
- Do not keep a multi-hour conversation alive merely to preserve technical state.

## Communication

- short sentences;
- concrete decisions;
- no routine narration;
- interrupt only for authorization, a real blocker, split_required, or the final checkpoint;
- report follow-ups separately from blockers.

## Completion checkpoint

- change;
- segment and files;
- mode and workflow metrics;
- acknowledged external changes;
- Module Locks and hardgates;
- current validation coverage;
- review and deduplicated follow-up tasks;
- residual risk;
- waiting for supervisor approval.

Load references only when relevant:

- `references/quality.md`
- `references/hardgates.md`
- `references/module-locks.md`
- `references/review.md`
