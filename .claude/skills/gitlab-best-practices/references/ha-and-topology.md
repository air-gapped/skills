# High availability — what the chart actually provides

**Tag convention.** Untagged claims were verified against a primary source on
2026-08-29. **[A]** = reported but not independently re-verified. **[?]** =
claimed somewhere but contradicted or unsupported when checked.

## The one-paragraph answer

**There is no generally-available HA path for Git data on Kubernetes today.**
Standalone Gitaly on Kubernetes went GA in 18.11 and is *by design a single
point of failure*. The replicated option — Gitaly Cluster (Praefect) — is
**beta** on Kubernetes as of 19.1. Everything else in the chart (webservice,
sidekiq, KAS, shell, registry, pages) scales horizontally and ships a PDB, so
the stateless tier is genuinely HA-capable. Plan HA around **a restore plan for
Git data**, not around replication.

## Gitaly — the ladder and the gap

| Milestone | Status |
|---|---|
| 17.3 | experiment |
| 17.10 | beta |
| 18.2 | limited availability |
| **18.11** | **GA — standalone (non-Cluster) only** |
| 19.1 | Gitaly Cluster (Praefect) on Kubernetes introduced as **beta** |

Verbatim from `doc/administration/gitaly/kubernetes.md`:

> "To support a Cloud Native deployment, Gitaly (non-Cluster) is the only
> generally available option. Gitaly Cluster (Praefect) on Kubernetes is in
> beta."

> "By design, Gitaly (non-Cluster) is a single point of failure service (SPoF).
> Data is sourced and served from a single instance... when the StatefulSet pod
> rotates (upgrades, node maintenance, or eviction), the rotation causes service
> disruption."

**Do not read the 18.11 GA announcement as closing the HA gap.** It made the
SPoF supported, not redundant.

### Mitigating the SPoF — the documented set

Upstream's own guidance for living with it:

- Schedule maintenance windows for chart upgrades, Gitaly config changes and
  node maintenance.
- Set a `PriorityClass`.
- Block autoscaler eviction:
  `cluster-autoscaler.kubernetes.io/safe-to-evict: "false"`.
- Size pods for **Guaranteed** QoS.
- Anti-affinity for multi-pod (sharded) layouts.

The whole mitigation set is written for **RWO, one-PVC-per-pod** StatefulSet
semantics. Nothing in the docs suggests RWX is required or supported. A
single-replica Gitaly on RWO is the documented, expected shape.

### The Raft direction — intent, not a schedulable plan

Epic 8903 goals, unchanged since `gitaly#4436` (2022): *"1. Solve the variety of
inconsistency issues Gitaly Cluster has. 2. Remove Praefect. 3. Remove Postgres.
4. Through an upgrade, make every Gitaly a cluster of one."*

### Planning rule: Praefect-on-Kubernetes GA has no credible date

**Do not put it in a roadmap, a migration plan, or a commitment to anyone.**
Design the HA posture for what exists today.

Grounding, enough that this is not re-litigated every planning cycle:

| Signal | State |
|---|---|
| Epic 20405, make Gitaly Cluster first-class | open; public weekly status **"No progress"**, ~5 contributor h/week (Jul 2026) |
| Epic 8903, Raft — removes Praefect *and* its Postgres | no status update since **2024-06-18** |
| `gitaly#4616`, retire Praefect's Postgres ahead of Raft | **closed — "Final decision: NO-GO"** |
| Published GA target FY26Q4 (Dec 2025–Jan 2026) | landed **18.11, 2026-04-16**, standalone only |
| Requirement age on epic 6127 | live and unmet **2023 → 2026** |

