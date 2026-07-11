# Review

One reviewer. Read-only.

The writer creates a packet with Tide `review_packet` and passes only the returned `review_id` to `tide-reviewer`. The reviewer reads the detailed packet directly with `review_get` or `tide://reviews/<review_id>`.

Do not relay the full diff or complete validation logs through the writer.

Review for:

- requested behavior;
- Module Lock compliance;
- regression and security risk;
- simplicity when Tide reports a simplicity signal;
- validation quality;
- boundary violations.

Return only the review ID, verdict, and short findings with severity. Do not write a report. Do not edit code.
