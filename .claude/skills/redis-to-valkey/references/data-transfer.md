# Data transfer: Redis → Valkey

Facts verified 2026-07-18. Version-gate everything here against the actual
source/target versions before running.

## Decision tree

```
Source Redis version?
├── ≤ 7.2.x ──► physical methods OK (REPLICAOF live, or RDB copy offline)
└── 7.4 / 8.x ──► logical replay only (RedisShake live, rdb-cli offline)
                  — REPLICAOF/DUMP/RESTORE/MIGRATE WILL FAIL (RDB v12)

Data class?
├── cache ────────► fresh start; skip transfer entirely
├── sessions ─────► fresh start acceptable (users re-auth once)
└── queues/state ─► transfer required, OR drain queues to empty first
                    (maintenance mode + wait for workers) then fresh start
```

Target Valkey major matters too: Valkey 9 writes RDB v80 — once data lands
on 9.x there is no path back to Redis or Valkey 8 (archive the last Redis
RDB as the rollback artifact). Choosing Valkey 8.1.x as an intermediate
target keeps snapshots at v11 (Redis-7.2-compatible) if a rollback window
matters more than 9.x features.

## Physical: REPLICAOF live cutover (source ≤ 7.2.x only)

On the (empty!) Valkey target:

```
valkey-cli REPLICAOF <redis-host> 6379
valkey-cli CONFIG SET masterauth <password>     # if source requires auth
valkey-cli INFO replication                     # wait: master_link_status:up
# compare master_repl_offset on both sides until converged
```

Cutover: quiesce writers → confirm offsets equal → `REPLICAOF NO ONE` →
repoint apps. Danger reminders:

- The replica **flushes itself before validating** the incoming RDB
  (valkey-io/valkey#2588) — never run this against a Valkey that already
  holds data, and never "just try it" from a 7.4+ source.
- TLS must match on both sides if the source uses it.
- If the source is Sentinel-managed, replicate from the *current master*
  and quiesce failovers (or Sentinel may repoint the source mid-sync).

## Physical: RDB file copy (source ≤ 7.2.x only)

```
redis-cli BGSAVE
redis-cli LASTSAVE          # poll until timestamp advances
# stop Redis (or stop writes), copy dump.rdb into the Valkey data dir
```

**Critical**: start Valkey with AOF **disabled** for the first boot
(`appendonly no`) — if AOF is enabled, the (empty) AOF takes precedence and
the RDB is silently ignored. Re-enable AOF after verifying data, which
rewrites it from the loaded dataset.

## Logical: RedisShake (any Redis version → any Valkey)

RedisShake decodes source data itself and re-issues plain commands, so RDB
version is irrelevant. v4.6+ supports Redis 2.8–8.4.x and Valkey 8.x–9.x,
standalone / master-replica / Sentinel / cluster on both ends.

Three readers (pick one in `shake.toml`):

| Reader | Mode | Use for |
|---|---|---|
| `sync_reader` | attaches like a replica (PSYNC), parses the RDB stream itself, then replays incremental commands continuously | near-zero-downtime: keep the target in sync while repointing apps one at a time |
| `rdb_reader` | reads a dump.rdb file | offline window, file in hand |
| `scan_reader` | SCAN + read + rewrite | when PSYNC is not permitted (managed services) |

Minimal live-sync config:

```toml
[sync_reader]
address = "<redis-master>:6379"      # current master, not the sentinel port
password = "<source-password>"

[redis_writer]
address = "<valkey-master>:6379"     # resolve via SENTINEL get-master-addr-by-name first
password = "<target-password>"
```

Operational caveats (from the maintainers):
- **No resume** — a restart means a full re-copy. Size the window accordingly.
- **Panics on topology change** (failover, resharding) on either end mid-run
  — quiesce Sentinel failovers for the duration (e.g. `SENTINEL SET <group>
  down-after-milliseconds 3600000` temporarily, restore after; or simply
  accept the re-run risk on small datasets).
- One-shot migration tool, not a permanent replication bridge.
- Verify after: `DBSIZE` both sides, sample keys incl. TTLs (`TTL`,
  `PTTL`), type spot-checks (`TYPE`, `HGETALL`, `LRANGE`).

### Air-gap delivery

- **Static binaries**: GitHub releases publish per-platform tarballs
  (`redis-shake-vX.Y.Z-linux-amd64.tar.gz`, also arm64) — a single Go
  binary + example configs. One file to carry across the gap; no runtime
  deps. (Verified present on v4.6.1, 2026-04-24.)
- **Container image**: `ghcr.io/tair-opensource/redisshake` — mirror it if
  you'd rather run the transfer as a Job/Pod inside the cluster (often the
  only place with network reach to both Redis and Valkey services).
- Typical in-cluster pattern: a one-off Pod/Job mounting `shake.toml` from
  a ConfigMap, running in the same namespace as source or target.

## Logical: rdb-cli (offline, any RDB version)

From redis/librdb (C library; build from source — releases are source-only,
no prebuilt binaries):

```
git clone https://github.com/redis/librdb && cd librdb && make
# air-gap: build on a connected machine of the same arch/libc, carry the
# rdb-cli binary (or vendor the source tarball and build inside)
```

Replay any dump.rdb (including Redis 7.4/8.x v12) into Valkey:

```
./bin/rdb-cli /path/dump.rdb redis -h <valkey-host> -p 6379
# add -a <password> as needed; supports filtering by key/db if required
```

Sequence: `BGSAVE` on source → stop writes → copy dump.rdb → replay →
verify → repoint. Simpler than RedisShake when a window exists and the
dataset fits comfortably in the window.

## Verification checklist (any method)

```
# counts
redis-cli -h <old> DBSIZE ; valkey-cli -h <new> DBSIZE     # per logical DB (-n N) if multiplexed
# sampled integrity
valkey-cli RANDOMKEY → TYPE/TTL/value spot-checks against source
# TTL preservation matters: logical tools must carry PTTL — spot-check keys known to expire
# app-level probe after repoint (login flow, queue drain, cache hit)
```

For multiplexed deployments (several logical DBs on one server): iterate
`-n <db>` for every index in use — a transfer that silently covered only
db0 looks complete on DBSIZE of db0 alone.
