# triage output templates (Phase 6)

Every template Phase 6 writes. SKILL.md Phase 6 holds the procedure (sort,
incremental writes, `checkpoint.py append`); this file holds the shapes. Fill
each `{...}` from working state.

## Contents

- [TRIAGE.json](#triagejson)
- [TRIAGE.md header](#triagemd-header)
- [Per-finding section](#per-finding-section)
- [Dropped table](#dropped-table)
- [Terminal summary](#terminal-summary)

## TRIAGE.json

```json
{
  "triage_completed": true,
  "triage_context": {
    "mode": "interactive|auto",
    "environment": "...",
    "threat_model": ["..."],
    "scoring": "...",
    "noise_tolerance": "...",
    "votes_per_finding": 3,
    "repo": "..."
  },
  "summary": {
    "input_count": 0,
    "duplicates": 0,
    "false_positives": 0,
    "true_positives": 0,
    "needs_manual_test": 0,
    "verifier_errors": 0,
    "by_severity": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
  },
  "findings": [
    {
      "id": "f001",
      "source": "VULN-FINDINGS.json#0",
      "title": "...",
      "file": "...",
      "line": 0,
      "end_line": null,
      "source_ref": "...|null",
      "sink_ref": "...|null",
      "threat_ids": [],
      "category": "...",
      "claimed_severity": "HIGH",
      "verdict": "true_positive|false_positive|duplicate",
      "verify_verdict": "exploitable|mitigated|needs_manual_test|reachable_no_impact|null",
      "confidence": 0.0,
      "severity": "HIGH|MEDIUM|LOW|null",
      "severity_label": "...",
      "severity_alignment": 0,
      "preconditions": ["..."],
      "access_level": "...",
      "asset": "...|null",
      "impact": "HIGH|MEDIUM|NONE_LOW|null",
      "exploitability": "HIGH|MEDIUM|LOW|null",
      "deployment_condition": "...|null",
      "threat_match": "...|null",
      "rationale": "file:line-cited prose: reachability, protections, why each held or didn't; then ranking rationale",
      "vote_breakdown": {"true_positive": 0, "false_positive": 0, "cannot_verify": 0},
      "refute_reasons": ["..."],
      "exclusion_rule": null,
      "first_links": ["file:line", "..."],
      "duplicate_of": null,
      "absorbed": ["..."],
      "owner_hint": "...",
      "missing_fields": ["..."]
    }
  ]
}
```

## TRIAGE.md header

```
# Triage Report

{summary line: N in -> D duplicates, F false positives, T confirmed (H high / M med / L low), X need manual test{if verifier_errors: , E verifier-error votes — see flagged findings}}

Context: {mode}; environment = {environment}; scoring = {scoring}; {votes}-vote verification.

## Act on these
```

## Per-finding section

```
### [{severity}] {title}  ({id})
`{file}:{line}` | {category} | claimed {claimed_severity} (alignment {severity_alignment:+d}) | confidence {confidence}/10
**Owner:** {owner_hint}
**Verdict:** {verify_verdict}, votes {vote_breakdown}
**Asset:** {asset} — impact {impact} x exploitability {exploitability}
**Moves if:** {deployment_condition or "nothing — severity is unconditional"}
**Preconditions ({n}):** {bulleted}
**Threat-model match:** {threat_match or "none"}
**Why:** {rationale}
**Reachability evidence:** {first_links}
{if source_ref or sink_ref:}**Claimed flow:** {source_ref or "?"} -> {sink_ref or "?"} (scanner-asserted; the verifier's reachability evidence above is what was read)
{if verify_verdict == needs_manual_test:}
> Recommend a human build a PoC; static reasoning hit its limit.
{if "verifier_error" in refute_reasons:}
> {n} of this finding's votes were verifier ERRORS, not verdicts — the
> remaining votes decided. Weigh accordingly.
```

## Dropped table

```
## Dropped

| id | title | file:line | why dropped |
{false_positives: refute_reasons + exclusion_rule}
{duplicates: "duplicate of {duplicate_of}"}
{unlocatable: "no source location in input"}
```

## Terminal summary

```
Triage complete: {N} findings -> {T} confirmed, {F} false positives, {D} duplicates.

  HIGH:   {n}   {title of top HIGH, owner_hint}
  MEDIUM: {n}
  LOW:    {n}
  Needs manual test: {n}

  Top refute reasons: {top 3 refute_reasons with counts}

Wrote ./TRIAGE.md and ./TRIAGE.json

Next step: > /patch ./TRIAGE.json --repo {repo}
```
