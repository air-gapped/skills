# Improvement backlog — harvester-upgrade

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Open

- **Dim 7 (Resource Quality, ~7 — neutral ceiling) — no bundled scripts, by design.** The skill points at the
  upstream `harvester/upgrade-helpers pre-check/v1.x/check.sh` rather than reinventing a pre-flight script, and
  the detection/gate commands are short kubectl one-liners. Adding a bespoke script to lift Dim 7 would
  duplicate upstream + add maintenance burden (House Rule spirit: use the real artifact). Attempted as an
  iteration hypothesis and rejected — lifting Dim 7 needs author judgment on whether a genuinely additive
  script (e.g. a guest-etcd-quorum watcher to pair with the 1.7 pause-map) is worth bundling. Not mechanical.
- **Dim 9 (Domain Accuracy, 9 not 10) — volatile leaf numbers are re-grounded, not static.** The skill
  deliberately tells the model to re-ground latest-patch numbers / GA dates / "fixed in vX" via `gh` (House
  Rule #2), so it cannot read as a frozen authoritative reference doc (the rubric's 10). This is correct design,
  not a defect — the cap is inherent and should not be "fixed."
- **Dim 4 (Actionability, 8 per blind) — version-targeting defers to `gh`-grounding.** A few steps (pick the
  target patch, confirm latest GA) intentionally defer to live `gh` grounding rather than hardcoding volatile
  versions. Correct per House Rule #2; means the skill alone isn't 100% turnkey. Not fixable without violating
  the anti-fabrication rule.

## Resolved this pass (2026-06-02)

- **Dim 3 (Writing Style) 7 → 9** — converted 16 second-person (`you`/`your`) occurrences across the reference
  files to imperative/declarative (controlled-flow 6, guest-rke2 4, external-rancher 1, version-ladder 2,
  landmines 1, per-hop 1). One verbatim doc quote (`"you must upgrade Rancher…"` in external-rancher-coupling.md)
  left intact as a source citation. SKILL.md body was already 0 second-person.
- **Dim 2 (Progressive Disclosure) 8 → 9** — added a Contents/TOC to `guest-rke2-survivability.md` (157 lines);
  both >100-line references now have one (controlled-flow already did).
- **Dim 6 (Simplicity) 7 → 8** — trimmed the three SKILL.md house rules (Rancher-leads, structural-safety,
  no-downgrade) that restated the load-bearing facts down to crisp pointers (`fact 2`, `facts 3–4`, `fact 5`),
  keeping only their incremental content. Addressed the baseline blind agent's top simplicity finding.
- **Freshen (2026-06-02)** — re-probed the most volatile claim: `gh release list -R harvester/harvester`
  confirms **v1.8.0 still latest GA, no 1.9.0 GA, prerelease flags unchanged**. All sources 1–2 days old → no
  staleness cap; no content mutations needed. Stamped the releases ledger row.

### Tried-and-discarded this pass (ceiling evidence)
- **Simplification (iter 4):** moving the inline pre-flight gate list fully into the reference left a hollow
  "Pre-flight gates" heading and removed the run-every-hop at-a-glance checklist — net D6 +1 but D4/D5 −1.
  Reverted: the inline quick-ref + full-table-in-reference is correctly-applied Pattern 2.1, not redundancy.
- **Frontmatter (iter 5):** evaluated `allowed-tools` (would constrain this advisory skill's diverse
  Read/Grep/Bash work; peer `rancher-upgrade` omits it), `effort: high` (speculative; forces max reasoning on
  every trigger incl. trivial version questions), `disable-model-invocation`/`user-invocable:false` (wrong —
  must auto-trigger), `paths`/`context:fork` (N/A). None improves the rubric; not applied.

Self-score 84 → ~89; baseline blind 86. Stop: **ceiling mapped** (2 discards across 2 categories). Remaining
headroom (Dim 7 no-scripts, Dim 9 volatile-leaves, Dim 4 version-deferral) is structural-by-design — changing
it would make the skill worse, not better.
</content>
