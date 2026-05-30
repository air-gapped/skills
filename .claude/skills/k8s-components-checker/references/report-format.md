# report-format.md — pre-upgrade report layout

When the operator asks for a **report** rather than an in-conversation verdict,
wrap the verdict in this layout. Recognizable section skeleton across runs so
a manager, JIRA reader, or change-management board can find the same things
in the same places between report N and report N+1. Section ordering and
headings are fixed; content is fully dynamic per cluster and per change set.

This file is a prose spec — no template engine, no scripts. Claude composes
each section per the current data.

## Section skeleton (fixed ordering, fixed headings)

```markdown
# Pre-upgrade report — <cluster identifier>

| Field | Value |
|---|---|
| Cluster | <name / kubeconfig context> |
| Upgrade scope | <change set — see Survey workflow § 1 for shapes> |
| Report date | <YYYY-MM-DD> |
| Skill registry freshened | <oldest Last verified: date from sources.md> |
| Report ID | <cluster>-<YYYY-MM-DD>-<seq> |

## Executive summary

<3–5 bullets a non-engineer can read in 30 seconds. Always include:
- Counts: N ready, M need bump, K blockers
- Critical dependency / blocker (the single sentence that determines go/no-go)
- Recommended call: proceed / proceed-with-prep / hold>

## Cluster survey

- **k8s server:** <version + RKE2 build, one line>
- **Nodes:** <count + OS + container runtime, one line>
- **Tracked components present:** <N of 19, one line>
- **Out-of-registry workloads detected:** <count + one-line note>
- **Deprecated-API liability:** <one-line conclusion from pluto + apiserver metric>

## Verdict

<the existing ✓ ready / ⚠ needs bump / ⚠ ordering / ✗ blockers /
✗ out of registry scope tree from SKILL.md § Verdict format, unchanged.
Source citations follow the references/compat/<comp>.md § <version> contract.>

## Diff vs prior report

<OMIT THIS WHOLE SECTION if no prior report is provided. If provided, three
buckets, each as a bullet list with the prior report's date as anchor:

**Improved since <prior date>**
- <one line per item that moved up the verdict severity: blocker → needs-bump,
  needs-bump → ready, out-of-scope → tracked>

**Regressed since <prior date>**
- <one line per item that moved down: ready → needs-bump, fresh → drift,
  etc. — usually new CVEs or newly-published deprecations>

**Unchanged blockers / pending items**
- <one line per item still in ⚠ or ✗ from the prior report — what's been
  carrying forward and how long>
>

## Action plan

<the existing ordered, numbered plan from SKILL.md § Verdict format,
respecting upgrade-ordering rules from the relevant compat files. Each step
short enough to land in a JIRA sub-task or a runbook PR commit.>

## Methodology

- Sourced from `k8s-components-checker` skill (registry of 19 components).
- Source citations follow `references/compat/<comp>.md § <version>` format.
- Survey commands: `kubectl version`, `kubectl get crd`, `helm list -A -o
  json`, `pluto detect-helm` + `detect-api-resources`, apiserver
  `apiserver_requested_deprecated_apis` metric.
- Community editions only; Prime / EE-gated content out of scope.
- Operator-driven floor overrides in effect: <list any non-default floors,
  e.g. "RKE2 1.31, Harvester 1.5.0, cert-manager 1.17, Argo CD 3.0">.
```

## Field discipline

- **Cluster** — name or kubeconfig context the survey ran against. Do NOT
  include kubeconfig path or any cluster-secret-shaped string.
- **Upgrade scope** — one of the five change-set shapes from SKILL.md §
  Survey workflow step 1. Use the same phrasing across reports so JIRA search
  finds them together.
- **Report ID** — `<cluster>-<YYYY-MM-DD>-<seq>` where `<seq>` is an integer
  starting at 1 per cluster per day. Predictable so reports can be archived
  and re-found.
- **Skill registry freshened** — read from `references/sources.md`'s oldest
  `Last verified:` date. If older than 90 days, surface that in the
  Executive summary as a caveat ("registry sources verified N days ago —
  recommend rerunning freshen before acting on this report").

## Worked example — anchor bump

Skeleton filled for the lab cluster's 1.32 → 1.34 verdict:

```markdown
# Pre-upgrade report — local

| Field | Value |
|---|---|
| Cluster | local |
| Upgrade scope | k8s 1.32 → 1.34 |
| Report date | 2026-05-28 |
| Skill registry freshened | 2026-05-28 |
| Report ID | local-2026-05-28-1 |

## Executive summary

- 7 components ready, 5 need bumps, 2 are current-state blockers
  (Argo CD CVE + cert-manager EOL).
- Critical dependency: Rancher 2.12 → 2.13 must complete BEFORE k8s 1.32
  upgrade begins (Rancher 2.12 does not cover k8s 1.34).
- Recommended call: **proceed-with-prep** — clear the two blockers and bump
  the 5 needs-bump components first; estimated 5 sequential change windows.

## Cluster survey

- k8s server: v1.32.12+rke2r1
- Nodes: 4 (Ubuntu 24.04, containerd 2.1.5-k3s1)
- Tracked components present: 14 of 19 (Kyverno, ECK, Mimir, Harvester, Tetragon not deployed)
- Out-of-registry workloads detected: 20+ (Rancher add-ons, RKE2 built-ins, inference stack)
- Deprecated-API liability: pluto scan at target k8s 1.34 returns zero hits;
  apiserver counter zero (per-process, recently restarted — cross-checked clean)

## Verdict

[... the existing verdict tree ...]

## Action plan

1. cert-manager 1.17 → 1.20 (step-wise)
2. Argo CD 3.0 → 3.2 (step-wise, strip IncludeMutationWebhook first)
3. KEDA 2.18 → 2.19
4. NVIDIA GPU Operator 25.10 → 26.3
5. Rancher 2.12 → 2.13 (backup OIDC AuthConfig first)
6. RKE2 1.32 → 1.33 (etcd / Traefik / snapshot-controller breaks)
7. RKE2 1.33 → 1.34
8. Re-run survey after each major step

## Methodology

[... per the spec above ...]
```

## Worked example — drift review

Skeleton filled for a drift-review change set (no target):

```markdown
# Pre-upgrade report — local

| Field | Value |
|---|---|
| Cluster | local |
| Upgrade scope | drift review |
| Report date | 2026-05-28 |
| Skill registry freshened | 2026-05-28 |
| Report ID | local-2026-05-28-2 |

## Executive summary

- 2 EOL'd components (cert-manager 1.17 EOL'd 2025-10-07; Argo CD v3.0 EOL'd
  2026-02-02). Argo CD also unpatched for CVE-2026-42880.
- 3 components at end-of-active-support but still receiving security patches
  (Traefik 3.6, KEDA 2.18, OpenEBS 4.3 stale-CI).
- Recommended call: **act on the two EOLs within this quarter**.

[... rest of skeleton, with verdict rows reflecting drift findings ...]
```

## Anti-patterns

- **Don't deviate from section ordering across runs.** Even if a section is
  empty, leave it in (e.g. "Diff vs prior report: no prior report on file —
  this is the baseline.").
- **Don't change section headings.** A manager scanning report N expects the
  same `## Executive summary` to appear at the same position in report N+1.
- **Don't bury blockers in the Verdict section without surfacing in Exec
  summary.** The exec summary is the only thing some readers will read.
- **Don't include kubeconfig paths, IP ranges, or other cluster-secret
  surface in the Cluster field.** Keep to a logical name.
- **Don't fabricate a Diff section** when no prior report exists. Say so in
  one line.
