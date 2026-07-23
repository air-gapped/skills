# Improvement backlog — skill-improver findings

Carries ceiling findings across skill-improver runs. Do not re-propose Open
items without new evidence.

## Open

- **Move the Backlog section out of SKILL.md body** (Dim 2/6) —
  SKILL.md:~190-215. Both blind scorers docked Dim 6 for author-facing
  maintenance state in the model-facing body, and relocating it is the main
  path toward the <150-line Dim 2 top band. Not applied: the author
  deliberately made SKILL.md the canonical backlog location (2026-07-23
  decision) so time-sensitive correctness guards (e.g. "don't deploy Redfish
  on iDRAC 10 until #202 ships") load with the skill. Requires author
  sign-off on moving guards elsewhere without losing their visibility.
- **Cross-file fact dedup** (Dim 6) — timeout math and v3-auth guidance
  appear in SKILL.md golden rules, references/kubernetes.md, and example
  comments. Final blind scorer cited the repetition; deduping is a multi-file
  restructure that risks removing point-of-use context (each restatement is
  where a reader acts on it). Attempt only with a utility test, not for
  score.

## Resolved — 2026-07-24 (freshen-style correction, post-run)

- **Trap-direction error fixed**: companions.md claimed
  "prometheus-community/snmp_notifier" receives device traps into
  Alertmanager. Verified online 2026-07-24: the project is
  **maxwo/snmp_notifier** and it is **outbound-only** (relays Alertmanager
  alerts out as SNMP traps for a legacy NMS) — as are
  SUSE/prometheus-webhook-snmp and the webhook-snmptrapper forks. Replaced
  the inbound recommendation with Telegraf's `snmp_trap` input (+
  prometheus_client output) or an snmptrapd traphandle → Alertmanager API
  script; fixed SKILL.md, companions.md, research-report.md, sources.md.

## Resolved this pass — 2026-07-24

Run: improve mode, baseline 81 → final 90 (self), blind 80 → 88.
8 kept iterations + 2 blind-flag fixes, 0 discards (no ceiling mapped —
stopped on the 90+/no-dim-below-7 condition).

- Added `references/sources.md` (100% dated rows, 2026-07-23) — lifted the
  Dim 9 staleness cap (6 → 9).
- Fixed CBS curated metric count 30 → 63 in SKILL.md (verified against
  generated snmp-cisco.yml).
- Second-person sweep: SKILL.md (10 → 0) and all instructional references
  (9 → 0); research-report.md exempt as background narrative.
- De-orphaned research-report.md (linked from SKILL.md, marked
  "background only").
- Added TOCs to all four >100-line reference files.
- Merged the duplicate numeric-OID pitfall into the Writing-modules section
  (net lines removed).
- Added edge triggers (snmpwalk, SNMP traps, Probe/ScrapeConfig CRDs), then
  split frontmatter into `description` + `when_to_use` (final blind scorer's
  Dim 1 flag).
- Labeled the distinct metric-count measurements (4034 generated vs 5223 in
  snmp_exporter#1229; 554 full-generation vs 512 upstream `dell` module) in
  cisco-cbs.md and generator-idrac.yml (+ mirrored to the working
  generator/ copy).
