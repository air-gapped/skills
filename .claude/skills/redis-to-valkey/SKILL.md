---
name: redis-to-valkey
description: >-
  Migrate Redis deployments (especially Bitnami Redis Helm charts in Sentinel
  HA mode) to Valkey on Kubernetes, including fully air-gapped clusters.
  Core knowledge: the RDB-version wall (Valkey replicates/loads only from
  Redis ≤ 7.2.x; Redis 7.4+ writes RDB v12 which Valkey rejects; Valkey 9
  writes its own v80 — a one-way door), the two transfer layers
  (version-bound REPLICAOF/DUMP-RESTORE vs version-agnostic logical replay
  with RedisShake or rdb-cli), a side-by-side cutover runbook, Valkey chart
  selection (groundhog2k / CloudPirates / official valkey-io tradeoffs),
  Bitnami-redis→valkey values translation, consumer-app reconnection
  (Sentinel discovery, master-set names, frozen redis_version 7.2.4),
  Prometheus exporter continuity, air-gap tool/image mirroring, and Argo CD
  source rewiring away from charts.bitnami.com. First skill of the
  bitnami-exit suite.
when_to_use: >-
  Use whenever the task involves replacing Redis with Valkey or retiring
  Bitnami Redis: "migrate redis to valkey", "replace bitnami redis",
  "valkey sentinel chart", "bitnami exit", "bitnami alternative for redis",
  "REPLICAOF valkey", "redis-shake / RedisShake", "copy redis data to
  valkey", "can valkey read my dump.rdb". Also on symptoms: image pulls
  failing for docker.io/bitnami/redis tags, "Can't handle RDB format
  version 12", a Valkey replica coming up empty after pointing it at Redis,
  charts pinned to charts.bitnami.com / bitnamilegacy, apps that misreport
  the server version as 7.2.4 after a swap, or Sentinel failover
  misbehaving after enabling dual-channel replication. Covers connected AND
  air-gapped clusters, plain Helm and Argo CD. NOT for Redis-Cluster-mode
  topologies (sharded cluster protocol) or for tuning an existing healthy
  Valkey.
argument-hint: "[chart|data|cutover|apps|airgap] (optional focus area)"
---

# redis-to-valkey

Migrate Redis (Bitnami-chart Sentinel HA or any standalone/replicated Redis)
to Valkey on Kubernetes with data intact, clients reconnected, and no
dependency left on dead-ended Bitnami artifacts. Facts below were verified
2026-07-18 against primary sources (valkey source at release tags, chart
repos, vendor docs); re-verify anything version-gated before relying on it in
a later year.

## Why this migration exists

Broadcom locked down the free Bitnami catalog (effective 2025-09-29):
versioned images moved to `docker.io/bitnamilegacy` (frozen forever, no
updates), free `docker.io/bitnami/*` repos keep only `latest` tags, and most
charts froze at Aug 2025. `charts.bitnami.com` still serves (it redirects to
`repo.broadcom.com`) — so pinned charts *sync* fine and the failure arrives
later, at **image-pull time**: the first pod reschedule onto a node without
the image cached fails, because the pinned tag no longer exists outside
`bitnamilegacy`. Migrate deliberately, but don't assume the status quo is
stable. Valkey (Linux Foundation fork of Redis 7.2.4, BSD-licensed) is the
sanctioned successor for the Redis role — major consumers (Harbor, GitLab)
have adopted or officially support it.

## The one fact that shapes every plan: the RDB-version wall

Valkey forked at Redis 7.2. Its replication and snapshot formats stayed at
the fork point, then diverged on their own path:

| Server | Writes RDB | Can load |
|---|---|---|
| Redis 7.0 | v10 | ≤ v10 |
| Redis 7.2 | v11 | ≤ v11 |
| Redis 7.4 / 8.x | **v12** | ≤ v12 |
| Valkey 8.0 / 8.1 | v11 | ≤ v11 (v12+ rejected as foreign) |
| Valkey 9.0 / 9.1 | **v80** (own numbering) | v11 and v80; Redis v12+ rejected |

