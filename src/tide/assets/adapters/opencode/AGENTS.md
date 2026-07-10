# Tide bootstrap

For any task that may modify project files:

1. Load the global `tide` skill.
2. Call Tide `prepare` before editing.
3. Do not edit while `mutation_allowed` is false.
4. Treat pending hardgates and Module Locks as mandatory.
5. Use one writer. Use `tide-reviewer` only when Tide requires review.
6. Call Tide `check` before reporting completion.
7. Never commit or push without explicit supervisor approval.

Use short, direct, caveman-style communication.
