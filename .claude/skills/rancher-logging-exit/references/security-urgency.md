# Security detail — CVE-2026-54680 and the precise exposure statement

For convincing stakeholders with facts, not FUD. All claims verified 2026-07-22.

## The vulnerability

**CVE-2026-54680 / GHSA-mjqf-28ph-426h** (published 2026-06-08, repo-scoped
advisory; NVD still RESERVED). CVSS **9.9 Critical**. Operator ≤6.5.2 writes
CRD- and Secret-provided string values into the rendered `fluent.conf`
**unescaped**; a value containing a newline terminates its directive and injects
arbitrary fluentd configuration — e.g. a `<match **>` block with `@type exec` —
arbitrary command execution in the aggregator pod. Hardening shipped in 6.6.0;
6.6.0's escaping broke legitimate newline-containing passwords (#2254), corrected
in 6.7.0 (#2255). **Deploy 6.7.0, not 6.6.0.**

## Why Rancher installs are affected with no fix

- Bundled operator = `rancher/mirrored-kube-logging-logging-operator:4.10.0` — a
  stock mirror of upstream 4.10.0, which predates the escaping fix and shares the
  vulnerable renderer. The 4.x line is EOL upstream; no backport exists.
- The `-rancher.N` fork (rancher/ob-team-charts) is **chart-level only** — a fix
  cannot ship as a chart respin; it requires a new operator line.
- No-fix status verified four ways (2026-07-22): suse.com/security/cve page 404s
  for the ID · NVD RESERVED · Rancher Security Advisories page lists nothing for
  logging/fluentd · zero logging commits in ob-team-charts since the advisory.
  This is verified "affected, unfixed" — not "not affected".

## Who can trigger it (Rancher RBAC, from the shipped chart)

- `templates/userroles.yaml` ships ClusterRole `logging-admin` (verbs `*` on
  `flows`/`outputs`) with `rbac.authorization.k8s.io/aggregate-to-admin: "true"`,
  unconditional ⇒ **any user bound to k8s `admin` in any namespace — i.e. any
  Rancher project-owner — can create Flow/Output CRs** and is a potential
  trigger. `logging-view` (get/list/watch) aggregates to admin/edit/view.
- The operator chart's aggregated **edit** role is gated behind
  `rbac.createAggregatedEditClusterRole` (default **false**) ⇒ project-members
  (edit) are read-only by default. If someone flipped it: members are triggers
  too.
- Secrets referenced by Outputs (`valueFrom.secretKeyRef`) are a second injection
  surface — anyone who can write those Secrets.

## Blast radius of aggregator RCE

The fluentd pod in cattle-logging-system holds: every Output credential
(ES/S3/Splunk/Loki secrets mounted or env-injected) · the fluentd SA — the chart's
`loggingServiceAccountAnnotations` value exists precisely to attach IRSA /
Workload Identity cloud roles to it · node/IMDS access in cloud (the advisory
itself cites AWS IMDS credential theft) · all cluster log traffic in transit.

Historical rhyme: **CVE-2019-12303** — Rancher ≤2.2.3, project owners injecting
fluentd config to read files/execute commands in the fluentd container. Same
class, same privilege tier, seven years apart.

## fluent-bit 3.1.8 — be precise, don't overstate

Bundled fluent-bit 3.1.8 is version-in-range for the Nov-2025 five-CVE set
(CVE-2025-12969/12970/12972/12977/12978; fixed 4.0.13/4.1.1/4.2.0+). BUT the
default rendered pipeline is `tail input → kubernetes filter → forward OUTPUT
(client)`; the vulnerable plugins (in_docker, out_file, in_http/in_splunk/
in_elasticsearch, in_forward server) are not enabled — and the forward *listener*
runs on the fluentd side. Correct framing: **outdated component that should be
updated**, exploitable only if someone enabled a vulnerable input/output. The
config-injection CVE above is the load-bearing urgency argument; this one is
supporting evidence of staleness.

## Interim mitigations (if the migration must wait)

- Audit who holds project-owner (⇒ Flow/Output authorship) per cluster; treat
  Flow/Output create rights as sensitive.
- Ensure `rbac.createAggregatedEditClusterRole` stays false.
- Alert on Flow/Output/ClusterFlow/ClusterOutput mutations
  (audit log: group `logging.banzaicloud.io`) and on fluentd pod exec/spawn
  anomalies (Falco/Tetragon: `@type exec` children of fluentd).
- Strip cloud IAM annotations from the logging SA if not strictly needed.
- These reduce, not remove, the exposure — 6.7.0 removes it.
