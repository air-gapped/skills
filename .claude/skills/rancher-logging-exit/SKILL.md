---
name: rancher-logging-exit
description: >-
  Migrate off the Rancher-bundled `rancher-logging` chart (cattle-logging-system,
  rancher/mirrored-kube-logging-* images) to the upstream kube-logging
  logging-operator ≥6.7.0 — air-gap-first. Rancher 2.11 through 2.15-dev all
  bundle a frozen operator 4.10.0 that is inside the affected range of
  CVE-2026-54680 (CVSS 9.9 config-injection RCE, no SUSE fix) — so the exit is
  security-urgent. Covers the maintainer-endorsed helm-release-secret strategy
  (near-zero gap; NOT `helm uninstall rancher-logging-crd`, which
  cascade-deletes every CR and the data plane), CR compatibility 4.10→6.7
  (silent field pruning), server-side CRD apply (828KB CRDs), buffer-PVC
  preservation, air-gap image/chart mirroring, rollback, and stale-CRD debris
  cleanup.
when_to_use: >-
  Use for anything about leaving or reconciling Rancher's bundled logging:
  migrate rancher-logging to upstream, uninstall it safely, its frozen
  operator version, whether `rancher-logging` / `cattle-logging-system` is
  exposed to CVE-2026-54680, or cleaning up leftover logging.banzaicloud.io
  CRDs / a `rancher-logging-crd` release. Triggers on
  rancher/mirrored-kube-logging images and 10x.y+up4.10.0-rancher.N chart
  versions. Air-gapped clusters are the primary audience. Not for: configuring
  a healthy logging-operator pipeline (use the logging-operator skill); a
  generic Rancher version upgrade (2.x→2.y) or upgrading another Rancher chart
  (monitoring, etc.) when logging is not the subject; or the legacy
  pre-operator `clusterloggings.management.cattle.io` v1 logging.
argument-hint: "[why|runbook|airgap|cr-compat|debris|rollback] (optional focus)"
---

# rancher-logging-exit — Rancher-bundled → upstream logging-operator

Migration reference, verified 2026-07-22. Target: **upstream ≥6.7.0** (6.6.0 fixes
the CVE but breaks newline-containing passwords, #2254 — 6.7.0 has the corrected
fix). Version matrix authority: `k8s-components-checker`
`references/compat/rancher-logging.md`. Day-2 configuration of the migrated
pipeline: the **logging-operator** skill.

## Why migrate (the honest urgency statement)

- **Frozen**: every Rancher minor 2.11 → 2.14 (and 2.15-dev) ships the same
  upstream base **operator 4.10.0** (Oct 2024) — only `-rancher.N` chart respins.
  The `-rancher.N` fork is **chart-level only** (rancher/ob-team-charts); the
  operator image is a stock upstream mirror. "Wait for Rancher" has been dead for
  20+ months of releases.
- **CVE-2026-54680** (GHSA-mjqf-28ph-426h, CVSS 9.9): operator ≤6.5.2 renders
  CRD/secret values into fluent.conf unescaped — a newline in a Flow/Output field
  or referenced Secret injects arbitrary fluentd directives (`<match **>
  @type exec` ⇒ RCE in the aggregator). 4.10.0 is affected; the fix exists only on
  the 6.x line; **no SUSE fix exists as of 2026-07-22** (verified: SUSE CVE page
  404, NVD reserved, Rancher advisories silent, no ob-team-charts logging commits
  post-CVE) and none CAN ship as a chart respin.
- **Who can trigger it**: the chart aggregates a `logging-admin` ClusterRole
  (verbs `*` on flows/outputs) into the k8s `admin` role ⇒ **any Rancher
  project-owner**. Blast radius: the aggregator holds every output credential and
  any IRSA/Workload-Identity role annotated onto its SA. Same vuln class as
  Rancher's 2019 CVE-2019-12303.
