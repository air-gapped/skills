# High availability — what the chart actually provides

**Tag convention.** Untagged claims were verified against a primary source on
2026-08-29. **[A]** = reported but not independently re-verified. **[?]** =
claimed somewhere but contradicted or unsupported when checked.

## Table of contents
- [The one-paragraph answer](#the-one-paragraph-answer)
- [Gitaly — the ladder and the gap](#gitaly-the-ladder-and-the-gap)
- [Zero-downtime upgrades on the chart](#zero-downtime-upgrades-on-the-chart)
- [Per-component HA in the chart](#per-component-ha-in-the-chart)
- [Where GitLab says Kubernetes starts](#where-gitlab-says-kubernetes-starts)
- [Deployment shape — chart vs Operator](#deployment-shape-chart-vs-operator)
- [Backup implications](#backup-implications)

## The one-paragraph answer

**There is no generally-available HA path for Git data on Kubernetes today.**
Standalone Gitaly on Kubernetes went GA in 18.11 and is *by design a single
point of failure*. The replicated option — Gitaly Cluster (Praefect) — is
**beta** on Kubernetes as of 19.1, for non-production evaluation only, and its
GA is deprioritized. Everything else in the chart (webservice,
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

### Raft is dropped; the replacement is a proposal

Epic 8903 (Raft-based Gitaly Cluster — remove Praefect, remove its Postgres) is
**closed as "won't do"**. GitLab's stated direction is now a new Gitaly storage
backend — MVCC on object storage, epic 21711 — whose design document is *"a
proposal and not yet a committed design"*. Any plan that waits on Praefect's
Postgres disappearing, or on Raft, waits on nothing.

### Planning rule: Praefect-on-Kubernetes GA is not planned

**Do not put it in a roadmap, a migration plan, or a commitment to anyone.**
Design the HA posture for what exists today. Epic 6127's own status update:
Gitaly Cluster on Kubernetes is beta *"for non-production evaluation only.
GitLab has deprioritized the work to take it to general availability, in favor
of a new Gitaly storage backend."* Do not run it in production.

Grounding, enough that this is not re-litigated every planning cycle:

| Signal | State |
|---|---|
| Epic 6127, Gitaly on Kubernetes | Praefect-on-K8s GA **deprioritized**; Raft reference called stale |
| Epic 20405, make Gitaly Cluster first-class | open; public weekly status **"No progress"**, ~5 contributor h/week (Jul 2026) |
| Epic 8903, Raft — removes Praefect *and* its Postgres | **closed, "won't do"** |
| `gitaly#4616`, retire Praefect's Postgres ahead of Raft | **closed — "Final decision: NO-GO"** |
| Published GA target FY26Q4 (Dec 2025–Jan 2026) | landed **18.11, 2026-04-16**, standalone only |

Treat "Praefect's Postgres goes away" as having no path and no date: the
incremental route was declined in `gitaly#4616` (*"k8s will still not work due
to Git I/O needs"*) and the Raft rewrite is closed.

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

## Zero-downtime upgrades on the chart

**Supported for Cloud Native Hybrid from GitLab 18.9**, through the chart's own
`doc/installation/upgrade.md` § "Upgrade with zero downtime". The reference
architectures page agrees. Copies of that page saying *"Cloud Native Hybrid is
not supported"* are outdated — do not plan from them.

Its stated requirements:

- Multiple replicas configured for **webservice and sidekiq**.
- **One minor release at a time** — skipping one means *"database modifications
  might be run in the wrong sequence and leave the database schema in a broken
  state."* A hop between required stops (18.2 → 18.5) is therefore not a
  zero-downtime hop; budget downtime for it.
- Explicit rollout settings, which are **not chart defaults**:
  `RollingUpdate`, `maxSurge: 10%`, `maxUnavailable: 0`, and tuned
  `terminationGracePeriodSeconds` for webservice, sidekiq, gitlab-shell and
  registry.
- *"Gitaly on Kubernetes supports zero-downtime upgrades through client
  retries."*

**Run its sequence exactly:** pause the webservice and sidekiq Deployments →
`helm upgrade` with `SKIP_POST_DEPLOYMENT_MIGRATIONS=true` → wait for the
migrations Job → resume sidekiq, then webservice → a second `helm upgrade`
without the flag for post-deployment migrations. Do not skip the pause.

**The trap:** applying those rollout settings for the first time itself triggers
a disruptive rolling restart. Land them in **their own release**, ahead of the
upgrade they are meant to protect — not in the same change.

### Supported is not disruption-free

Budget a brief disruption anyway:

| Mechanic | Consequence |
|---|---|
| Standalone Gitaly is a SPoF; its pod rotation *"causes service disruption"* | Git operations ride on **client retries** across the Gitaly restart, not on process survival |
| Rails ↔ Gitaly have no cross-version gRPC guarantee; Gitaly must be upgraded first | confirm the Gitaly StatefulSet has rolled before resuming webservice and sidekiq. Independent rollout is still **open** upstream (`gitaly#6934`) |
| Reference architectures: *"there may still be brief moments of downtime when the HA mechanisms take effect"* | stated by GitLab for every zero-downtime method |

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

The reference architectures state it outright: *"Running stateful components in
Kubernetes, such as Postgres and Redis, is not supported"*.

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
