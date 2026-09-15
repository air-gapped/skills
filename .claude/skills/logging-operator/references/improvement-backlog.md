# Improvement backlog — logging-operator

Gaps carried from the 2026-07-22 research pass (report:
`.claude/skills/autoresearch/results/logging-operator-research-2026-07-22.md`).
Address opportunistically during freshen/improve passes.

## Resolved — 2026-09-15 (a conflict that does not exist at runtime)

- **T6 trigger conflict with `rancher-logging-exit` — CLOSED.** The entry
  documents that the over-firing appears **in isolation only**, and that it is
  "resolved in the REAL both-installed runtime" because the sibling's description
  is strictly more specific on that territory and fires 1.00 on both contested
  queries. Its own unblock condition — "only act if real-session misrouting is
  observed" — has not been met.
- The residual cause is legitimate and should not be edited away: this skill
  documents CVE-2026-54680 as its upstream **version floor**, so it has to carry
  the keyword. Removing it to win an isolation probe would trade a real fact for
  a synthetic score.

## Checked 2026-09-15 — no change needed

- **The CVE floor is correct and comfortably conservative.** `kube-logging/logging-operator`
  has exactly **one** published security advisory,
  **GHSA-mjqf-28ph-426h = CVE-2026-54680** (critical, 2026-06-08, Fluentd
  configuration injection allowing remote code execution), affecting
  **`<= 6.5.2`**. This skill's documented floor is **6.7.0**, which clears it
  with room to spare. No newer advisory exists.
- Recorded so a later pass does not re-derive it: the advisory's
  `first_patched_version` is **null**, as it is for every upstream checked in
  this pass, so the `<= 6.5.2` ceiling is what establishes the floor. Anyone
  re-checking should read the range, not the patched field.

## Open

## Research gaps (carried 2026-07-22)

- **6.6.0/6.7.0 escaping character table**: the CVE fix changes rendering of values
  containing quotes/backslashes/#/newlines; direction verified but the exact
  per-character diff (#2254/#2255 PR diffs) was never opened. Before asserting a
  concrete table, read those PRs.
- **Flow Select `namespace_labels` asymmetry**: generated docs show it under Flow's
  Exclude but not Select (ClusterFlow has both). Confirm against flow_types.go
  before asserting either way.
- **Telemetry Controller hands-on smoke test** never run — the "usable standalone
  with caveats" verdict is docs/source-based. If TC reaches 1.0/v1beta1, rerun the
  assessment and revisit the LoggingRoute-first recommendation.
- **syslog-ng recipe depth**: only quickstart + samples-level chains covered
  (OTLP, http, openobserve). If syslog-ng mode becomes a real deployment here,
  do a dedicated recipe pass (parser/rewrite filters, disk-buffer sizing).
- Live-validation status: recipes were verified against official
  quickstarts/samples and source defaults, not yet end-to-end on a cluster by this
  skill's authorship pass. First real use on the lab cluster should confirm the
  minimal chain + CRI flag behavior and note any drift here.

## Resolved — 2026-07-23 (trigger mode)

- **Description exceeded the 1024-char hard cap** (was 1093 → `skills-ref
  validate` would reject) and combined description+when_to_use exceeded the
  1536 listing cutoff (was 2243), silently truncating the sibling-routing
  clause out of the visible listing. Rewrote frontmatter tightly (desc 688,
  combined 1523) and pulled the rancher-logging-exit routing clause into the
  visible window. Trigger probe held pass counts (train 9/10, test 4/5) while
  halving the description; the CVE-rancher over-trigger improved 1.00→0.67 as
  the routing clause began registering. Baseline was already strong (13/15);
  residual over-triggers are the T6 item above, not a description defect.