- Also stale: fluent-bit 3.1.8 (in-range for the Nov-2025 five-CVE set — though
  NOT exploitable in the default tail→k8s-filter→forward pipeline; frame as
  "outdated", not "default RCE"), fluentd v1.16 (upstream at 1.19).
- Not formally deprecated — Rancher docs still describe it. The story is
  "abandonware with an open critical", not EOL notice.

## Strategy selection

| Situation | Strategy | Reference |
|---|---|---|
| Healthy bundled install, minimal gap wanted (default) | **A: release-secret surgery** (maintainer-endorsed) | `references/runbook.md` |
| Want a clean slate / config redesign anyway | B: backup → uninstall → reinstall (corrected) | `references/runbook.md` §B |
| Stale debris: old CRDs + orphaned CRs, no operator running | Debris cleanup then fresh install | `references/entry-states.md` |
| Windows nodes using nodeAgents | STOP — no 6.x path; plan separately | `references/cr-compat.md` §nodeAgents |

**Strategy A in one breath**: mirror images/chart (air-gap step zero) → back up all
CRs + rendered config → scale down the rancher operator → back up then **delete the
`sh.helm.release.v1.rancher-logging.*` and `...rancher-logging-crd.*` Secrets**
(releases vanish from Helm/Rancher UI; CRDs, CRs, and the running fluentd/fluent-bit
keep working) → server-side-apply 6.7.0 CRDs → helm-install upstream operator
reusing the Logging name `rancher-logging-root` + controlNamespace
`cattle-logging-system` (preserves buffer PVCs) → validate → clean up Rancher
extras. Near-zero collection gap.

**Never run `helm uninstall rancher-logging-crd` on a live install**: the CRD chart
has **no `helm.sh/resource-policy: keep`** — uninstall deletes the CRDs, the API
server cascade-deletes every CR, and the operator-owned fluentd/fluent-bit go with
them. Full collection outage, possible config loss.

## The five technical facts the whole migration hinges on

1. **API group/version identical** both sides (`logging.banzaicloud.io/v1beta1`
   storage) — backed-up CRs re-apply cleanly, no conversion.
2. **Failure mode is silent pruning, not errors**: fields removed 4.10→6.7
   (sumologic, enhanceK8s, ClusterOutput `enabledNamespaces`, nodeAgents) are
   silently dropped on re-apply. Pre-flight: server-side dry-run diff
   (`references/cr-compat.md`).
3. **CRD applies must be `kubectl apply --server-side --force-conflicts`** —
   828KB/557KB CRDs exceed the client-side annotation limit. Also: the upstream
   chart's `crds/` dir is **silently skipped** when any CRD already exists — a
   naive install runs 6.7 against stale 4.10 schemas with no error.
4. **Buffer PVCs survive** iff Logging name + controlNamespace are preserved
   (StatefulSet `<logging>-fluentd`, volume `fluentd-buffer` — stable across
   4.10→6.7). Deleting cattle-logging-system destroys them.
5. **Escaping cutover check**: 4.10 renders values unescaped, 6.7 escapes —
   capture the rendered `*-fluentd-app` secret before, diff after, for any value
   containing quotes/backslashes/newlines.

## Where to go next

| Task | Read |
|---|---|
| Full step-by-step runbooks (A: release-secret; B: clean reinstall) + validation | `references/runbook.md` |
| Air-gap prep: image list, OCI chart mirroring, values overrides (no systemDefaultRegistry upstream) | `references/airgap-prep.md` |
| CR field diffs, pruning pre-flight, escaping diff, Rancher-chart deltas (journald DaemonSets, Windows), rollback | `references/cr-compat.md` |
| Entry states incl. stale-debris cleanup and legacy v1 logging CRDs | `references/entry-states.md` |
| CVE detail, RBAC exploitability, fluent-bit CVE precision | `references/security-urgency.md` |
| Per-Rancher-minor chart/image matrix | k8s-components-checker `references/compat/rancher-logging.md` |
