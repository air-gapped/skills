---
name: gitlab-best-practices
description: >-
  Operate self-managed GitLab on the official Helm chart — multi-hop upgrade
  campaigns across required stops, the chart-10 wall (bundled PostgreSQL,
  Redis and MinIO removed and now mandatory), PostgreSQL 17 being both the
  minimum and the maximum for GitLab 19.x, default flips invisible to a values
  diff, air-gapped image sets the chart will not reveal, backup/restore with
  external dependencies and the secrets that are deliberately not in the
  backup, Sidekiq migration-loss and HPA-flap traps, and what high
  availability the chart actually provides (standalone Gitaly on Kubernetes is
  a documented single point of failure; Praefect on Kubernetes is beta).
when_to_use: >-
  Use for any self-managed GitLab task: "upgrade GitLab", "GitLab required
  stops", "upgrade_path.yml", "GitLab 19", "chart 10", "gitlab helm values",
  "GitLab air-gap image list", "gitlab-rails-secret", "backup-utility",
  "restore GitLab", "GitLab HA", "Gitaly Cluster", "Praefect", "GitLab Duo
  self-hosted", "GitLab zero-downtime upgrade". Symptoms: background
  migrations stuck or finalizing forever, `PG::UndefinedTable` mid-upgrade,
  `deduplicated: dropped` in Sidekiq logs, Sidekiq pods rescaling constantly
  or jobs SIGKILLed, Ingress objects vanishing after a chart bump, a default
  render failing with "external PostgreSQL became required", `helm upgrade`
  timing out on a migration. NOT for GitLab CI pipeline authoring, and NOT for
  Zalando postgres-operator mechanics (use postgres-operator-best-practices).
argument-hint: "[upgrade|ha|air-gap|backup|duo] (optional focus area)"
---

# gitlab-best-practices

Run and upgrade a **self-managed GitLab on the official Helm chart** without
unplanned downtime. The hard part is never `helm upgrade`. It is that the
chart changes defaults you never set, ships prerequisites written for a
configuration you do not run, and removed its own bundled databases in a
release that breaks your *tooling* before it breaks your deployment.

Facts here were verified **2026-08-29** against machine-readable upstream
sources, the chart at master, and a live RKE2 install carried from GitLab
18.7.0 to 19.3.1 across four hops. Re-verify anything version-bearing.

**Version anchor (2026-08-29):** latest chart **10.3.1** / app **19.3.1**.
Chart major = app major − 9. Required stops through 19.x: **18.2 · 18.5 ·
18.8 · 18.11 · 19.2 · 19.5 · 19.8 · 19.11** — enumerate them fresh, never
from memory.

## Symptom index

| Symptom | Where |
|---|---|
| Planning a multi-version upgrade; which stops, which order | § The ladder below, then `references/upgrade-campaign.md` |
| Ingress objects gone after a chart bump; instance off the network | `references/upgrade-campaign.md` § the chart-10 wall |
| Default render fails: "external PostgreSQL became required" | `references/upgrade-campaign.md` § chart 10.0 makes external deps mandatory |
| Background migrations stuck, finalizing forever, `PG::UndefinedTable` | `references/failure-modes.md` |
| `deduplicated: dropped` in Sidekiq logs; migrations never run, install looks green | `references/failure-modes.md` § Sidekiq |
| Sidekiq rescaling constantly; jobs SIGKILLed mid-flight | `references/failure-modes.md` § the HPA flaps by construction |
| PostgreSQL version, extensions, `amcheck`, scaling down for a DB cutover | `references/external-deps.md` |
| Redis / Sentinel / Valkey, object storage on non-AWS S3, registry `s3_v2` | `references/external-deps.md` |
| Building an air-gapped image list; what the render will not show | `references/air-gap.md` |
| Backup, restore, `gitlab-rails-secret`, rehearsing a restore | `references/backup-restore.md` |
| "Is this HA?", Gitaly Cluster, Praefect, zero-downtime upgrades | `references/ha-and-topology.md` |
| GitLab Duo, AI features, pointing it at a local model | `references/duo-ai.md` |

## The ladder

**Stops are minor-level, and the `.0` of a new major is not one.** Read them
from the machine-readable source, never from prose docs or memory:

```bash
curl -sS https://gitlab.com/gitlab-org/gitlab/-/raw/master/config/upgrade_path.yml
helm search repo gitlab/gitlab --versions | head -30   # chart <-> app, unfiltered
```

There is no `19.0` entry. The path is **18.11 → 19.2**, which crosses every
19.0 and 19.1 breaking change in a single hop with no intermediate resting
point. Satisfy 19.0's prerequisites *before leaving 18.11*.

A stop is a minor, satisfied by any patch of it — take the highest. Chart and
app patch numbers drift apart (chart 9.11.12 carries app 18.11.11); name both
in every artifact.

## The eight facts that cause unplanned downtime

**1. PostgreSQL 17 is both the minimum and the maximum for 19.x.** There is no
running ahead to PG 18. Because 18.x already tolerates PG 17, that overlap is
the only ordering with a supported resting point on both sides: **move the
database to 17 while still on 18.x, then upgrade GitLab.** Extensions are the
quiet half — `amcheck` became required at 18.4, migrations do not install
extensions, and the extensions docs page does not carry the table.
→ `references/external-deps.md`

