# Improvement backlog — rancher-logging-exit

Gaps carried from the 2026-07-22 research pass (report:
`.claude/skills/autoresearch/results/logging-operator-research-2026-07-22.md`).

- **Live dry-run of Strategy A** on the lab cluster (`local` context — currently a
  State-2 debris specimen, so it exercises the debris path; a kind/k3d cluster
  with rancher-logging installed would exercise Strategy A proper). The runbook
  rests on primary-artifact analysis + the maintainer blog, not a 2026 field run.
- **Exact deployment/DaemonSet names in runbook step 1/4** were written from chart
  templates (`rancher-logging` deploy, `<release>-rke2-journald-aggregator` DS) —
  confirm against a real install on first use; note drift here.
- **Escaping character table** (shared with logging-operator backlog): open
  #2254/#2255 diffs before asserting which characters change in rendered config.
- **SUSE response watch**: if SUSE ships an advisory/backport for CVE-2026-54680,
  the urgency section must be rewritten same-day (see sources.md watch-list).
- **Image-override field spellings** in airgap-prep.md values skeleton
  (configReloaderImage, bufferVolumeImage, drain images) were taken from the CRD;
  validate the exact paths against a rendered 6.7.0 install once.
- No 2026 community war stories for this exact migration surfaced — collect the
  first real execution's findings (timings, surprises) into a dated log here.

## Resolved — 2026-07-23 (trigger mode)

- **Description exceeded the 1024-char hard cap** (was 1241 → `skills-ref
  validate` would reject) and combined description+when_to_use exceeded the
  1536 listing cutoff (was 2429). Rewrote frontmatter tightly (desc 738,
  combined 1506). Trigger probe: baseline train 10/10, test 3/4 → final train
  10/10, test 4/4 (converged, 14/14). The cap-fit rewrite also cleared the
  one over-trigger — a generic Rancher-version-upgrade decoy that had fired
  0.67 — by surfacing the "not for generic Rancher upgrades" negative into the
  visible listing window. Cross-skill negatives vs the logging-operator sibling
  held at 0.00 throughout (no shadowing). Eval set: references/trigger-evals.json.

## Open

- (none from the trigger pass — converged clean at 14/14.)
