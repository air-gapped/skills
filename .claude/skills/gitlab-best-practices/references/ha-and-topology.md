# High availability — what the chart actually gives you

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
single-replica Gitaly on RWO is the documented, expected shape — not a
misconfiguration to apologise for.

### The Raft direction — intent, not a plan you can schedule

Epic 8903 states the goals plainly: *"1. Solve the variety of inconsistency
issues Gitaly Cluster has. 2. Remove Praefect. 3. Remove Postgres. 4. Through an
upgrade, make every Gitaly a cluster of one."*

**[?]** The epic's last dated status update is **2024-06-18**, describing a
proof-of-concept just starting. There is no public evidence it has shipped, is
in beta, or is currently staffed. Treat Raft as stated intent with no date.
**Do not put it in a roadmap.**

### The roadmap signal, and what it is honest to conclude

Epic 20405 ("Make Gitaly Cluster a first-class solution") is open and describes
Praefect as *"our high availability solution for Git data"*, listing critical
open bugs: sticky-TCP imbalance needing client-side DNS load balancing, object
pools breaking under Praefect, forks/parents migrating out of order, Praefect-DB
WAL bloat, repository-move API failures on large repos, HEAD-reference
inconsistency.

Its public weekly status notes read **"total hours spent this week by all
contributors: 5 ... achievements: No progress"** (2026-07-23), and **"No
progress"** again (2026-07-30), with prior weeks in the 5–20 hour range. A
publicly visible customer note on the sibling epic (2026-07-28) records a
**paused evaluation**: Gitaly GA at 18.11 *"partially resolved the blocker...
However, the Praefect dependency on VMs remains a hard blocker for production
readiness."*

**What this supports:** the HA-on-Kubernetes work is stalled, upstream says so
in public, and planning around Praefect-on-Kubernetes reaching GA is planning
around an unstaffed epic.

**[?] What it does not support:** a claim that GitLab publicly reversed an HA
promise, or that staff publicly objected to their own company's HA direction.
Searched the trackers, forums and aggregators — **no such statement was found**.
Do not repeat that framing; the stall is documented, the reversal narrative is
not.

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

Note the tension with the migration-loss race: multi-replica Sidekiq is required
for zero-downtime *and* is the precondition for the deduplication race that
silently loses background migrations (`references/failure-modes.md` § Sidekiq).
On a small install, prefer a single Sidekiq replica and accept the restart.

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
