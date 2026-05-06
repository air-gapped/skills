# Keycloak observability and operations

For Keycloak 26.6.x. Metrics, tracing, logging, health probes, and the troubleshooting recipes that come up most.

## TOC
1. [Metrics surface](#metrics)
2. [OTLP tracing](#tracing)
3. [Health probes](#health)
4. [Logging](#logging)
5. [Events and audit](#events)
6. [Performance tuning baseline](#perf)
7. [Troubleshooting recipes](#troubleshooting)

---

## <a id="metrics"></a>1. Metrics surface

Endpoint: `/metrics` on the management interface (default `:9000`). Requires `--metrics-enabled=true` (build-time).

Format: Prometheus text exposition. The metrics come from Quarkus Micrometer + Keycloak's own `MicrometerUserEventMetricsEventListenerProvider`.

Families to alert on:

| Metric family                                    | What it tells you                                                |
|--------------------------------------------------|------------------------------------------------------------------|
| `jvm_memory_used_bytes{area="heap"}`             | Heap pressure. Alert > 85% of limit for sustained periods.       |
| `jvm_gc_pause_seconds_sum`                       | GC overhead. Alert if pause budget > 5%.                         |
| `jvm_threads_states_threads`                     | Thread count by state.                                            |
| `http_server_requests_seconds`                   | HTTP latency histogram (with `method`/`uri`/`status` tags). Alert on p99 latency for `/realms/*/protocol/openid-connect/token`. |
| `http_server_active_requests`                    | In-flight request count. Alert if >= worker pool size for sustained periods (capacity exhaustion). |
| `agroal_pool_size{datasource="default"}`         | DB pool current size.                                             |
| `agroal_pool_available_count{datasource="default"}` | DB pool free connections. Alert if 0 for sustained periods.   |
| `agroal_acquire_count_total{datasource="default"}` | Cumulative acquires; rate gives QPS to the DB pool.            |
| `infinispan_cache_size{cache="..."}`             | Per-cache size. Caches that matter: `sessions`, `clientSessions`, `offlineSessions`, `authenticationSessions`, `actionTokens`, `loginFailures`, `work`, `realms`, `users`. |
| `infinispan_cache_hits_total` / `_misses_total`  | Hit ratio. Alert on hit ratio < 80% for `realms`/`users`.        |
| `infinispan_cache_evictions_total`               | Evictions — high rate indicates undersized caches.               |
| `keycloak_user_events_total{event,realm,error,client_id}` | Counts by event type. Watch `LOGIN_ERROR`, `REFRESH_TOKEN_ERROR`. |

Histogram tuning:
- `--http-metrics-histograms-enabled=true` for HTTP request latency p50/p90/p99/p999.
- `--http-metrics-slos=5,10,25,50,100,250,500,1000` to choose your SLO buckets.
- `--cache-metrics-histograms-enabled=true` for cache op latency.

Operator-side: setting `spec.serviceMonitor: {}` (the operator generates a Prometheus-Operator `ServiceMonitor` against the management port) is the path of least resistance.

---

## <a id="tracing"></a>2. OTLP tracing

Build-time enable: `--tracing-enabled=true`. Configure endpoint: `--tracing-endpoint=http://otel-collector.observability:4317`.

What gets traced:
- Quarkus HTTP server (each request)
- Hibernate ORM / JDBC (each query, each transaction)
- Infinispan operations
- Custom spans you can add via `@Traced` in extension code

Sampler: default `traceidratio` at 100%. Production: drop to 1–5% (`--tracing-sampler-ratio=0.05`) and switch to `parentbased_traceidratio` so client-initiated traces propagate cleanly.

Pair tracing with structured logs: enable `--log-mdc-enabled=true`, set `--log-console-output=json`, configure your collector to enrich log events with `trace_id` / `span_id`. This lets you click from a Tempo trace to its log lines and back.

Service name and resource attributes have moved to `--telemetry-service-name` / `--telemetry-resource-attributes` (the `--tracing-*-service-name` variants are deprecated, even though they still work). Set both for consistency across traces, metrics, and logs.

---

## <a id="health"></a>3. Health probes

Endpoints (on management port):

| Endpoint           | What it checks                                                                            | K8s usage          |
|--------------------|-------------------------------------------------------------------------------------------|--------------------|
| `/health/live`     | The Quarkus runtime is alive (event loop responsive).                                     | `livenessProbe`    |
| `/health/ready`    | DB up, caches initialised, **returns UP during DB migration as of 26.6** (was DOWN before).| `readinessProbe`   |
| `/health/started`  | Startup sequence complete.                                                                | `startupProbe`     |

If you've inherited probe configs with `failureThreshold: 60` to "ride out migrations," you can remove that — 26.6 handles it correctly.

If liveness flaps without obvious cause: heap pressure can stall the event loop. Check `jvm_gc_pause_seconds_sum`. Bumping memory often fixes it.

---

## <a id="logging"></a>4. Logging

Production defaults to set:

```
--log=console
--log-level=info
--log-console-output=json
--log-mdc-enabled=true
--http-access-log-enabled=true
--http-access-log-pattern=combined
--http-access-log-exclude=/health/.*|/metrics
```

Per-category log levels for debugging:
- `org.keycloak.events:debug` → all auth events to log
- `org.keycloak.protocol.oidc:debug` → OIDC handshake debugging
- `org.keycloak.broker:debug` → IdP brokering
- `org.keycloak.storage.ldap:debug` → LDAP federation
- `org.hibernate.SQL:debug` → DB queries (very noisy; use briefly)
- `org.infinispan:debug` → cache cluster issues

Sensitive-info redaction (26.6 default-on): `Authorization` headers and session cookies are masked. Don't disable this in production. Add to the redaction list with `--http-access-log-masked-headers=X-Custom-Sensitive`.

---

## <a id="events"></a>5. Events and audit

Two streams of events:
- **User events** (`LOGIN`, `LOGIN_ERROR`, `REGISTER`, `REFRESH_TOKEN`, `LOGOUT`, ...)
- **Admin events** (`CREATE`/`UPDATE`/`DELETE` on realm, client, user, role, ...)

Both are configured per-realm under **Realm Settings → Events**.

Default storage: realm DB tables (`EVENT_ENTITY`, `ADMIN_EVENT_ENTITY`). Configure retention with **Expiration**. Don't leave at "forever" in production — it bloats the DB.

For SIEM forwarding:
- Built-in `jboss-logging` listener emits events as log lines (use with structured JSON output).
- Custom `EventListenerProvider` for Kafka, webhook, Splunk HEC, etc. Few lines of Java; the source has examples.

Common pitfall: filtering events at the realm level limits what's *stored*; event listeners run on all events. If a custom listener floods downstream, narrow at the listener.

---

## <a id="perf"></a>6. Performance tuning baseline

JVM flags (set via `JAVA_OPTS_APPEND`):
```
-XX:+UseG1GC                  # default on JDK 17+, but explicit
-XX:MaxRAMPercentage=75       # heap as % of container limit
-XX:+ExitOnOutOfMemoryError   # let K8s restart on OOM
-XX:+UseStringDeduplication   # G1 string dedup; mild memory saving for high-realm workloads
```

Realistic numbers (3-replica baseline, 2 vCPU / 2 GiB each, Postgres on dedicated node):
- ~500–1000 token issuances / sec
- ~50–150 logins / sec (the slow path: password hashing dominates)
- p99 token endpoint latency ~50 ms

Don't autoscale based on these — see `k8s-deployment.md` §HPA. For sustained higher throughput, scale up first (4 vCPU / 4 GiB), then add replicas.

The official benchmark harness lives at `https://github.com/keycloak/keycloak-benchmark` — Gatling-based, Helm-deployable, supports realistic distributions of login / token-refresh / introspection. Run it before promising numbers to a stakeholder.

---

## <a id="troubleshooting"></a>7. Troubleshooting recipes

### Login redirect loop

**Symptom**: Browser bounces between `/auth` and `/realms/.../authenticate?code=...`. Or login appears to succeed, then immediately re-prompts.

**Diagnosis**: 95% of the time, hostname/proxy mismatch. Curl `https://<your-hostname>/realms/master/.well-known/openid-configuration` — if `issuer` doesn't match the hostname clients use, you have a mismatch.

**Fix**: Set `KC_HOSTNAME=https://<actual-public-url>`, `KC_HOSTNAME_STRICT=true`, `KC_PROXY_HEADERS=xforwarded` (or `forwarded`). Set `KC_PROXY_TRUSTED_ADDRESSES` to the proxy's CIDR. Restart pods.

### Liquibase migration stuck

**Symptom**: Pods never become Ready. Logs show "waiting for changeloglock". A previous pod crashed mid-migration.

**Diagnosis**: `SELECT * FROM DATABASECHANGELOGLOCK;` shows `LOCKED=true` with no live owner.

**Fix** (after confirming no other pod is migrating): `UPDATE DATABASECHANGELOGLOCK SET LOCKED=false, LOCKEDBY=NULL, LOCKGRANTED=NULL WHERE ID=1;`. Restart a pod. Migration resumes.

### Operator pod log floods (26.6.0 specifically)

**Symptom**: Operator emitting many warning lines, no functional impact.

**Fix**: Issue `#47872` in 26.6.0; **upgrade to 26.6.1**.

### "@keycloak/keycloak-admin-client fails to install" on 26.6.0

**Symptom**: `npm install @keycloak/keycloak-admin-client@26.6.0` fails or installs broken package.

**Fix**: Upstream packaging bug; **use 26.6.1**.

### Realm export silently missing users

**Symptom**: `kc.sh export` produces a realm JSON without users.

**Cause**: Default `--users` mode for export is `same_files` (users go into the same file as realm), but for large realms you may have used `skip` and forgotten.

**Fix**: `kc.sh export --dir /tmp/export --realm myrealm --users different_files` writes one file per chunk of users. Note: federated users (LDAP) are NOT exported regardless of mode. Realm exports are NOT a backup substitute — back up the DB.

### Slow token introspection

**Symptom**: `/realms/.../token/introspect` p99 latency creeping up under load.

**Diagnosis**: Cache miss on `clientSessions`/`offlineSessions`. Check `infinispan_cache_misses_total{cache="clientSessions"}` rate vs hits.

**Fixes** (in order):
1. Bump cache size: `--cache-config-file` with raised `max-count` for `clientSessions`.
2. Reduce token TTL — fewer long-lived tokens to look up.
3. Stateless tokens: switch clients to JWT validation against JWKS instead of introspection.

### LDAP federation user count doesn't match LDAP

**Symptom**: Keycloak user list shows fewer users than LDAP `ldapsearch`.

**Diagnosis**: Lazy-import default — Keycloak only imports a user on first login. The full set won't appear until Sync Settings → Periodic Full Sync runs.

**Fix**: Either trigger a full sync (admin console → User Federation → LDAP → Sync all users) or enable scheduled sync.

### Stuck "Account is disabled" after disable→enable

**Symptom**: Re-enabled user still sees "Account is disabled."

**Diagnosis**: Stale session in Infinispan cache.

**Fix**: User → Sessions tab → "Logout all sessions" for that user. If many users are affected, restart the realm cache via admin REST or rolling restart.

### TLS hot-reload not picking up new cert

**Symptom**: Cert-manager rotated the secret, browsers still see the old cert.

**Diagnosis**: `--https-certificates-reload-period=1h` (default) means up to a 1h delay. Check by listing the Pod's mounted secret timestamps.

**Fix**: For faster rotation, set `--https-certificates-reload-period=5m`. For instant rotation, do a rolling restart of the StatefulSet.

### "Could not connect to remote-cache" in HA topology

**Symptom**: Keycloak starts but logs warnings about remote Infinispan.

**Diagnosis**: External Infinispan unreachable, `--cache-remote-host` wrong, or TLS / auth misconfigured.

**Fix**: From a Keycloak pod, `nc -zv <infinispan-host> 11222`. Check `--cache-remote-username/password`. If TLS, the Infinispan server's cert needs to be in Keycloak's truststore — 26.6's automatic K8s truststore (`/var/run/secrets/.../service-ca.crt` on OpenShift) often handles this without extra config.

### Pod won't start: "schema validation error" on the Keycloak CR

**Symptom**: Operator rejects an apply with "unknown field `spec.update.strategy`".

**Diagnosis**: CRD is older than the operator deployment. The CRDs and operator must be from the same version tag.

**Fix**: Re-apply the matching `keycloaks.k8s.keycloak.org-v1.yml` from the version tag of the operator you're running.
