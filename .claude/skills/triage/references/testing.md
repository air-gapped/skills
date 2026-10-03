# Testing triage

A five-finding fixture ships at `fixtures/canary-findings.json` (2 real, 1
dup, 2 FP). Its findings cite `targets/canary/entry.c` from the defending-code
reference harness (see `../../vuln-scan/HARNESS.md`); to run the smoke test, clone
that harness and point `--repo` at it:

```
/triage <skill-dir>/fixtures/canary-findings.json --auto --repo <harness>/targets/canary
```

Expected: f001 and f003 confirmed; f002 duplicate of f001; f004 dropped
(`misread_code`: it's a read buffer, not a randomness source); f005 dropped
(`already_handled`: there is a null check at line 68). Without the source
tree the verifiers cannot read the cited code, so they return
`needs_manual_test` — the fixture then documents the ingest/dedup shape rather
than exercising verification. Its findings carry no `source_ref`/`sink_ref`
(most scanners emit none), so it exercises the refs-absent path: f001/f002
must still collapse on the line window alone.

Against any real scanner output, hand-check a sample of TRUE_POSITIVE/HIGH
results (the `first_links` should point at real call sites) and a sample of
FALSE_POSITIVE rejects (the `exclusion_rule` or `refute_reasons` should be
defensible).
