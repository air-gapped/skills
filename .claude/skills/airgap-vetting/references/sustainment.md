# Q7 — Sustainment: Can It Be Kept Alive Offline?

**Contents:** staleness behavior (fail-closed/warn/silent) · low-cost feed
mechanics · high-cost patterns · offline upgrades · sync tooling · ML model
updates · what to record.

Questions 1–6 are day-one; this is day-two. Three parts: how product
upgrades cross the gap, how content feeds (vuln DBs, rules, models) stay
fresh, and what the product does when they don't.

## Staleness behavior — first-class vetting signal

Search the candidate's codebase for an age-validation constant vs
schema-only validation. **Fail-closed beats warn beats silent.** The
spectrum:

- **Fail-closed (best)** — refuses to run on a feed older than a named age
  limit unless the operator consciously overrides it. The failure is
  visible; find the constant and the override knob.
- **Warn, fail-open** — prints a loud warning and keeps working.
  Acceptable; document the exact warning string so operators can alert on
  it.
- **Silent (worst)** — with updates skipped, validates *schema version
  only*; an arbitrarily old feed runs without warning and reports green on
  stale data. Check whether feed metadata (build timestamp / next-update)
  is at least exposed so an ops pipeline can check age externally — the
  tool itself won't.

A security feed that silently reports green on stale data caps the grade at
`possible-with-mirror` with an explicit warning in the verdict. Dynamic
confirmation: the stale-feed run (`references/dynamic-harness.md` step 7).

## Feed mechanics — low-sustainment-cost patterns (green flags)

- Feed published as **OCI artifact** on a public registry — mirror with
  `oras pull` or plain registry replication (replication then doubles as
  feed sync); look for a repository-redirect flag pointing consumers at
  the internal copy.
- Feed as **plain HTTPS artifact** with an update-URL override and an
  offline import subcommand.
- **Official mirror tool** maintained by the vendor (incremental patches,
  cron-able).
- **Git-mirrorable rules/DB** with remote-URL / local-path /
  update-disable knobs.
- **Mirror-and-re-serve** — the product mirrors an upstream feed and
  re-serves it to its own components. Attached lesson: upstream feed
  formats and endpoints get retired; the mirroring *mechanism* is itself a
  staleness risk — pin it and re-vet it periodically, not just the data.
- **Published build cadence** in feed metadata ("built every N hours") —
  lets the sync pipeline be sized.

## High-sustainment-cost patterns (red flags)

- **Feed reachable only via SaaS API at runtime** — never cached, cannot
  run offline; sustainment means vendoring the ruleset/data yourself and
  losing upstream updates.
- **No feed artifact at all** — the tool queries package registries or
  upstreams live, so air-gap operation requires standing mirror
  infrastructure (Artifactory/Nexus-class) plus per-ecosystem host rules.
- **Lockstep version-pinned companions** — a registry/executor/companion
  image that must exactly match the deployed product version multiplies
  the artifacts per upgrade hop.
- **Docs-vs-behavior gaps** — "offline mode" flags that still leave one
  component fetching; search the tracker for issues titled "not fully
  disconnected" / "still calls home with offline set".

## Offline upgrades (product itself)

- Best pattern: a documented **artifact/tarball drop-in per hop** with no
  internet needed mid-upgrade (include any upgrade-controller images in
  the mirror list).
- **Delta-capable mirroring** (incremental since-date mirroring,
  differential packages) beats full re-hauls as the install grows.
- **Mandatory sequential version stops** multiply gap crossings — every
  intermediate package must cross the gap.

**Count the gap crossings**: sequential-stop upgrade paths are a
quantifiable sustainment cost. Report it as artifacts-per-hop × hops.

## Sync/mirror tooling (2026 state — for the recommendation section)

Zarf `package create --differential <previous-package>` (omits
already-shipped version-pinned images/repos); Hauler declarative
`hauler-manifest.yaml` + `store sync`/`save`/`load` hauls with an embedded
registry; Replicated `.airgap` bundles (full, not delta) with a documented
recurring update loop; oc-mirror v2 (cache-based incremental, `--since`,
`mirrorToDisk`→`diskToMirror`, two-phase `delete`); registry replication
for OCI-artifact feeds.

## ML model updates

Models published as **plain artifacts with a repository/mirror override**
are the green flag; LLM weights transferred as filesystem files mean every
model update is a full re-transfer. Either way, models go on the mirror
list with a size estimate — they are often the largest thing crossing the
gap.

## What to record for the verdict

For each feed: mechanism, override flag, upstream cadence, staleness
behavior (fail-closed/warn/silent). For upgrades: gap crossings per hop.
For the whole candidate: one-time mirror vs standing sync pipeline, and the
minimum sync cadence before the product becomes stale-dangerous.
