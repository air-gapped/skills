---
name: k8s-components-checker
description: >-
  Survey an RKE2 community cluster against an embedded compatibility registry of
  18 stack components and produce a verdict for upgrade-readiness, drift-review,
  and version-skew questions. Components: RKE2, Rancher, Harvester, Cilium,
  cert-manager, Kyverno, KEDA, Argo CD, Harbor, Traefik, Rook, Ceph, OpenEBS,
  GitLab, ECK, Zalando postgres-operator, Grafana Mimir, NVIDIA GPU Operator.
  Works air-gapped — all per-component compatibility data lives in
  `references/compat/` and is maintained out-of-band by
  `skill-improver freshen`. Surveys run via `kubectl` + `helm` + `pluto` + the
  apiserver `apiserver_requested_deprecated_apis` metric from the operator's
  workstation. Community editions only — Prime/EE-gated content is ignored.
  NOT for installing components, NOT for executing upgrades, NOT for tracking
  per-cluster running state (the registry is methodology, not inventory).
allowed-tools: Bash(kubectl *) Bash(helm *) Bash(pluto *) Bash(jq *) Read Grep Glob
when_to_use: >-
  Use whenever the user asks about cross-component compatibility on Kubernetes /
  RKE2: "are we good to upgrade RKE2 from 1.X to 1.Y", "what breaks if I bump
  k8s", "is Cilium A compatible with k8s B", "stack drift review",
  "pre-upgrade survey", "blast radius of bumping X", "version skew", "components
  audit against k8s 1.NN", "what's the supported range of Y on k8s Z", "Harvester
  to Rancher pairing", "RKE2 leaf compatibility", "GPU Operator vs k8s minor",
  "Mimir Chart kubeVersion", "ECK against k8s 1.NN" — even when the user does
  not name the skill or the registry explicitly. Also trigger on cluster-survey
  requests using kubectl + helm + pluto + the apiserver deprecated-API metric.
---

# k8s-components-checker

Survey an RKE2 community cluster, cross-reference against the embedded
compatibility registry, produce a verdict. Community editions only. Air-gapped
at use time — `references/` carries everything needed; no internet calls during
a survey.

The registry is **methodology**, not inventory. It encodes which versions of
which components are compatible with which Kubernetes minors. It does not — and
must not — record what's actually running where.

## Quick decision guide

| Task | Go to |
|------|-------|
| Run a survey + answer an upgrade-readiness question | § Survey workflow below |
| Look up one component's k8s support window | `references/components.md` |
| Read what changed for compat in a specific component minor | `references/compat/<comp>.md` |
| Which kubectl/helm/pluto commands to run, and how to parse output | `references/cluster-survey.md` |
| Which deprecated-API tools to trust and how | `references/tooling.md` |
| Source URLs + last-verified timestamps (read-only — `freshen` writes here) | `references/sources.md` |

## Survey workflow

The operator runs the skill against a kubeconfig pointing at one cluster at a
time. Network access to the target cluster is assumed (direct or via
VPN/bastion). No internet calls. Five steps:

1. **Identify the change set.** Pin down what's being upgraded and from what
   to what. Five shapes the skill answers:
   - **anchor bump** — `k8s <current> → <target>` (e.g. RKE2 1.32 → 1.34)
   - **single leaf** — `<component> <current> → <target>` (e.g. Cilium 1.18 → 1.19)
   - **combined** — multiple bumps in one upgrade window
     (e.g. `k8s 1.32 → 1.34 + Argo CD 3.0 → 3.2`)
   - **drift review** — no specific target; report what's stale / EOL'd / unpatched
   - **feasibility** — find the highest tolerable bump on one axis given the
     others are pinned (e.g. "highest Argo CD that supports our k8s 1.32")

   Current k8s from `kubectl version --output=json`; current component
   versions from the survey commands in `references/cluster-survey.md`.
2. **Detect installed components** — run the canonical survey commands in
   `references/cluster-survey.md`. Output: a list of `(component, version)`
   tuples covering the 18 registry entries that are actually present.
3. **Cross-reference against the registry** — for each detected component,
   read its row in `references/components.md` and (when version-specific signal
   matters) its `references/compat/<comp>.md`. Determine compatibility
   against the current k8s minor and, if relevant, the target k8s minor.
4. **Check deprecated-API liability** — read
   `apiserver_requested_deprecated_apis{}` from `/metrics` (canonical, never
   stale — the cluster reports what it has actually served), then run `pluto`
   against manifests/Helm releases for pre-apply static catch. See
   `references/tooling.md`.
5. **Emit a verdict** — structured per § Verdict format. The action plan
   respects upgrade-ordering rules from the relevant compat files.

If the operator asks for a *drift review* rather than an upgrade question,
steps 1–4 still run; step 5 reports against current k8s minor only (no target),
flagging components whose installed version is approaching or past upstream
EOL.

## Verdict format

The header carries the **change set** (see Survey workflow § 1) — anchor bump,
single leaf, combined, drift review, or feasibility. The per-row reason at the
end of each `✓ ready` / `⚠ needs bump` line is composed from the compat data
and is change-set-specific (`supports k8s 1.32..1.34` for an anchor bump,
`compat with target Cilium 1.19` for a leaf bump, `current version EOL'd
2025-10-07` for drift, etc.).