**2. Chart 10.0 makes external PostgreSQL, Redis and object storage
mandatory — and breaks your tooling first.** The bundled databases are gone
and `NOTES.txt` carries hard `fail`s, so any "render the chart with defaults"
step dies, taking the all-features image sweep with it. Installs already on
external dependencies are insulated at the *deployment* layer and still lose
the *diffing* layer. → `references/upgrade-campaign.md`

**3. Default flips are invisible to a values diff.** A site inheriting a
default cannot see it change by looking at what it sets. Crossing chart
9.11.12 → 10.2.5 flipped five defaults, and a hand-built breaking-change table
written a week earlier from the release notes still missed one of them. **Diff
stock values every hop, including against your own notes.** Left unpinned,
`global.ingress.enabled: false` alone takes the instance off the network.

**4. A prerequisite in release notes is written for the DEFAULT
configuration.** Chart 10.3.0's "apply the Gateway API CRDs before upgrading or
it fails on the GitLab Shell TCPRoute" reads as mandatory for everyone. It
fires only if you render Gateway API objects. Render the target with your real
values, grep for the object kind the prerequisite names, and if it does not
render, record *why* it cannot apply. Complying anyway is not free — Gateway
API CRDs are cluster-scoped and permanent.

**5. Offline `helm template` corrupts exactly the artifacts your gates read.**
A cluster-less render cannot populate `.Capabilities.APIVersions`, so the chart
falls to its **oldest** apiVersion branch and silently drops blocks. `helm
upgrade` is unaffected because it talks to the cluster — so only the diffs are
wrong. Pass `-a/--api-versions` from `kubectl api-versions`; `--kube-version`
does not fix it.

**6. A single Sidekiq replica removes a silent migration-loss race.** With
multiple replicas, an old-version pod can take a background-migration job
before terminating, crash, and leave an orphaned dedup key in Redis — after
which **migrations never run while the install looks completely green**. Scale
Sidekiq to 0 for the upgrade, or run one replica. Note the tension: the chart's
zero-downtime procedure *requires* multiple replicas.
→ `references/failure-modes.md`

**7. There is no GA high-availability path for Git data on Kubernetes.**
Standalone Gitaly went GA at 18.11 and is *by design a single point of
failure*; Gitaly Cluster (Praefect) on Kubernetes is **beta**, and its
first-class-solution epic publicly reports "No progress" at ~5 contributor
hours a week. The stateless tier is genuinely HA-capable. Plan around a
**restore plan for Git data**, not replication.
→ `references/ha-and-topology.md`

**8. Rollback is a restore plan.** Reverting means reverting the database
schema, which needs a backup taken at the exact version and edition being
downgraded to, and the restore overwrites all newer content. **There is no
supported `helm rollback` after migrations have run against production data** —
the documented remedy for a bad state is to go *forward* to a required stop.
`helm rollback` recovers a bad values change, nothing more.

## AI, in three lines

- **Free tier gets no Duo at all**, and **CE can never hold a licence**, so no
  Duo path exists there ever. The chart defaults to `edition: ee` — which is
  what keeps an unlicensed install upgradeable later.
- **Duo against your own vLLM needs Premium/Ultimate plus the Duo Enterprise
  add-on.** Bringing your own GPU does not buy you out of the licence. The
  mandatory AI Gateway defaults to calling `customers.gitlab.com`, and when
  that is unreachable and unoverridden it costs **20 seconds per request** —
  presenting as "the AI is slow", not as an egress error.
- **The MCP server is free** (`Tier: Free, Premium, Ultimate`) and was
  decoupled from Duo in **19.2** — no add-on, no AI Gateway, no egress. On
  ≥19.2 that is the zero-licence answer; below it, the REST/GraphQL API.

→ `references/duo-ai.md`

## Working method

- **Run all six diff layers, every hop.** Stock values, stock render, site
  values, set-difference verify, site render, and site-render-vs-live-cluster.
  Each catches what the others structurally cannot — the stock-render layer is
  the only one that sees RBAC, probes and container args, because those never
  appear in `values.yaml`. → `references/upgrade-campaign.md`
- **Never `patch` a values delta onto a new version; use `diff3`.** `patch` has
  two inputs and cannot know what the file looked like when it was edited — it
  has already fuzz-matched a hunk onto an adjacent identically-shaped key and
  silently changed cluster-wide behaviour, exit 0. Merge mechanics: the `helm`
  skill, `references/values-porting.md`.
- **`helm lint` is not a typo check**, and **never `kubectl apply` a rendered
  template** — it rotates lookup-generated TLS/CA secrets.
- **Use `glab`, not a scraper, for gitlab.com.** The notes endpoint 401s to
  unauthenticated fetchers and comments are JS-rendered. A scraped pass once
  concluded a fix had no backport; `glab api .../related_merge_requests`
  returned three and proved the opposite. **A milestone says when a fix landed
  on master, not whether it reached your version** — only backport MRs and
  their `target_branch` answer that.
- **Get background migrations to zero at every stop, not just the last.**
  Active is fine; paused or failed is not.
- **A failed `helm upgrade` is usually a timeout on a long migration**, not a
  broken release. Check before reacting.
- **Verify in order of what each check proves**, cheapest first: `helm list` →
  Ingress objects exist with an external address → HTTP 200 on the web host →
  registry `/v2/` returns 401 → background migrations clean.
- Citations, per-claim, with issue states: `references/sources.md`.