`gitaly#4616` matters most: the incremental route off Praefect's PostgreSQL was
evaluated and explicitly declined (*"k8s will still not work due to Git I/O
needs"*), so the only path is the full Raft rewrite — which has no visible
investment. Treat "Praefect's Postgres goes away" as having no path and no date.

Open Praefect bugs named in epic 20405, worth checking against any Praefect
deployment: sticky-TCP imbalance requiring client-side DNS load balancing,
object pools breaking, forks/parents migrating out of order, Praefect-DB WAL
bloat, repository-move API failures on large repos, HEAD-reference
inconsistency.

### Do not cite pre-2024 GitLab architecture guidance

GitLab withdrew an earlier recommendation that blessed in-cluster stateful
components. Staff record it directly: *"architecture that GitLab had once
blessed and has since changed our recommendation"*. Any design resting on
GitLab guidance older than ~2024 must be re-checked against the current
reference architectures before it is trusted.

## The zero-downtime contradiction — the load-bearing one

Two GitLab-maintained documents make **opposite claims** about the same
deployment method. Nothing found reconciles them.

| Source | Claim |
|---|---|
| `doc/administration/reference_architectures/_index.md` | *"Zero-downtime upgrades are available for standard environments with HA (Cloud Native Hybrid is not supported)"* |
| `charts/gitlab` → `doc/installation/upgrade.md` | ships a full **"Upgrade with zero downtime"** section for the plain Helm chart, with concrete required settings |

The reference-architectures claim cites work item `gitlab-org/cloud-native#52`
as its justification. That item is **closed**, and it concerns the **GitLab
Operator** — a different deployment method from the plain chart. The citation is
stale and does not support the sentence resting on it.

**Act on the chart's own doc**, which is specific and maintained. Its stated
requirements:

- Multiple replicas configured for **webservice and sidekiq**.
- **One minor release at a time** — skipping one means *"database modifications
  might be run in the wrong sequence and leave the database schema in a broken
  state."*
- Explicit rollout settings, which are **not chart defaults**:
  `RollingUpdate`, `maxSurge: 10%`, `maxUnavailable: 0`, and tuned
  `terminationGracePeriodSeconds` for webservice, sidekiq, gitlab-shell and
  registry.
- *"Gitaly on Kubernetes supports zero-downtime upgrades through client
  retries."*

**The trap:** applying those rollout settings for the first time itself triggers
a disruptive rolling restart. Land them in **their own release**, ahead of the
upgrade they are meant to protect — not in the same change.

### Do not promise zero downtime on Kubernetes

Follow the chart procedure, but budget a brief disruption. It is not a
guarantee, and the gap is stated by GitLab's own delivery organisation in
`gitaly#6934` (open, 2025-09-29), under "Self-Managed Charts":

> "Current status: **No documented or publicly supported approach to ZDU in
> Cloud Hybrid.**"

Three mechanics from that issue constrain what is achievable:

| Mechanic | Consequence |
|---|---|
| `tableflip`, the in-place restart that delivered ZDU on Omnibus, is being **removed** — *"does not work to any extent with immutable infrastructure... This includes containerised deployments like Kubernetes"* | ZDU for Gitaly on Kubernetes rests on **client retries**, not process survival |
| No backward/forward gRPC compatibility guarantee between Rails and Gitaly | a single Helm release cannot order them safely; **open** |
| Pod restart latency vs in-place VM swap | **open** |

Verify against the actual workload, never against the word "zero".

## Per-component HA in the chart

Verified by grepping the chart source at master.

Defaults read from the unpacked chart at **10.3.1**.

| Component | PDB | Default | Notes |
|---|---|---|---|
| webservice | yes | `minReplicas: 2` | |
| kas | yes | `minReplicas: 2` | |
| gitlab-shell | yes | `minReplicas: 2` | |
| registry | yes | `minReplicas: 2` | values carries a commented `replicas: 6` example |
| **sidekiq** | yes | **`minReplicas: 1`** | the chart default is already the value that avoids the dedup race — scaling it up is what introduces the hazard |
| gitlab-pages | yes | — | |
| praefect | yes | `replicas: 2` | StatefulSet — beta on Kubernetes |
| gitaly | yes (`pdb.yaml`, `pdb-with-praefect.yaml`) | StatefulSet, sharded not replicated | a PDB on a single-replica StatefulSet prevents **voluntary** eviction; it does not create HA |
| **toolbox** | **none** | fixed `replicas: 1` | hidden singleton — anything scripted against it (backups, rake tasks) has no redundancy |
| **gitlab-exporter** | **none** | no replica key; effectively 1 | hidden singleton; a metrics outage, not user-facing, but scrapes break |

**Correct a common assumption:** the chart does *not* default to one replica
across the board. The stateless tier defaults to **2**, so a default install is
already partially redundant — while **Sidekiq defaults to 1**, which is
fortunate, because that is the value that avoids the silent migration-loss race.

**Autoscaling is opt-in.** `minReplicas` is a floor, not a scaling posture; the
KEDA-style autoscaling blocks ship commented out.

## Where GitLab says Kubernetes starts

Cloud Native Hybrid deploys *"select stateless components (Webservice, Sidekiq)
in Kubernetes using Helm Charts, while select components remain on virtual
machines or use cloud provider services (PostgreSQL, Redis, Object Storage)"* —
and the smallest published tier is **2,000 users / 40 RPS**.

**[A]** The frequently-quoted sentence *"Running stateful components in
Kubernetes, such as Postgres and Redis, is not supported"* is GitLab's standing
position, corroborated across pages but not re-grepped from raw source this
pass.

Below 2,000 users GitLab recommends the Linux package, not Kubernetes. Chart
10.0 then **removes bundled PostgreSQL, Redis and MinIO entirely** — so the
chart's own direction and the reference architectures now agree on one thing:
stateful dependencies belong outside the chart.

## Deployment shape — chart vs Operator

The plain chart is **not** deprecated and remains the mainstream choice. The
Operator *"relies on GitLab chart to provision Kubernetes resources. Therefore,
any limitation in GitLab chart impacts GitLab Operator"*, and is documented as
*"only suitable for specific scenarios in production use."* **[A]**

## Backup implications

Gitaly **Cluster** does not support snapshot backups (Praefect DB desyncs) — use
the Rake backup/restore tasks or incremental repository backups. A
single-replica non-Cluster Gitaly is not covered by that restriction →
`references/backup-restore.md`.
