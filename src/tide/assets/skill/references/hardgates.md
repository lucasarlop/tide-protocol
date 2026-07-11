# Hardgates

Stop before mutation when work touches:

- production or deploy;
- databases or migrations;
- auth or permissions;
- secrets or credentials;
- real data or reprocessing;
- infrastructure or CI/CD;
- public API contracts;
- new production dependencies;
- Module Lock invariants or sensitive contracts.

Reading and planning are not approval to mutate.

Tide `prepare` returns pending hardgates and `mutation_allowed`.
Only the supervisor may authorize them through Tide `authorize`.
