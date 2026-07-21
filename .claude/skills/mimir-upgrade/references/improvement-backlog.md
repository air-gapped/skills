# Improvement backlog — mimir-upgrade

Work-not-done log across skill-improver runs. Append-only history; not a wishlist.

## Open

### No claim has been behaviourally observed on a cluster (Dim 9 / integrity)

- **What:** the claims are documentation- and source-grounded, not behaviourally observed. No lab cluster
  existed at authoring time (prod is air-gapped; the lab Mimir install was decommissioned as too large to run
  continuously). This is a narrow gap, not an absence of rigour — see SKILL.md §"Evidence tags" for what the
  research did cover, including two claims settled by experiment (a golden-CI-fixture render diff and a Go
  probe against Mimir's YAML library).
- **Why it could not be closed:** requires a cluster. Not fixable by reading.
- **Highest-value validations, in order,** if a lab is ever available:
  1. That `classic-architecture.yaml` produces a *working* 6.x cluster, not merely a clean render — specifically
     that a live Mimir accepts `ingest_storage.kafka.address: null` through its `Validate()` path. The decode
     was proven against Mimir's YAML library; the validate path was not.
  2. That an in-place 5.7.0 → 6.x classic upgrade preserves ingestion across the ingester roll.
  3. That the nginx→gateway `nameOverride` migration genuinely preserves client connectivity end to end.
- **Do NOT** silently upgrade `[RFC]` tags to `[UG]` on the strength of "it looks right". The tag distinction is
  the skill's integrity.

### Fleet-facts interview answers are unknown (Dim 4)

- **What:** Step 0 asks five questions the skill cannot answer for itself. Until a real fleet answers them, the
  runbook necessarily hedges — most visibly around nginx-vs-gateway (§3 of `per-hop-runbook.md`), where the
  entire hop-2 risk profile depends on the answer.
- **Why not closed:** requires cluster access the author did not have.
- **Next pass:** if the operator supplies answers, consider a worked example section pinned to that fleet's real
  shape — but keep the generic interview, since the skill outlives one fleet.

### MQE differencing rig is assembled, not documented (Dim 5)

- **What:** `verification.md` §7 describes a query-tee rig built from documented primitives (query-tee flags +
  an engine-pinned second query path). Upstream describes having done this in staging but **publishes no
  procedure**.
- **Why not closed:** there is no upstream runbook to cite, and no lab to test the rig in. Tagged `[RFC]`
  accordingly.
- **Next pass:** re-probe for an upstream query-tee runbook; if one appears, replace the reconstruction and
  re-tag.

### Kafka sizing has no upstream guidance (Dim 5)

- **What:** `architecture-decision.md` §6 extrapolates from a single community datapoint (~2 GB/day per 1k
  samples/s at 24 h retention) because upstream publishes none — tracked in grafana/mimir#12012 and #14008, both
  open.
- **Why not closed:** the guidance does not exist yet.
- **Next pass:** check whether #14008 landed capacity-planning docs for ingest storage; if so, replace the
  extrapolation with the real numbers.

### Chart 6.1.x may supersede 6.1.0 (Dim 9)

- **What:** the ladder terminates at 6.1.0 / app 3.1.2, but app 3.1.3 exists upstream and a 6.1.x patch chart may
  land.
- **Why not closed:** correct at authoring time; this is a freshen concern, not a defect.
- **Next pass:** re-derive the terminal hop from `k8s-components-checker` → `compat/mimir.md` rather than
  updating numbers here. This skill deliberately holds no version matrix.

## Resolved — 2026-07-21 (skill-improver improve, 5 iterations)

Baseline blind 81 → final blind 82. Self-score peaked at 87, so **the self-scoring ran ~5 points
optimistic** — the blind agent is the reason this run has a truthful number.

- **Iter 1 (81→82):** corrected the "nothing is field-validated" framing. It read as "unresearched" to a
  domain expert, when the intended meaning was "not behaviourally observed on a cluster". SKILL.md now
  states what the research *did* cover, including the two experimental results.
- **Iter 2 (82→85):** 74 second-person constructions → imperative/impersonal. The 3 remaining are verbatim
  upstream quotes and a `<your-values>` placeholder.
- **Iter 3 (85→86):** added `improvement-backlog.md` to the References table; removed a "this skill
  previously repeated it" line that described a revision history the file's own record contradicts.
- **Iter 4 (86→87):** sharpened house rule #1. The rule said "no version numbers here" while the ladder and
  image tags plainly appear. Restated as **no floor, support window, or legality verdict is decided here** —
  which is what the skill actually does — plus what to do when example and registry disagree.
- **Iter 5 — REGRESSED, then repaired.** Adding `scripts/audit-values.sh` dropped blind Dim 7 from 8 to 6:
  the final blind agent *executed it against planted keys* and found the LOUD half caught **1 of 6**
  crashloop keys, because the list used hyphenated CLI-flag spellings that cannot occur in a
  `structuredConfig` block (underscored). Plus two more: a dead-code branch (piping `grep -n` output, which
  begins with digits, into a `^\s*key:` anchor) and an `image.tag` check that any `tag:` at any indent —
  e.g. `kafka.image.tag` — silently satisfied. All three fixed; `scan_key()` now matches either spelling,
  and the re-test catches 7/7 planted keys. **A script that gives false assurance on the crashloop half is
  worse than no script**, which is precisely why the loop's own +score for "bundled a script" was wrong
  until an adversary ran it.
- **Cross-skill correction:** the blind agent found this skill and `k8s-components-checker/compat/mimir.md`
  contradicting each other on `kubeVersion` enforcement. Settled by experiment, not memory: `helm template`
  of `mimir-distributed-6.1.0` (`^1.32.0-0`) **passes** under helm 3.17.3 with no flag and **fails** with
  `--kube-version 1.31.0`. So the constraint is checked against `.Capabilities.KubeVersion` — the API server
  for install/upgrade, helm's compiled-in default for `template`. **kubectl is not involved.** The registry's
  "checks the kubectl client version" claim (predating this session) was wrong and has been corrected there.

## Resolved — 2026-07-21 (initial authoring)

Built from a six-agent autoresearch pass. Notable corrections that the research forced into the skill, all of
which contradicted the starting assumptions:

- **Classic architecture is supported, shipped, and CI-tested** — the premise that the override was
  undocumented was wrong. The chart ships `classic-architecture.yaml`; the migration guide has a dedicated
  section; upstream regression-tests it with golden manifests.
- **MQE became the querier default at 2.17, not 3.0** — moving the read-path risk to hop 1 and changing the
  recommended sequencing (pin the engine through 5.8.0, flip separately).
- **The `kubectl rollout restart` prohibition is folklore** — no upstream document states it, and the
  "it errors on `OnDelete`" variant is disproven by kubectl source. The real mechanism is defused by the
  chart's `unregister_on_shutdown: false` pin; the genuinely dangerous case is single-zone.
- **Four chart-CHANGELOG claims are wrong** (querier `max_concurrent`, GEM port 8080, Helm v4, rollout-operator
  version) — recorded in `per-hop-runbook.md` §7 with the tarball evidence, since a future reader will hit the
  same changelog.
- **The nginx→gateway break is community-specific**, which is why it is under-reported: enterprise fleets
  already ran `gateway` and never saw it.
