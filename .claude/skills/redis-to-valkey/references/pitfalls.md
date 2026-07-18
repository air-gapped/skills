# Pitfalls catalog

Scan before executing any migration plan. Ordered by severity. Version
gates verified 2026-07-18.

## Data-destroying

1. **Replica flushes before rejecting a foreign RDB** (valkey-io/valkey#2588):
   during full sync a Valkey replica runs its flush *before* discovering the
   incoming RDB (Redis 7.4+/v12) is unparseable — the replica ends up empty
   AND unsynced. Never point a Valkey that holds data at any source; never
   "test" replication from a >7.2 source.
2. **AOF masks RDB import on first boot**: with `appendonly yes` at first
   start, a copied-in dump.rdb is silently ignored (empty AOF wins). Boot
   with AOF off, verify data, then re-enable (AOF rewrites from the loaded
   set).
3. **Valkey 9 one-way door**: RDB v80 loads nowhere else (not Redis, not
   Valkey 8). Archive the final Redis RDB before decommissioning — it is
   the only rollback artifact. If a rollback window matters, land on
   Valkey 8.1.x first (still writes Redis-7.2-compatible v11).
4. **Persistence defaults**: some charts (groundhog2k) default to emptyDir
   unless a storage size is set — an HA deployment that "works" until the
   whole StatefulSet restarts. Set persistent storage explicitly for any
   non-cache class.

## Failover-breaking

5. **Dual-channel replication + Sentinel on Kubernetes**
   (valkey-io/valkey#2338): with `dual-channel-replication-enabled yes` and
   `replica-announce-ip`, the RDB channel connects from the pod's ephemeral
   IP; Sentinel records a phantom second replica and can elect a
   self-replicating "master". Fix (PR #2846, merged 2026-02-23) shipped in
   **Valkey 9.1.0 only** — not in 8.1.8 or 9.0.4. Upstream default is `no`;
   keep it off below 9.1.0. (Managed services may enable it by default.)
6. **`failoverWait` vs `downAfterMilliseconds` cross-unit trap**
   (groundhog2k): failoverWait is seconds, downAfter is milliseconds; the
   forced-failover logic misfires if failoverWait ≤ downAfter. Tuning
   downAfter up to Bitnami's 60000 requires failoverWait > 60.
7. **`redis-sentinel` symlink in early Valkey 8.x** didn't enter sentinel
   mode without an explicit `--sentinel` (valkey#719) — bites drop-in
   binary/systemd swaps, not chart deployments.
8. **RedisShake panics on topology change** — quiesce Sentinel failovers
   for the duration of a sync (temporarily raise down-after, or accept the
   full-recopy risk; there is no resume).

## Client-breaking

9. **Frozen `redis_version:7.2.4`** (permanent, by design; some builds emit
   two-part `7.2` which has crashed strict parsers — e.g. Sentry). Apps
   gating on ≥7.4 refuse Valkey even when the feature exists. Real version:
   `valkey_version` + `server_name:valkey`.
10. **HA service without 6379**: groundhog2k's main service exposes only
    26379 in HA mode — non-Sentinel-aware clients that pointed at the old
    Bitnami service's 6379 lose connectivity entirely (see app-cutover
    Class B).
11. **Master-set name mismatch**: `valkeyha` (groundhog2k default) vs
    `mymaster` (Bitnami/most clients' default) — Sentinel discovery returns
    nothing; either align the chart value or update every client.
12. **HEXPIRE gap**: hash-field TTL is Redis 7.4+ but **Valkey 9.0+** only
    — apps using it fail with unknown-command on Valkey 8.x. (Valkey's
    variant also emits `hexpired` keyspace events where Redis emits
    `hdel`/`del` in some edge cases — subscribers may diverge.)
13. **Valkey 8.0 vs Redis 7.2 behavior deltas** (from the fork's own 8.0
    line): nested MULTI/WATCH now aborts the transaction; SCAN stops
    returning lazily-expired keys; BITCOUNT/BITPOS raise errors on invalid
    args instead of returning 0; error strings drop the word "Redis"
    (string-matching on error text breaks); repl-backlog default 1→10MB.
14. **Valkey 9.x deltas**: auth errors now precede unknown-command errors
    for unauthenticated clients; `CLUSTER SHARDS`/`SLOTS` gained an
    availability-zone field that broke strict older parsers (go-redis fixed).
15. **Module gap**: no time series and no vector sets in the Valkey bundle
    (JSON, Bloom, search exist). Apps on Redis Stack modules need a
    per-module compatibility check before any migration promise.

## Operational

16. **io-threads default-on (Valkey 8+)**: markedly higher throughput but
    higher CPU per pod than single-threaded Redis — revisit CPU
    requests/limits sized for Redis (a 1-core limit that was generous for
    Redis can throttle Valkey under the same load).
17. **Exporter auth not auto-wired**: chart-side exporter sidecars need the
    password passed explicitly (env/secret); metrics silently absent
    otherwise.
18. **ServiceMonitor default inversion** (groundhog2k): enabling metrics
    enables the ServiceMonitor by default — install fails on clusters
    without prometheus-operator CRDs.
19. **Per-DB verification**: multiplexed deployments (several logical DBs)
    must be verified per index — DBSIZE on db0 alone reads as success while
    other indexes are empty.
