# Module Locks

A Module Lock protects a mature module.

It records only what is expensive or unsafe to rediscover:

- stable responsibility;
- invariants;
- external contracts;
- mandatory validations;
- sensitive changes.

Do not document every file, class, or function.

When a lock applies:

1. read it before editing;
2. verify impact against live code;
3. run every mandatory validation;
4. use independent review when required;
5. stop before changing an invariant.
