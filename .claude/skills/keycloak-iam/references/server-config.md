# Keycloak server configuration reference

For the Quarkus-based distribution (24.x → 26.6.x). Source-of-truth for option names: `quarkus/config-api/src/main/java/org/keycloak/config/*Options.java` in the upstream clone, and `https://www.keycloak.org/server/all-config`.

## TOC
1. [Configuration sources & precedence](#config-sources)
2. [The `kc.sh` CLI and the build step](#kc-sh)
3. [Hostname (the most common cause of broken logins)](#hostname)
4. [HTTP, TLS, reverse proxy](#http-tls-proxy)
5. [Database](#database)
6. [Cache / clustering / Infinispan](#cache)
7. [Feature flags](#features)
8. [Health, metrics, management interface](#health-metrics)
9. [Logging](#logging)
10. [Bootstrap admin (the `KEYCLOAK_ADMIN` replacement)](#bootstrap-admin)
11. [Tracing (OpenTelemetry)](#tracing)
12. [`kcadm.sh`: the admin REST CLI](#kcadm)

---

## <a id="config-sources"></a>1. Configuration sources & precedence

Keycloak reads configuration from the following sources, **highest precedence first**:

1. CLI args: `kc.sh start --hostname=https://auth.example.com`
2. Environment variables with `KC_` prefix: `KC_HOSTNAME=https://auth.example.com`
3. `KCRAW_` prefix env vars (**new in 26.6**) — same as `KC_` but bypasses SmallRye Config's `${...}` expression evaluation. Use this when a value legitimately contains `$` (e.g. a generated password). Without it, `pa$$word` becomes `paord` because `$$` is collapsed to `$` and `${pa…}` would be treated as an expression.
4. `conf/keycloak.conf` file (uses dot syntax: `hostname=https://...`, no prefix, dashes become dots)
5. Built-in defaults

The `KC_`/`KCRAW_` env name is derived from the option name: capitalise + replace `-` with `_`. So `--proxy-headers` → `KC_PROXY_HEADERS`.

`kc.sh show-config` prints the resolved config (after all source merging) and is invaluable for debugging "where did this value come from."

### Build-time vs runtime options

A subset of options are **build-time**: they bake into the Quarkus runtime jar and require an explicit (or auto-triggered) `kc.sh build` to take effect. Build-time options include:

- `--db <vendor>` (the JDBC driver and Hibernate dialect are picked at build)
- `--features=` and `--features-disabled=` (Quarkus extensions are wired in at build)
- `--health-enabled`, `--metrics-enabled` (the management endpoints are baked in)
- `--tracing-enabled` (OTel exporter is baked in)
- `--http-relative-path` (URL path baked into static resources)
- `--cache stack=embedded vs remote` (different Infinispan extensions)
- `--https-client-auth` (the TLS handshake is configured at build)

Everything else (hostname, proxy, db host/credentials, cache stack at runtime, log level, …) is **runtime** and can change at pod start.

### `kc.sh start` vs `kc.sh start --optimized`

- `kc.sh start` (no flag): if a build-time option has changed since the last build, Keycloak triggers an **auto-build** before starting. This is convenient for dev but adds tens of seconds (sometimes a minute+) to startup.
- `kc.sh start --optimized`: skips the auto-build step. Fails if build-time options would have changed.

Production pattern: bake `kc.sh build --db postgres --features=...` into your Dockerfile, and run with `--optimized` (or set `spec.startOptimized: true` in the Keycloak CR — but only if your image is pre-built, otherwise the operator falls back to the auto-build path).

---

## <a id="kc-sh"></a>2. The `kc.sh` CLI

Subcommands:

| Command            | Purpose                                                                          |
|--------------------|----------------------------------------------------------------------------------|
| `start`            | Start the server (auto-builds if needed)                                         |
| `start-dev`        | Dev mode — HTTP, no clustering, hostname relaxed, dev DB. **Never use in prod.** |
| `build`            | Run the build step explicitly (for `--optimized`)                                |
| `show-config`      | Print resolved configuration                                                     |
| `export`           | Export realm(s) to JSON                                                          |
| `import`           | Import realm(s) from JSON                                                        |
| `bootstrap-admin user` / `service` | Seed an admin (replaces the old `KEYCLOAK_ADMIN` env path)       |
| `tools completion` | Generate bash/zsh shell completion                                               |

`start-dev` does **not** trigger a build of production options — it always uses dev defaults (H2 in-memory, hostname loose). Don't use it as a smoke test for prod settings.

---

## <a id="hostname"></a>3. Hostname (the v2 provider)

This is the #1 source of "my login redirects forever" tickets. The legacy v1 hostname provider is **removed** as of 26.4. The current options live under `--hostname-*`:

| Option                         | Env var                           | What it does                                                                                                                                     |
|--------------------------------|-----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `--hostname`                   | `KC_HOSTNAME`                     | Public URL or hostname. Accept `auth.example.com` or `https://auth.example.com`. **Required** when `hostname-strict=true` (the default).         |
| `--hostname-strict`            | `KC_HOSTNAME_STRICT`              | Default `true`. If `true`, Keycloak refuses to derive its base URL from request headers — only `--hostname` (and the proxy headers) are trusted. Keep it on. |
| `--hostname-backchannel-dynamic` | `KC_HOSTNAME_BACKCHANNEL_DYNAMIC` | Default `false`. When `true`, internal services (calling `/protocol/openid-connect/token` etc. via cluster DNS) get URLs derived from their request rather than `--hostname`. Useful when the public URL isn't reachable from inside the cluster. Requires `--hostname` to be a full URL. |
| `--hostname-admin`             | `KC_HOSTNAME_ADMIN`               | Override for the admin console URL. Set this if you want admin on `admin.example.com` and login on `auth.example.com`.                            |
| `--hostname-debug`             | `KC_HOSTNAME_DEBUG`               | Default `false`. When `true`, `/realms/master/hostname-debug` shows resolved hostname state. Don't leave this on in production.                  |

### What "wrong hostname" looks like

- The login page works, but after submitting credentials the browser bounces between `/auth` and `/realms/.../authenticate?code=...` forever → almost always a hostname/proxy mismatch. Check that `https://<hostname>/realms/master/.well-known/openid-configuration`'s `issuer` field matches what the client expects.
- Mobile / native clients work, browser flows fail → CORS / Web Origins, not hostname.
- Keycloak signs tokens with `iss=https://internal-svc:8443` → you didn't set `--hostname`, so it derived the issuer from the request. Set `--hostname=https://auth.example.com` and `--hostname-strict=true`.

---

## <a id="http-tls-proxy"></a>4. HTTP, TLS, reverse proxy

### HTTP / HTTPS listeners

| Option                         | Env var                          | Default     | Notes                                                       |
|--------------------------------|----------------------------------|-------------|-------------------------------------------------------------|
| `--http-enabled`               | `KC_HTTP_ENABLED`                | `false`     | Set `true` only if you terminate TLS at the proxy.         |
| `--http-port`                  | `KC_HTTP_PORT`                   | `8080`      |                                                             |
| `--https-port`                 | `KC_HTTPS_PORT`                  | `8443`      |                                                             |
| `--https-certificate-file`     | `KC_HTTPS_CERTIFICATE_FILE`      | —           | PEM cert. Pair with `--https-certificate-key-file`.         |
| `--https-key-store-file`       | `KC_HTTPS_KEY_STORE_FILE`        | —           | PKCS12 / JKS keystore alternative.                          |
| `--https-key-store-password`   | `KC_HTTPS_KEY_STORE_PASSWORD`    | `password`  | The default is a literal placeholder — set it.              |
| `--https-protocols`            | `KC_HTTPS_PROTOCOLS`             | `TLSv1.3,TLSv1.2` | Tighten to `TLSv1.3` for new deployments.            |
| `--https-client-auth`          | `KC_HTTPS_CLIENT_AUTH`           | `none`      | `request` or `required` for mTLS. **Build-time.**           |
| `--https-certificates-reload-period` | `KC_HTTPS_CERTIFICATES_RELOAD_PERIOD` | `1h`  | `-1` to disable. Lets cert-manager rotate without restart.  |

### Proxy (`--proxy edge|reencrypt|passthrough` is **gone** — use `--proxy-headers`)

| Option                          | Env var                          | Notes                                                                                  |
|---------------------------------|----------------------------------|----------------------------------------------------------------------------------------|
| `--proxy-headers`               | `KC_PROXY_HEADERS`               | `xforwarded` (X-Forwarded-*) or `forwarded` (RFC 7239). Set this whenever a proxy fronts Keycloak. |
| `--proxy-protocol-enabled`      | `KC_PROXY_PROTOCOL_ENABLED`      | `false` by default. For HAProxy PROXY-protocol. Mutually exclusive with `proxy-headers`. |
| `--proxy-trusted-addresses`     | `KC_PROXY_TRUSTED_ADDRESSES`     | CIDR list. Headers from outside the list are **not** trusted. Set this in production. |

### Graceful HTTP shutdown (new in 26.6)

| Option                | Env var               | Default | Notes                                                  |
|-----------------------|-----------------------|---------|--------------------------------------------------------|
| `--http-server-shutdown-delay`   | `KC_HTTP_SERVER_SHUTDOWN_DELAY`   | `1s`    | Wait this long after SIGTERM before closing the listener — gives the LB time to deregister. |
| `--http-server-shutdown-timeout` | `KC_HTTP_SERVER_SHUTDOWN_TIMEOUT` | `1s`    | Drain timeout for in-flight requests after listener closes. |

For setups where the proxy and the pod get the SIGTERM at the same time, the defaults are fine. If the LB takes longer than 1s to deregister (e.g. AWS NLB target deregistration), bump `shutdown-delay` to 30s.

### Automatic Kubernetes truststore (new in 26.6)

When the file `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt` (and on OpenShift, `/var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt`) exists, Keycloak now automatically adds it to the system truststore at boot. Disable with `--truststore-kubernetes-enabled=false`. Removes the need for the operator to copy these into a custom truststore.

---

## <a id="database"></a>5. Database

Supported vendors: `postgres`, `mariadb`, `mysql`, `oracle`, `mssql`, plus dev-only `h2-file`, `h2-mem`, `dev-mem`, `dev-file`.

| Option                          | Env var                            | Notes                                                              |
|---------------------------------|------------------------------------|--------------------------------------------------------------------|
| `--db`                          | `KC_DB`                            | **Build-time.** `postgres` is the only one battle-tested at scale. |
| `--db-url`                      | `KC_DB_URL`                        | Full JDBC URL. Overrides `db-url-host`/`port`/`database`.          |
| `--db-url-host`                 | `KC_DB_URL_HOST`                   |                                                                    |
| `--db-url-port`                 | `KC_DB_URL_PORT`                   |                                                                    |
| `--db-url-database`             | `KC_DB_URL_DATABASE`               |                                                                    |
| `--db-url-properties`           | `KC_DB_URL_PROPERTIES`             | Vendor-specific; e.g. `?ssl=true&sslmode=verify-full`.             |
| `--db-username` / `--db-password` | `KC_DB_USERNAME` / `KC_DB_PASSWORD` | Use Kubernetes Secret + envFrom in the operator/manifests.        |
| `--db-pool-initial-size`        | `KC_DB_POOL_INITIAL_SIZE`          | Default `1`.                                                       |
| `--db-pool-min-size`            | `KC_DB_POOL_MIN_SIZE`              |                                                                    |
| `--db-pool-max-size`            | `KC_DB_POOL_MAX_SIZE`              | Default `100`. **Per pod.** With 3 replicas that's 300 connections — make sure Postgres `max_connections` accommodates this. |
| `--transaction-xa-enabled`      | `KC_TRANSACTION_XA_ENABLED`        | Default `false` (since 26.0). Enable for distributed transactions across DB and JMS — rare. |

### Database TLS (simplified in 26.6)

The old `--db-url-properties` route still works, but 26.6+ adds first-class options:

- `--db-tls-mode` / `KC_DB_TLS_MODE` — `disabled` / `verify-server` / `verify-full`
- `--db-tls-trust-store-file` and `--db-tls-trust-store-password` — for `verify-server` / `verify-full`
- `--db-mtls-key-store-file` / `--db-mtls-key-store-password` — for client-cert (mTLS) DB authentication

### Migrations and probes (changed in 26.6)

Liquibase runs on startup. As of 26.6, `/health/live`, `/health/ready`, `/health/started` return UP **during** migration so K8s does not kill the pod mid-Liquibase. Previously you had to bump probe `failureThreshold` for upgrades.

**If a migration crashes:** the `DATABASECHANGELOGLOCK` row gets stuck. After confirming nothing else is migrating, `DELETE FROM DATABASECHANGELOGLOCK WHERE ID=1`. Do NOT `--force-clear` lock without checking — concurrent migrations against an unsuspecting locked row corrupt the schema.

### Database data-at-rest encryption (preview in 26.6.0, expanded 26.6.1)

A subset of stored values (refresh tokens, client secrets in the DB, …) can be encrypted at the application layer via the new `--db-data-encryption-*` SPI. Independent of Postgres TDE. Read the migration guide in the official docs before enabling — it's not retroactive and re-keying requires a planned migration.

---

## <a id="cache"></a>6. Cache / clustering / Infinispan

Keycloak uses Infinispan for: realm/client metadata caches, login session caches, user session caches, action token caches, distributed lock service, work cache.

| Option              | Env var                | Notes                                                                                  |
|---------------------|------------------------|----------------------------------------------------------------------------------------|
| `--cache`           | `KC_CACHE`             | `ispn` (default in production) or `local` (single-node, no clustering).                |
| `--cache-stack`     | `KC_CACHE_STACK`       | JGroups discovery: `kubernetes`, `tcp`, `udp`, `jdbc-ping`, `jdbc-ping-udp`, `ec2`, `azure`, `google`. **`kubernetes`** is correct on K8s; `jdbc-ping` is the universal-cloud fallback (no extra k8s perms). |
| `--cache-config-file` | `KC_CACHE_CONFIG_FILE` | Path to `cache-ispn.xml` to override the default. Use to tune cache sizes, TTLs.       |
| `--cache-embedded-mtls-enabled` | `KC_CACHE_EMBEDDED_MTLS_ENABLED` | Default `true` (since 26.x). Keycloak self-issues an ephemeral mTLS keystore for JGroups encryption. |

### `kubernetes` stack requirements

The `kubernetes` stack uses `KUBE_PING` which queries the K8s API to discover peers. It needs:
- Pods to use a headless `Service` (the operator creates one automatically)
- The pod's ServiceAccount to have `pods` `list+get` RBAC in the namespace (operator-created RBAC handles this)
- `KUBERNETES_NAMESPACE` env var set to the pod's namespace (the operator injects this; for raw manifests use the downward API)

If `kubernetes` doesn't work (stricter PSP, sidecars), fall back to `jdbc-ping` — the cluster discovers peers via a Postgres table, no K8s perms needed.

### External Infinispan ("remote-cache", for HA)

For multi-cluster active-active or active-passive setups, Keycloak no longer relies on JGroups cross-site replication (deprecated). Instead, deploy an external Infinispan cluster and point Keycloak at it:

```
--cache=ispn
--cache-config-file=cache-ispn-remote.xml   # ships in the distribution
--cache-remote-host=infinispan.iam.svc
--cache-remote-port=11222
--cache-remote-username=keycloak
--cache-remote-password=$(KC_CACHE_REMOTE_PASSWORD)
--cache-remote-tls-enabled=true
```

See `https://www.keycloak.org/high-availability/` for the full topology, including the recommended pattern: Keycloak in DC1 + Keycloak in DC2 each pointing at their own local Infinispan, with Infinispan doing site-to-site replication between DCs. This pattern survives a DC failure with bounded session loss.

---

## <a id="features"></a>7. Feature flags

`--features=<csv>` and `--features-disabled=<csv>` toggle Quarkus extensions. **Build-time.**

Feature names use a colon for versions: `client-policies:v2`, `admin-fine-grained-authz:v2`, `hostname:v2`. As features mature they're promoted from `experimental` → `preview` → supported (at which point they're enabled by default and the feature flag is removed).

Notable features in 26.6 worth knowing:

| Feature                          | Status (26.6.x)        | What it does                                                           |
|----------------------------------|------------------------|------------------------------------------------------------------------|
| `organizations`                  | supported (default on) | Multi-tenancy within a realm                                           |
| `admin-fine-grained-authz:v2`    | supported (off)        | FGAP v2 — granular admin permissions. Enable explicitly.              |
| `recovery-codes`                 | supported (default on) | Backup OTP codes                                                       |
| `dpop`                           | supported              | DPoP-bound tokens (RFC 9449)                                           |
| `client-policies:v2`             | supported              | Client policy executors v2                                             |
| `transient-users`                | preview                | Anonymous → upgrade-to-real-user flow                                  |
| `declarative-user-profile`       | supported (default on) | JSON-driven user profile schema                                        |
| `cimd`                           | experimental           | OAuth Client ID Metadata Document (for MCP authorization servers)      |
| `step-up-authentication-saml`    | preview                | Step-up auth for SAML clients (OIDC was already there)                 |
| `workflows`                      | supported              | Realm workflow engine                                                  |
| `token-exchange`                 | supported              | RFC 8693 standard token exchange                                       |

`kc.sh show-config` lists active features. The full list lives in `quarkus/config-api/src/main/java/org/keycloak/common/Profile.java`.

---

## <a id="health-metrics"></a>8. Health, metrics, management interface

Health and metrics live on a **separate management port** (default 9000) — *not* the main HTTP/HTTPS port. This isolates ops endpoints from public traffic.

| Option                         | Env var                          | Default | Notes                                  |
|--------------------------------|----------------------------------|---------|----------------------------------------|
| `--health-enabled`             | `KC_HEALTH_ENABLED`              | `false` | **Build-time.** Enables `/health/*`.    |
| `--metrics-enabled`            | `KC_METRICS_ENABLED`             | `false` | **Build-time.** Enables `/metrics`.    |
| `--http-management-enabled`    | `KC_HTTP_MANAGEMENT_ENABLED`     | auto    | Auto-enabled when health or metrics is on. Disable to expose health/metrics on the main port instead (not recommended). |
| `--http-management-port`       | `KC_HTTP_MANAGEMENT_PORT`        | `9000`  |                                        |
| `--http-management-relative-path` | `KC_HTTP_MANAGEMENT_RELATIVE_PATH` | inherits from `--http-relative-path` | |
| `--http-management-scheme`     | `KC_HTTP_MANAGEMENT_SCHEME`      | inherits | `http` or `https`. The management port can run plain HTTP even if the main port is HTTPS. |

Endpoints (under the management interface):

- `/health/live` — process is alive
- `/health/ready` — ready to serve traffic (DB up, caches initialised). **Returns UP during DB migrations** as of 26.6.
- `/health/started` — startup probe. Useful for slow boots.
- `/metrics` — Micrometer / Prometheus exposition.

Probes in K8s should always target the management port (`port: 9000`, scheme: HTTP unless you've forced management HTTPS).

---

## <a id="logging"></a>9. Logging

| Option                         | Env var                          | Default     | Notes                                                              |
|--------------------------------|----------------------------------|-------------|--------------------------------------------------------------------|
| `--log`                        | `KC_LOG`                         | `console`   | CSV: `console,file,syslog,gelf`.                                   |
| `--log-level`                  | `KC_LOG_LEVEL`                   | `info`      | Per-category: `info,org.keycloak.events:debug`.                    |
| `--log-console-output`         | `KC_LOG_CONSOLE_OUTPUT`          | `default`   | `default` (text) or `json`. Use `json` in production.              |
| `--log-console-format`         | `KC_LOG_CONSOLE_FORMAT`          | …           | Pattern; ignored when `output=json`.                                |
| `--log-mdc-enabled`            | `KC_LOG_MDC_ENABLED`             | `false`     | Includes realm, clientId, etc. in JSON logs.                       |

### HTTP access log (with sensitive-info redaction in 26.6)

| Option                          | Env var                          | Default     | Notes                                                              |
|---------------------------------|----------------------------------|-------------|--------------------------------------------------------------------|
| `--http-access-log-enabled`     | `KC_HTTP_ACCESS_LOG_ENABLED`     | `false`     |                                                                    |
| `--http-access-log-pattern`     | `KC_HTTP_ACCESS_LOG_PATTERN`     | `common`    | `common`, `combined`, or `long`.                                   |
| `--http-access-log-exclude`     | `KC_HTTP_ACCESS_LOG_EXCLUDE`     | —           | Regex of paths to skip (e.g. `/realms/master/.*` for noisy realms). |

In 26.6, sensitive headers (`Authorization`) and session cookies are masked by default. Override the lists with `--http-access-log-masked-headers` and `--http-access-log-masked-cookies` if needed.

---

## <a id="bootstrap-admin"></a>10. Bootstrap admin

`KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD` were **removed in 26.0**. The replacement:

| Env var                              | Notes                                                                                            |
|--------------------------------------|--------------------------------------------------------------------------------------------------|
| `KC_BOOTSTRAP_ADMIN_USERNAME`        | Default `temp-admin`. A temporary admin in the master realm.                                     |
| `KC_BOOTSTRAP_ADMIN_PASSWORD`        | Required if `KC_BOOTSTRAP_ADMIN_USERNAME` is set. **Don't pass this on the CLI.**                |
| `KC_BOOTSTRAP_ADMIN_CLIENT_ID`       | Service account variant — default `temp-admin`.                                                  |
| `KC_BOOTSTRAP_ADMIN_CLIENT_SECRET`   | Service account secret. If set, allows machine bootstrap without a human user.                    |

The bootstrap admin **expires after 120 minutes**. The intended workflow:

```bash
# 1. Pod boots with KC_BOOTSTRAP_ADMIN_USERNAME / PASSWORD set
# 2. Use kcadm.sh to create your real admin
kcadm.sh config credentials --server http://localhost:8080 --realm master \
    --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
kcadm.sh create users -r master -s username=alice -s enabled=true \
    -s firstName=Alice -s lastName=Admin -s email=alice@example.com
kcadm.sh set-password -r master --username alice --new-password '<...>'
kcadm.sh add-roles -r master --uusername alice --rolename admin
# 3. Remove KC_BOOTSTRAP_ADMIN_* from the pod env (or just let it expire).
```

`kc.sh bootstrap-admin user --username alice --password ...` works similarly when the server is offline (writes directly to the DB).

The Keycloak Operator's `spec.bootstrapAdmin.user.secret` covers this end-to-end; don't roll it manually if you're using the operator.

---

## <a id="tracing"></a>11. Tracing (OpenTelemetry)

| Option                          | Env var                          | Default                  | Notes                                              |
|---------------------------------|----------------------------------|--------------------------|----------------------------------------------------|
| `--tracing-enabled`             | `KC_TRACING_ENABLED`             | `false`                  | **Build-time.**                                    |
| `--tracing-endpoint`            | `KC_TRACING_ENDPOINT`            | `http://localhost:4317`  | OTLP gRPC.                                         |
| `--tracing-protocol`            | `KC_TRACING_PROTOCOL`            | `grpc`                   | `grpc` or `http/protobuf`.                         |
| `--tracing-sampler-type`        | `KC_TRACING_SAMPLER_TYPE`        | `traceidratio`           | **Build-time.**                                    |
| `--tracing-sampler-ratio`       | `KC_TRACING_SAMPLER_RATIO`       | `1.0`                    | Sample 100% in dev, ~0.01–0.05 in production.      |
| `--tracing-jdbc-enabled`        | `KC_TRACING_JDBC_ENABLED`        | `true` (when tracing on) | **Build-time.**                                    |
| `--tracing-infinispan-enabled`  | `KC_TRACING_INFINISPAN_ENABLED`  | `true` (when tracing on) | **Build-time.**                                    |

Service name and resource attributes moved to `--telemetry-service-name` / `--telemetry-resource-attributes` (the `--tracing-*` variants are deprecated). Set both for traces and metrics consistency.

Pair with `--log-mdc-enabled=true` and a JSON log format that includes `trace_id` / `span_id` so traces and logs link up in Tempo/Grafana.

---

## <a id="kcadm"></a>12. `kcadm.sh`: the admin REST CLI

`kcadm.sh` is the official CLI for the admin REST API. Lives in the same `bin/` as `kc.sh`. Operates on JSON via the same endpoints the admin UI hits.

```bash
# Authenticate (writes to ~/.keycloak/kcadm.config)
kcadm.sh config credentials --server https://auth.example.com \
  --realm master --client admin-cli \
  --user alice --password '<...>'

# Or with a service account (better for CI)
kcadm.sh config credentials --server https://auth.example.com \
  --realm master --client my-cicd-client \
  --client-secret '<...>'

# Inspect
kcadm.sh get realms/myrealm
kcadm.sh get users -r myrealm -q username=alice

# Mutate
kcadm.sh create users -r myrealm -s username=bob -s enabled=true
kcadm.sh update users/<id> -r myrealm -s firstName=Bob

# Realm-level export of a single client (for terraform import etc.)
kcadm.sh get clients -r myrealm -q clientId=my-app --fields clientId,enabled,redirectUris
```

For CI/GitOps, prefer **terraform-provider-keycloak** (the keycloak/keycloak fork on registry.terraform.io is now the upstream-blessed one) or the operator's `KeycloakRealmImport` CR over kcadm.sh scripts — both are idempotent and diffable.

`kcadm.sh` uses `admin-cli` as the client by default; that's a built-in public client in the master realm. For non-master realms, create a dedicated confidential service-account client with appropriate `realm-management` roles assigned and use its `--client-secret`.
