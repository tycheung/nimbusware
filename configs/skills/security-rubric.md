# Security rubric

- Reject slices that disable auth, jail, or path allowlists.
- Flag raw SQL, shell injection, and secret literals in diffs.
- FAIL when verify logs show bandit or pip-audit regressions.
