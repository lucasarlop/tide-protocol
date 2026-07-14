# Tide Protocol 1.2

Tide is a local quality protocol for autonomous coding agents. It does not manage branches, worktrees, containers, project planning, or remote services. It controls the quality and continuity of the code change already being performed in the current Git working tree.

## Core flow

```text
resume
→ prepare when no task exists
→ inspect live code and define the smallest safe boundary
→ implement the smallest safe delta
→ targeted validation
→ final validation for the stable fingerprint
→ independent review
→ blocker correction and incremental re-review
→ check
→ commit_check when commit is authorized
```

## Sources of truth

1. Live code and Git state.
2. File fingerprints for validation and review evidence.
3. A single deterministic evaluation used by `resume`, `check`, and `commit_check`.
4. The reviewer verdict bound to the exact reviewed fingerprint.

## Autonomy

The agent continues routine reads, edits, local tests, blocker fixes, independent review, and operational checks without user approval.

User input is required only for:

- a genuine requirement choice;
- destructive or production actions;
- real secrets or credentials;
- meaningful external cost;
- irreversible Git or deployment actions not already authorized;
- an investigation checkpoint after bounded failed attempts.

Technical risk changes validation and review depth. It is not itself an authorization gate.

## State

Each Git worktree naturally receives its own Tide runtime under its Git directory. The runtime stores only technical continuation state, not the conversation or private reasoning:

- task and boundary;
- validations and saved logs;
- review findings and approval proof;
- operational checks;
- segment receipts;
- convergence state and exact next action.

Lifecycle values are intentionally small:

- `active`;
- `approved`;
- `committed`;
- `abandoned`.

No task is represented by the absence of runtime state.

## Convergence

Two bounded failed correction attempts with an unknown root cause move the task into investigation. Editing stops until the problem is reduced.

When investigation finds new evidence but the root cause is still unknown, Tide asks the user to choose:

- `continue_one_cycle` — permit one more bounded investigation cycle;
- `stop_and_report` — end with the current diagnosis and no commit.

If no new evidence appears, Tide stops and reports instead of producing speculative patches.

## Validation

Evidence records the command, covered files, fingerprints, phase, result, duration, and saved log. A file edit invalidates only evidence covering that file. Final evidence is reused for the same fingerprint.

Tide recognizes clearly equivalent shell wrappers, but does not guess semantic equivalence between unrelated commands or broad and narrow test selectors.

## Review

Every code change receives independent review. Ordinary validated changes use `tide-reviewer`; technical risk, Module Locks, or explicit full review use `tide-reviewer-critical`.

Only `blocking` findings prevent closure. `follow_up` findings are recorded without extending the current task automatically.

The reviewer submits the verdict directly. The writer never relays or resubmits it.

## Commit gate

`commit_check` requires:

- current validation coverage;
- current independent approval;
- exact approved fingerprints;
- no pending user decision;
- staged files exactly matching the current Tide delta.

A managed pre-commit hook is a technical backstop. `--no-verify` is never permitted by the protocol.
