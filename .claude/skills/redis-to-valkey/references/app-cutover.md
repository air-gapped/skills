# Reconnecting consumer applications

Mechanisms only — dated per-product findings live in `known-consumers.md`.

## Config-surface classes

Every Redis-consuming app falls into one or more of these classes. Identify
the class first; the repoint then becomes mechanical.

### Class A — Sentinel-aware

The app takes a **list of sentinel endpoints + a master-set name** and
discovers the master itself. Typical shapes:

- Flag style: `--use-sentinel`, `--sentinel-master-name`,
  `--sentinel-connection-urls` (list)
- Values style: `redis.host` reinterpreted as the *master-set name* plus a
  `sentinels: [{host, port}]` list
- Env style: `REDIS_URL` host = master-set name + `SENTINEL_HOSTS`/`_PORT`

Repoint checklist: new sentinel service DNS names (port 26379), master-set
name (keep the old one via the chart's master-group value to avoid touching
clients at all), data-node password, and — separately — whether the
**sentinel processes themselves** require auth. Many clients carry a
distinct sentinel password knob (`sentinel_kwargs` in redis-py,
`--redis-sentinel-password` style flags); a missing one yields
`MasterNotFoundError`/auth errors *against the sentinels* while the data
password is correct. Simplest robust posture: leave sentinels
unauthenticated inside the cluster network (the common chart default) and
authenticate the data nodes.

### Class B — URL single-endpoint (not Sentinel-aware)

The app takes one `redis://host:port` URL and expects 6379 to answer. Two
options: (1) switch the app to its Sentinel mode if it has one; (2) give it
a stable 6379 — but note some Valkey charts' HA main service exposes ONLY
26379, so "point it at the service" silently stops working. A
non-Sentinel-aware app in front of a Sentinel deployment needs a
master-tracking proxy (HAProxy pattern) or should use a non-HA
(single-instance) Valkey instead — honest single-instance beats fake HA the
app can't follow across failovers.

### Class C — DB-index multiplexed

One server, several logical DBs (`SELECT n`) split across app components
(core=0, jobs=1, cache=2, …). Preserve the exact index assignments in the
new deployment's config, and remember data transfer must cover **every**
index in use (verify per-DB, not just db0). Some apps hard-require specific
indexes (e.g. a component that "must be 0").

### Class D — version-parsing

Apps that read `redis_version` from `INFO server`. Valkey hardcodes
`redis_version:7.2.4` permanently ("should never exceed 7.2.x" in
version.h); real identity is `server_name:valkey` + `valkey_version:X.Y.Z`.
Consequences:

- Minimum-version gates pass as long as the app requires ≤ 7.2 — an app
  demanding Redis ≥ 7.4 will refuse or misbehave even though Valkey 9
  has the features.
- Feature detection by version is wrong in both directions on Valkey
  (e.g. hash-field TTL exists in Valkey 9 despite "7.2.4").
- Some builds emit two-part `7.2`, which has crashed strict semver parsers
  outright. Test the actual image: `valkey-cli INFO server | grep -E
  'redis_version|valkey_version|server_name'`.
- Admin UIs showing "Redis 7.2.4" post-migration is cosmetic and expected.

## Cutover verification per app

1. Connection: app logs show master discovery (Class A) or clean connect.
2. Failover drill (HA only): delete the master pod; confirm the app
   reconnects to the new master within the sentinel window without restart.
3. Functionality probe appropriate to data class: session login persists,
   queue consumers drain, cache hit-rate recovers.
4. Version-gates: check app health/admin endpoints for version warnings
   (Class D cosmetics vs real refusals).
5. Metrics: exporter targets up, dashboards populated.

## Sequencing multiple apps off one shared Redis

With a live logical sync (RedisShake sync_reader) the target tracks the
source continuously — repoint apps one at a time, lowest-risk first
(sessions/cache before queues), keeping the sync running until the last
writer moves. Without live sync, each app needs its own write-freeze window,
or move them all in one window. Never leave two apps writing the same
logical data to both sides — split-brain data is worse than downtime.
