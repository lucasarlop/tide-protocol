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
- Module Lock invariants.

Reading and planning are not approval to mutate.
