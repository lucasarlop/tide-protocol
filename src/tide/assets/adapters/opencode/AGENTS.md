# Tide bootstrap

For any task that may modify project files:

1. Load the global `tide` skill.
2. Call `tide_prepare` before editing.
3. Treat Tide hardgates and Module Locks as mandatory.
4. Use one writer. Use `tide-reviewer` only when Tide requires review.
5. Call `tide_check` before reporting completion.
6. Never commit or push without explicit supervisor approval.

Use short, direct, caveman-style communication.