(Verified in `src/rdb.h` at release tags: `RDB_VERSION`, `RDB_FOREIGN_VERSION_MIN 12`.)

Consequences:

1. **`REPLICAOF`, RDB file copy, `DUMP`/`RESTORE`, and `MIGRATE` work only
   from Redis ≤ 7.2.x sources.** A full sync ships an RDB stream; a DUMP
   payload embeds RDB encodings. From Redis 7.4+ these fail with
   `Can't handle RDB format version 12`.
2. **Worse than failing: a Valkey replica FLUSHES its own dataset before it
   discovers the incoming RDB is unreadable** (valkey-io/valkey#2588). Never
   point a Valkey holding data at a source "to see if replication works".
3. **Valkey 9 is a one-way door.** Its v80 snapshots load on nothing else —
   not Redis, not Valkey 8. The final pre-cutover Redis RDB is your only
   rollback artifact; archive it before decommissioning.
4. The wall is about **persistence formats, not the wire protocol**. Any
   client speaking RESP to Redis 7.2 works against Valkey — which is exactly
   why logical replay (next section) is version-agnostic.

## Choosing a transfer method

Two layers exist; pick by source version and data class:

**Version-bound (physical) — only for Redis ≤ 7.2.x sources:**
- Live: on Valkey run `REPLICAOF <redis-host> 6379`, wait for
  `master_link_status:up` + offset convergence, repoint clients,
  `REPLICAOF NO ONE`.
- Offline: `BGSAVE` → poll `LASTSAVE` → stop Redis → place `dump.rdb` in
  Valkey's data dir → start Valkey **with AOF disabled for the first boot**
  (an enabled AOF silently wins over the RDB and you boot empty), re-enable
  after.

**Version-agnostic (logical replay) — any Redis version → any Valkey:**
Tools that decode the data themselves and re-issue plain commands; the
target only ever sees ordinary RESP traffic.
- **RedisShake** (tair-opensource, v4.6+): live PSync sync (keeps target in
  sync while you repoint apps one at a time), RDB-file reader, SCAN reader.
  Supports Redis 2.8–8.4.x → Valkey 8–9, standalone/Sentinel/cluster.
  Caveats: no resume (restart = full recopy); panics on topology change —
  quiesce failovers during the run.
- **rdb-cli** (redis/librdb): parses any-version `dump.rdb` offline and
  replays it as commands. Best for maintenance-window cutovers.

**No transfer (fresh start)** — legitimate for disposable data classes:

| Data class | Examples | Loss consequence | Verdict |
|---|---|---|---|
| Pure cache | page/object caches | cold-cache latency blip | fresh start |
| Sessions | encrypted web sessions | users re-authenticate once | fresh start (announce it) |
| Job queues / app state | Sidekiq, jobservice queues, schedules | enqueued work permanently lost | **must transfer** (or drain queues to empty in maintenance mode first) |

Read `references/data-transfer.md` for full recipes (RedisShake configs
incl. Sentinel endpoints, rdb-cli build, verification commands, air-gap
delivery of both tools).

## Cutover runbook (side-by-side, any method)

Never upgrade in place — resource naming, UIDs, and formats differ across
charts. Deploy Valkey next to Redis, move data, repoint, decommission:

1. **Deploy the Valkey release** side-by-side (new release name). Decide the
   Sentinel master-group name up front — keeping the old name (commonly
   `mymaster`) means zero client-side master-set changes.
2. **Pre-verify** the empty Valkey: sentinel quorum forms,
   `SENTINEL get-master-addr-by-name <group>` answers, auth works.
3. **Quiesce writers**: scale client Deployments to 0 or enable the app's
   maintenance mode. (For live RedisShake sync, start the sync *before*
   this step and quiesce only for the final repoint.)
4. **Move the data** per the method chosen above. Skip for fresh-start classes.
5. **Repoint the app**: sentinel endpoint list + master-set name + password
   secret (shape may change per chart — see values translation). For
   URL-style single-endpoint apps note that some Valkey charts' HA service
   exposes ONLY the sentinel port — the app must actually speak Sentinel.
6. **Scale up and verify**: `DBSIZE` comparison, sampled keys with TTLs
   intact, app functional probe, exporter metrics flowing.
7. **Archive the final Redis RDB** (rollback artifact — see one-way door),
   soak, then delete the Bitnami release, its PVCs, and its image pins.

## Chart selection and values translation

As of 2026-07-18: **groundhog2k/valkey** (Sentinel HA `haMode`, upstream
`valkey/valkey` images, tracks Valkey releases within days, bus-factor 1) and
**CloudPirates valkey** (Sentinel + an `externalReplica` migration mode,
multi-maintainer, cosign-signed, but one extra OCI library-chart to mirror)
are the production-ready Sentinel options. The **official valkey-io chart
has no Sentinel yet** (replication without automatic failover; Sentinel PR
pending — recheck before new deployments, a first-party chart likely wins
long-term). The Bitnami valkey chart is frozen with dead-ended images. The
official valkey-operator is cluster-mode-only and self-declared not
production-ready.

Bitnami-redis values do NOT translate 1:1. The traps that break clients or
lose data are: auth as config-file fragments instead of a bare
password secret, an HA service exposing only 26379, a different default
master-group name, persistence defaulting to emptyDir, ServiceMonitor
defaulting ON, and UID 999 vs Bitnami's 1001. Full mapping table, behavioral
diffs, and exporter wiring: `references/chart-migration.md`.

## Reconnecting consumer applications

Apps fall into config-surface classes — identify the class, then the
translation is mechanical: Sentinel-aware (endpoint list + master-set +
possibly a separate sentinel password), URL-based single endpoint (needs a
real 6379 service or must be switched to its Sentinel mode), DB-index
multiplexed (one server, many logical DBs — preserve index assignments), and
version-parsing (Valkey hardcodes `redis_version:7.2.4` forever — real
version is in `valkey_version`; two-part `7.2` builds have crashed naive
parsers). Classes, verification steps, and the dated per-product
compatibility log (Harbor, GitLab, oauth2-proxy, Open WebUI, Sidekiq,
Sentry): `references/app-cutover.md` and `references/known-consumers.md`.

## Air-gap and GitOps rewiring

The complete mirror list for a Sentinel HA migration is short: 2 images
(`docker.io/valkey/valkey`, exporter `oliver006/redis_exporter` — also on
ghcr.io and quay.io), 1 vendored chart tarball, and optionally the
RedisShake static binary (single-file Go binary from GitHub releases; also
`ghcr.io/tair-opensource/redisshake` as an image). For Argo CD: keep the
multi-source `$values` pattern and swap only the chart source; vendoring the
chart into git is the only bootstrap-safe option when the migrated Redis
backs your own registry (a registry cannot host the chart for its own
dependency's replacement). Details, OCI syntax (no `oci://` prefix in Argo
`repoURL`), Bitnami-endpoint risk model, and Renovate notes:
`references/airgap-gitops.md`.

## Pitfalls quick index

Before executing any plan, scan `references/pitfalls.md`. Highest-severity:
replica flush-before-reject (#2588); dual-channel replication + Sentinel
phantom replicas on Kubernetes (#2338 — fix shipped in Valkey 9.1.0 ONLY;
keep `dual-channel-replication-enabled no` below that); AOF masking RDB
import on first boot; HEXPIRE absent until Valkey 9; io-threads default-on
in Valkey 8+ raising per-pod CPU vs single-threaded Redis sizing.

## Reference files

| File | Read when |
|---|---|
| `references/data-transfer.md` | moving data: recipes for REPLICAOF / RDB copy / RedisShake / rdb-cli, verification, tool delivery offline |
| `references/chart-migration.md` | selecting a chart or translating Bitnami redis values |
| `references/app-cutover.md` | repointing applications; config-surface classes; verification checklist |
| `references/known-consumers.md` | dated per-product compatibility findings (log-style, append-only) |
| `references/airgap-gitops.md` | air-gapped mirroring, chart vendoring, Argo CD source rewiring |
| `references/pitfalls.md` | always, before executing a migration plan |
