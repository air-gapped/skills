# Pitfalls catalog

Scan before executing any migration plan. Ordered by severity. Version
gates verified 2026-08-26.

## Data-destroying

1. **Replica flushes before rejecting a foreign RDB — below 9.1.0**
   (valkey-io/valkey#2588): during full sync a Valkey replica runs its flush
   *before* discovering the incoming RDB (Redis 7.4+/v12) is unparseable —
   the replica ends up empty AND unsynced. **Fixed by PR #2600 (validate
   before `emptyData`), contained in 9.1.0+ only** — verified absent from
   tags 8.1.9 and 9.0.5 by compare. On 8.x/9.0.x the hazard is live; on
   9.1.0+ the replica keeps its data and the sync merely fails. Never point a
   Valkey that holds data at a >7.2 source on any version.
2. **AOF masks RDB import on first boot**: with `appendonly yes` at first
   start, a copied-in dump.rdb is silently ignored (empty AOF wins). Boot
   with AOF off, verify data, then re-enable (AOF rewrites from the loaded
   set).
3. **Valkey 9 one-way door**: RDB v80 loads nowhere else (not Redis, not
   Valkey 8). Archive the final Redis RDB before decommissioning — it is
   the only rollback artifact. If a rollback window matters, land on
   Valkey 8.1.x first (still writes Redis-7.2-compatible v11) — but weigh it
   against #1 and #5: both the foreign-RDB flush and the dual-channel
   Sentinel bug are fixed **only in 9.1.0+**, so 8.1.x buys rollback at the
   cost of carrying both live hazards.
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
   full-recopy risk; there is no resume). Resume is not coming: maintainers
   declined it as out of scope for a sync tool (issue #1016, still open at
   v4.6.2) — plan the window around a full recopy rather than waiting.

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
20. **`useHostnames: false` makes Sentinel remember dead pod IPs forever**
    (Bitnami chart). In that branch `get_full_hostname()` has **no `echo`** —
    the function's value is the `until` condition's pipeline,
    `getent hosts | awk '{print $1}'`, i.e. the **resolved IP**. Both
    `replica-announce-ip` and `sentinel announce-ip` capture it, so every
    StatefulSet roll leaves the old IP in the replica table as a permanent
    `s_down` phantom. Deliberate design for that mode, so there is no upstream
    bug to wait on.
    **The check that looks right and isn't:** `announce-hostnames yes` and
    `resolve-hostnames yes` are written into the config *regardless of the
    flag*, so byte-identical configs across installs prove nothing — and
    `resolve-hostnames` per Redis docs "will still refer to IP addresses when
    announcing an instance". Test the flag, not the directives:
    `helm get values <release> -n <ns> | grep useHostnames`.
    **Scope the impact honestly:** quorum is computed over the *sentinel*
    table, which stays clean, and Sentinel will not promote an `s_down`
    replica — do not claim a failover risk without new evidence. The real
    costs are external: whatever later inherits a recycled IP receives
    continuous connection attempts, and an unallocated IP can black-hole into
    an ICMP Time Exceeded storm (often invisible, since ICMP is inexpressible
    in a NetworkPolicy). Distinct from pitfall 5 — same phantom-replica
    symptom, different mechanism.
    **Repair** `SENTINEL RESET <mastergroup>` on each sentinel, one at a time
    verifying between so quorum never drops. That is a repair, not a fix: the
    next roll regenerates phantoms. **Fix** is `useHostnames: true` plus one
    reset to clear stored IPs — but check with the owner first, because
    upstream history runs both ways (#9689's workaround is to *disable* it;
    #25136 is cross-namespace pollution *with* it enabled).
21. **A single lost DNS packet puts Sentinel into TILT and fails exec
    probes.** With `resolve-hostnames yes`, sentinels re-resolve peer
    hostnames on every hello (~2 s), making them the one process class
    permanently exposed to UDP DNS loss. One lost packet costs a full glibc
    resolver timeout — **5 s by default** — spent inside a blocking
    `getaddrinfo()` (upstream-confirmed TILT cause, redis/redis#13866). That
    single stall is simultaneously over the 2 s TILT threshold *and* over any
    exec probe timeout ≤ 5 s, so it reads as a liveness failure and can
    restart otherwise-healthy pods.
    **Fix, independent of what drops the packet:** pod `dnsConfig.options`
    `timeout: 1` (or 2) and `attempts: 3`, making a lost packet cost 1 s —
    below both thresholds. Carry it per chart:
    - **Bitnami in sentinel mode → `replica.dnsConfig`.** The `-node`
      StatefulSet renders from the `replica` block, not a sentinel block.
    - **groundhog2k valkey has no `dnsConfig`/`dnsPolicy` value at all**
      (through 2.3.3; only `dnsFailureWait`). Use a Helm post-renderer. A live
      `kubectl patch` does survive ordinary upgrades via Helm's three-way
      merge, but is silently lost on `--force`, a reinstall or a fresh
      air-gapped install, and never appears in `helm get manifest`.
    Do **not** "fix" this by announcing IPs instead of hostnames — that is
    pitfall 20. Underlying packet loss is environment-specific (CNI conntrack
    or NAT-map GC evicting an in-flight UDP query is one documented cause);
    the `dnsConfig` change is worth making regardless, because it bounds the
    cost rather than chasing the source.
