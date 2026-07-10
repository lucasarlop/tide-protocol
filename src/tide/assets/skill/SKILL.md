---
name: tide
description: Mandatory quality protocol for code changes. Use before editing code, configuration, tests, dependencies, infrastructure, or project files.
---

# Tide

Use Tide to control implementation quality.

## Always

1. Treat current code, Git state, diff, and real validations as truth.
2. Call `tide_prepare` before editing.
3. Use the smallest safe boundary.
4. Use one writer.
5. Respect Module Locks and hardgates.
6. Validate changed behavior.
7. Call `tide_check` before saying the work is ready.
8. Never commit or push without explicit supervisor approval.

## Communication

Caveman style:

- short sentences;
- concrete decisions;
- no ceremonial preamble;
- do not repeat the request;
- do not narrate intentions;
- explain only decisions, risks, blockers, and evidence.

## Context

Use `tide_context` first when it reduces broad exploration.
`code-review-graph` accelerates discovery but never replaces reading current code.

## Review

Use the configured `tide-reviewer` only when Tide requires review.
The reviewer is read-only. Pass only the task, diff, applicable locks, and validations.

## Completion

Final checkpoint:

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
