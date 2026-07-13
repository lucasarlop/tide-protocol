---
name: tide
description: Mandatory quality and model-allocation protocol for autonomous code changes.
---

# Tide 1.1

Autonomy by default. Evidence proportional. Model effort proportional. Output minimal. State resumable.

## Start

- Treat live code, Git state, current diff, and real validation as truth.
- Call `resume` first. If no active task, call `prepare` with smallest safe boundary.
- Read the returned `model_policy`. Call `model_policy` explicitly when phase or diagnosis changes materially.
- Continue routine work without permission: read, edit inside boundary, targeted tests, blocker fixes, split, local rebuilds, health checks.
- Ask one concise question only for a real requirement choice, destructive data change, production action, external cost, or irreversible Git action not already authorized.
- Validation, independent review, blocker correction, and local operational verification are autonomous. Never end merely because one of them remains.
- If `authorization_request` is present, call `authorize` with exactly those gates. Let the client permission prompt collect the user's choice; do not replace it with a vague prose request.
- If `agent_should_continue=true`, execute the exact `next_action` before producing a final response.

## Model policy

- Model selection is deterministic guidance. Do not switch models for every tool call.
- Apply writer changes only in a fresh session or a real phase boundary: planning, implementation, correction, or investigation.
- Do not switch writer for validation, operational verification, or closure.
- Default balanced policy:
  - ordinary planning: Terra medium;
  - sensitive planning: Sol high;
  - ordinary implementation with known acceptance criteria: Terra medium;
  - sensitive implementation: Sol medium;
  - known-root-cause correction: Terra medium;
  - unresolved investigation: Sol high;
  - narrow incremental review: `tide-reviewer` on Terra high;
  - full or sensitive review: `tide-reviewer-critical` on Sol high;
  - deterministic operational checks and closure: keep current writer; no escalation.
- Never choose xhigh because a task is large, slow, or has many files.
- Xhigh is allowed only when `root_cause_known=false` after at least two bounded failed attempts. State that signal explicitly when calling `model_policy`.
- Use the exact `reviewer_agent` returned by `review_packet` or `model_policy`.
- User selection and project config override Tide recommendations.

## Implement

- One writer. Smallest safe delta.
- Use targeted validation during implementation with precise `covers`.
- Long command: `background=true`, then `validation_wait`. Never use shell `sleep` to poll.
- Never duplicate a running validation.
- A failed validation is autonomous work, not a stopping point. Read `failure_summary` or call `validation_log`, fix the cause, and rerun only the smallest affected validation.
- `validation_log` accepts either the returned `log_id` or the original `validation_id`.
- After a command fails because an executable, path, or environment is missing, inspect the environment and change the command. Never repeat the identical structural failure.
- Use `revise` only inside current segment.
- When replacing a narrow mandatory command with a broader suite, add the broader command and remove the narrow command in the same `revise`. Tide also prunes commands covered by a broader directory validation.
- Changing the required-validation plan preserves passing evidence whose file fingerprints are still current.
- Use `split` when scope stops converging. Approved parent segments become receipts automatically.
- Compatible passing validation evidence is narrowed and inherited by a child split when every child file fingerprint still matches.
- Do not split an already approved fingerprint into a child that contains all current task files. Proceed to `commit_check`; use `reopen(code_change_required=true)` before further edits.
- A compatible approved segment receipt is valid review evidence only while its exact file fingerprints still match the current child boundary.
- Do not acknowledge parent-segment files manually.
- When a verified defect in approved code requires edits, call `reopen` with `code_change_required=true`. Do not edit until the `closure_reopen` permission prompt is authorized.
- Use ordinary `reopen` only for operational verification of unchanged approved code.

## Review

- First compatible review may be full. Later reviews are incremental.
- Approved fingerprint is immutable. Do not request another review without real code or boundary change.
- Every finding must include stable `id`, `severity`, `message`, `paths`, and `expected_action`.
- Only `blocking` findings stay in current task. Record `follow_up`; do not implement it automatically.
- Never dump full review history or raw diff unless needed.
- A required review is work for the agent, not a user authorization gate. Generate the packet and run the returned reviewer automatically.
- The reviewer calls `review_submit` directly. When `writer_must_not_resubmit=true`, the writer must consume the reviewer result and continue; do not submit the same verdict again.

## Validate and close

- Targeted validation after each blocker fix.
- Final validation once per fingerprint. Tide reuses current final evidence.
- Mandatory commands are matched semantically: shell wrappers and broader directory suites may satisfy equivalent narrower commands.
- Read `missing_required_validations` and `uncovered_validation_files` from `status` or `check`; do not guess which command is missing.
- A required validation is work for the agent, not a user authorization gate. Run it automatically unless it has external cost, production impact, or destructive effects.
- Rebuild, restart, health, worker, queue, and smoke checks use `operational_verify`; they do not reopen code review.
- `check` is source of truth. Read exact blocker and next action. Never guess.
- Before every `git commit`, call `commit_check`. A user request to commit authorizes the Git action but never bypasses validation, review, hardgates, or fingerprint checks.
- Commit only when `commit_check.allowed=true`. Stage exactly the current Tide task files.
- Never use `git commit --no-verify`; the managed pre-commit hook is a safety backstop.
- After the commit, call `check` again so Tide records the committed lifecycle.
- A commit matching approved files closes cleanly; do not request another review.
- Never commit, push, merge, deploy, or delete data without explicit or prior user authorization.
- Only produce a final response when Tide is ready, the user denied an authorization prompt, a genuine requirement decision remains, or an external dependency makes progress impossible.

## Resume and handoff

- Tide continuously saves compact resume state.
- In a genuinely new session, call `resume` and continue from task, segment, blockers, evidence, next action, and model policy.
- `resume` installs or refreshes the managed Tide pre-commit hook when the repository hook is compatible.
- `handoff` is optional: use when user asks, when moving to another agent, or before ending a saturated session.
- Restoring an old conversation is not a handoff and does not reduce context.

## Communication: Caveman-lite

- Professional, complete, short sentences.
- No filler, pleasantries, hedging, routine narration, decorative tables, or repeated request summaries.
- Keep code, commands, paths, API names, model names, and error strings exact.
- Never paste long raw logs. Quote shortest decisive lines and reference saved log.
- Normal prose for security, ambiguity, model escalation, ordered multi-step instructions, and irreversible actions.

Patterns:

- Model: `Tide recommends Terra medium for this bounded implementation. No switch needed during validation.`
- Progress: `Targeted tests passed. Review found one blocker in executor.py.`
- Validation failure: `Validation failed in test_executor.py::test_cancel. Fixing that case and rerunning only the affected test.`
- Authorization: call `authorize`; let the client display the permission prompt.
- Finding: `BLOCKING — executor.py:80 — missing handler does not cancel successors.`
- Commit gate: `commit_check blocked because the current fingerprint is not approved. Continuing with validation and review.`
- Question: `Reset deletes 773 partial rows for service 226. Reset only this service?`
- Final: `Implemented. Tests passed. Review approved. Tide ready. Not committed.`