```
<cluster name or kubeconfig context> — <change set>

✓ ready
   - <component> <version>                    <change-set-specific reason>

⚠ needs bump
   - <component> <version> → ≥ <minimum>      <reason — what blocks the change set>
     source: references/compat/<comp>.md § <version>

⚠ ordering
   - <component A> must reach <version> BEFORE <component B> reaches <version>
     reason: <one-liner>
     source: references/compat/<a>.md § <version>

✗ blockers
   - <deprecated API>: still served (<N requests/day>) — source: <namespace/workload>
   - <component> <version>: <reason — current-state issue or change-set blocker>
     source: references/compat/<comp>.md § <version>

✗ out of registry scope
   - <component> <version>: below registry's min_tracked_version (<floor>);
     verdict abstained. Bump to a tracked version, or add an override in
     references/components.md.

action plan
   1. <ordered step>
   2. <ordered step>
   ...
```

`✓ ready` rows are noise after the first survey — collapse them by default in
follow-up surveys unless the operator asks for the full list. `⚠` and `✗` rows
always show.

**Verdict vs report.** The verdict above is the technical core, suitable for
in-conversation use and runbook PRs. When the operator asks for a *pre-upgrade
report* (for JIRA, change management, audit, mgmt review), wrap the verdict in
the layout from `references/report-format.md` — same content, recognizable
section skeleton across runs so prior reports compare cleanly.

## House rules

These are non-negotiable; encode them into every verdict.

1. **Community editions only.** Any Prime / EE / paid-tier feature, version, or
   support window is out of scope. Ignore SUSE Prime backports. Ignore GitLab
   EE-only features (the operator runs the EE binary as CE; treat as CE).
2. **Axis discipline.** A component's `axis_type` is `multi` only when the
   operator picks two or more dimensions independently. Container runtime,
   driver version, GPU architecture — all derived from other choices and
   therefore NOT axes. RKE2 → containerd is fixed; don't treat it as a variable.
3. **Min-tracked-version is overridable per component.** Default floor is
   "current + prior 2 minors" (~18 months). Operator overrides set per-component
   `min_tracked_version:` in `references/components.md`; `skill-improver
   freshen` respects overrides and trims unset rows.
4. **Apiserver metric is the truth source for deprecated APIs.** It reports
   what the cluster has actually served. Pluto's bundled rule set goes stale;
   use it for manifest-side static scans, never as primary. Kubent is dead
   (rulesets stop at k8s 1.32); do not use.
5. **Harvester ordering**: any survey involving Harvester + RKE2 must check the
   Harvester compat file for ordering rules before emitting an action
   plan. Some Harvester↔RKE2 combinations require Harvester to upgrade first;
   missing this turns the upgrade plan into a cluster-rebuild.
6. **Cite sources.** Every `⚠` and `✗` row carries a `source:` line pointing at
   the exact `references/compat/<comp>.md § <version>` block that
   produced the finding. No unsourced verdicts.
7. **Abstain when the registry is silent.** If the registry doesn't carry
   enough signal to verdict a row, abstain on that component and recommend
   running `skill-improver freshen <skill>` from an internet-accessible
   client.

## Truth-source-type — branch the lookup

Each component in the registry carries a `truth_source_type` field that says
*where the compat truth lives*. The skill branches on it when reading
`references/compat/<comp>.md`:

| Type | What the file contains |
|------|------------------------|
| `published_matrix` | Distilled rows extracted from the vendor's k8s support matrix, per-version. |
| `release_notes` | Sifted highlights from GitHub release notes — breaking, CRD, k8s floor, ordering. |
| `chart_metadata` | Helm `Chart.yaml`'s `kubeVersion:` constraint per chart-release tag, plus chart→app mapping. |

The branching matters at maintenance time (freshen probes different sources)
and at use time (the verdict cites a different kind of evidence per row).

## References

- `references/components.md` — the 18-entry registry (table for single-axis, stanzas for multi-axis). Carries `axis_type`, `truth_source_type`, source URL, `min_tracked_version`. The lookup table the survey reads.
- `references/cluster-survey.md` — the canonical command set: kubectl/helm/pluto/apiserver-metric. Detection patterns for mapping running workloads onto registry entries.
- `references/tooling.md` — apiserver `apiserver_requested_deprecated_apis` metric (primary), pluto (static manifest scan), kubent dead.
- `references/compat/README.md` — file-format spec for per-component compat files.
- `references/compat/<comp>.md` — one per component. The load-bearing per-version compatibility signal. Air-gap-complete.
- `references/sources.md` — URL index with `Last verified:` timestamps. Maintained by `skill-improver freshen`; read at use time only to surface staleness in the verdict if a row is past 90 days.
- `references/report-format.md` — pre-upgrade report layout: fixed section skeleton (header table, exec summary, survey, verdict, diff vs prior, action plan, methodology) with dynamic content. Used when the operator asks for a *report* rather than a verdict.
