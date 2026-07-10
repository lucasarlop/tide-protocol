# Tide bootstrap

For any task that may modify project files:

1. Load the global `tide` skill.
2. Call Tide `prepare` before editing.
3. Use Tide `revise`, not another `prepare`, when the task or boundary changes.
4. Do not edit while `mutation_allowed` is false.
5. Treat pending hardgates and Module Locks as mandatory.
6. Use one writer. Use `tide-reviewer` only when Tide requires review.
7. Pass only the `review_id`; the reviewer reads the detailed packet directly.
8. Call Tide `check` before reporting completion.
9. Never commit or push without explicit supervisor approval.

Use short, direct, caveman-style communication. Do not announce routine steps or maintain visible todos unless requested. Interrupt only for authorization, blockers, or the final checkpoint.
