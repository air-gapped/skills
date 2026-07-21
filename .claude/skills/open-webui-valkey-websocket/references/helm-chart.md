# Helm chart reference (`open-webui/helm-charts`)

Chart **v15.2.0 → appVersion 0.10.2**, released 2026-07-01 (was v14.6.0/0.9.5). The 14→15 major bump was **not** audited for breaking changes this pass; what was checked is that the structures this file depends on survived — `websocket:` is still a top-level block (line 66) and `replicaCount: 1` still present (line 183). Released 2026-05-20 for the prior pin. Repo URL: `https://helm.openwebui.com/`. Maintainer (`westbrook-ai`) explicitly volunteer-maintained: *"this repo is maintained by volunteers and is admittedly not always perfect."*

This is the supported Kubernetes deployment path (per the maintainer's own confirmation on issue #338, 2026-02-01) but it ships sparse defaults. The list below is what to override and what the chart doesn't cover.

## What the chart auto-decides

The chart picks workload kind based on persistence:

```yaml
# templates/workload-manager.yaml
{{- $workloadKind := .Values.workload.kind | default (
  ternary "StatefulSet" "Deployment"
    (and .Values.persistence.enabled (eq .Values.persistence.provider "local"))
) }}
```

For stateless multi-pod, force Deployment explicitly:

```yaml
workload:
  kind: Deployment
```

Default `replicaCount: 1` — bump to 3 minimum for HA at 1000+ users.

## Bundled Redis is not for production

```yaml
# values.yaml lines 51-140 (default)
websocket:
  enabled: true
  manager: redis
  redis:
    enabled: true                    # ← THE TRAP
    image:
      repository: redis
      tag: 7.4.2-alpine3.21
    service:
      port: 6379
      type: ClusterIP
```

Looking at `templates/websocket-redis.yaml`: the bundled Redis is a single-pod plain `apps/v1 Deployment` with **no PVC, no auth, no resources, no Sentinel, no Cluster, no replication**. It's "good enough to demo, not production-grade." On every pod restart, all state is gone — sessions, models cache, ydoc CRDT, ratelimit buckets, rate limits, all reset.

The chart README does not warn about this. Operators routinely leave it enabled and find out the hard way when a node reboot wipes Valkey state mid-day.

**Production override: disable the bundled Redis and point at external Valkey:**

```yaml
websocket:
  enabled: true
  manager: redis
  redis:
    enabled: false                   # turn it OFF
  url: ""                            # leave empty if using existingSecret
  existingSecret: "valkey-credentials"     # added in chart v13.2.0
  existingSecretKey: "redis-url"
```

The Secret should contain the full URL with creds:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: valkey-credentials
type: Opaque
stringData:
  redis-url: "redis://default:HUNTER2@valkey-master.valkey.svc.cluster.local:6379/0"
  websocket-redis-url: "redis://default:HUNTER2@valkey-master.valkey.svc.cluster.local:6379/1"
```

## Env wiring

`templates/workload-manager.yaml` lines 301–323 inject:

```yaml
- name: "ENABLE_WEBSOCKET_SUPPORT"
  value: {{ ternary "True" "False" .Values.websocket.enabled | quote }}
{{- if .Values.websocket.enabled }}
- name: "WEBSOCKET_MANAGER"
  value: {{ .Values.websocket.manager | default "redis" | quote }}
- name: "REDIS_URL"
  value: {{ include "websocket.redis.url" . | quote }}
- name: "WEBSOCKET_REDIS_URL"
  value: {{ include "websocket.redis.url" . | quote }}
{{- end }}
```

By default `REDIS_URL` and `WEBSOCKET_REDIS_URL` are set to **the same URL** — meaning websocket pub/sub and general app state share the same DB (database 0). The official Redis tutorial recommends splitting (`/0` for app state, `/1` for websockets) for "better organization and potential performance optimization."

To enforce the split via the chart, override the URLs explicitly via `extraEnv`:

```yaml
extraEnvVars:
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: valkey-credentials
        key: redis-url            # ends in /0
  - name: WEBSOCKET_REDIS_URL
    valueFrom:
      secretKeyRef:
        name: valkey-credentials
        key: websocket-redis-url  # ends in /1
  - name: REDIS_SENTINEL_HOSTS
    value: "valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2"
  - name: REDIS_SENTINEL_PORT
    value: "26379"
  - name: WEBSOCKET_SENTINEL_HOSTS
    value: "valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2"
  - name: WEBSOCKET_SENTINEL_PORT
    value: "26379"
  - name: REDIS_KEY_PREFIX
    value: "open-webui"
  - name: REDIS_HEALTH_CHECK_INTERVAL
    value: "60"
  - name: REDIS_SOCKET_KEEPALIVE
    value: "True"
  - name: REDIS_SOCKET_CONNECT_TIMEOUT
    value: "5"
  - name: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE
    value: "10"                          # the #23733 mitigation
  - name: ENABLE_DB_MIGRATIONS
    value: "false"                       # set to "true" only on the designated migration pod
  - name: WEBUI_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: openwebui-secrets
        key: secret-key
  - name: OAUTH_PICTURE_CLAIM
    value: ""
  - name: OAUTH_UPDATE_PICTURE_ON_LOGIN
    value: "false"
```

## Ingress / sticky sessions — chart ships nothing

`values.yaml` lines 296–331 set up a basic `Ingress`, but **no built-in sticky-session annotation, no service `sessionAffinity: ClientIP`**.

The multi-replica troubleshooting docs page recommends:

```yaml
ingress:
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    # AWS ALB users: enable Target Group Stickiness on the TG instead
```

Strictly required only with polling fallback. With `WEBSOCKET_MANAGER=redis` and pure WS transport, not required, but enabling cookie affinity smooths jitter and costs nothing.

## What the chart does not ship

| Resource | Chart provides? | What to add |
|---|---|---|
| `HorizontalPodAutoscaler` | No template | Add an `autoscaling/v2` HPA externally. CPU @ 70% is a reasonable start, but OWUI is mostly I/O-bound waiting on upstream LLMs — a custom metric (active sessions or request rate) via Prometheus Adapter is preferable when available. |
| `PodDisruptionBudget` | No template | `minAvailable: 2` so rolling updates don't drop the cluster below capacity for 1000 users. |
| `livenessProbe` / `readinessProbe` / `startupProbe` | All default to `{}` | Liveness `/health`, readiness `/ready` (added in 0.9.0; only returns 200 once startup + DB ping + Valkey ping all succeed). |
| `Service` `sessionAffinity` | Not set | Add at ingress level (above) instead. |
| Migration init container | No | Either run migrations from a separate `Job` before rollout, or designate one pod with `ENABLE_DB_MIGRATIONS=true` and the rest with `false`. |
| `topologySpreadConstraints` | Field exposed (`workload.topologySpreadConstraints`), no defaults | Add explicit topology constraints across zones / nodes for HA. |

## Probe override block

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready          # 0.9.0+ — gates traffic on DB + Valkey ping
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
  successThreshold: 1

startupProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30      # allow ~5 min for cold-start (model probing, OAuth init, etc)
```

## Recent chart history

| Version | Change |
|---|---|
| v15.2.0 | appVersion 0.10.2. **Current as of 2026-07-01.** Majors 15.0.0/15.1.0 both landed 2026-06-29 — breaking changes unreviewed. |
| v14.11.0 | appVersion 0.10.x line. 2026-06-28. Last 14.x. |
| v14.6.0 | appVersion 0.9.5. 2026-05-20. |
| v14.5.0 | appVersion 0.9.5. 2026-05-11. |
| v14.4.0 | appVersion 0.9.4. 2026-05-09. |
| v13.3.1 | Fixed `ENABLE_WEBSOCKET_SUPPORT=False` not being explicitly set when websocket disabled. |
| v13.2.0 | Added `websocket.existingSecret` so `REDIS_URL`/`WEBSOCKET_REDIS_URL` can come from K8s Secrets (#341 fix). |
| (earlier) | Added `workload.kind` override so operators can force Deployment regardless of persistence settings (#326). |

## Open chart issues

- **#383 (open, 2026-04-21)** — gateway-API users (e.g. `kgateway`) need `service.appProtocol: kubernetes.io/ws` on the Service for some controllers to recognize WebSocket traffic. Unfixed. Workaround: patch the Service post-deploy.

## A worked-out values block

Putting it all together for a 1000-user multi-pod deployment with external Valkey Sentinel:

```yaml
replicaCount: 3
workload:
  kind: Deployment
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: kubernetes.io/hostname
      whenUnsatisfiable: ScheduleAnyway
      labelSelector:
        matchLabels:
          app.kubernetes.io/name: open-webui

resources:
  requests:
    cpu: "1"
    memory: "2Gi"
  limits:
    cpu: "4"
    memory: "8Gi"

# Disable bundled Redis; we run Valkey externally
websocket:
  enabled: true
  manager: redis
  redis:
    enabled: false
  existingSecret: "valkey-credentials"
  existingSecretKey: "redis-url"

# Postgres for app state and pgvector
extraEnvVars:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url
  - name: DATABASE_POOL_SIZE
    value: "15"
  - name: DATABASE_POOL_MAX_OVERFLOW
    value: "20"
  - name: VECTOR_DB
    value: "pgvector"
  - name: PGVECTOR_DB_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url
  - name: WEBSOCKET_REDIS_URL
    valueFrom:
      secretKeyRef:
        name: valkey-credentials
        key: websocket-redis-url
  - name: REDIS_SENTINEL_HOSTS
    value: "valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2"
  - name: REDIS_SENTINEL_PORT
    value: "26379"
  - name: WEBSOCKET_SENTINEL_HOSTS
    value: "valkey-sentinel-0,valkey-sentinel-1,valkey-sentinel-2"
  - name: WEBSOCKET_SENTINEL_PORT
    value: "26379"
  - name: REDIS_KEY_PREFIX
    value: "open-webui"
  - name: REDIS_HEALTH_CHECK_INTERVAL
    value: "60"
  - name: REDIS_SOCKET_KEEPALIVE
    value: "True"
  - name: REDIS_SOCKET_CONNECT_TIMEOUT
    value: "5"
  - name: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE
    value: "10"
  - name: UVICORN_WORKERS
    value: "1"
  - name: ENABLE_DB_MIGRATIONS
    value: "false"
  - name: CONTENT_EXTRACTION_ENGINE
    value: "tika"
  - name: TIKA_SERVER_URL
    value: "http://tika.openwebui.svc.cluster.local:9998"
  - name: RAG_EMBEDDING_ENGINE
    value: "openai"
  - name: WEBUI_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: openwebui-secrets
        key: secret-key
  - name: OAUTH_PICTURE_CLAIM
    value: ""
  - name: OAUTH_UPDATE_PICTURE_ON_LOGIN
    value: "false"

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
  hosts:
    - host: chat.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: chat-tls
      hosts: [chat.example.com]

livenessProbe:
  httpGet: { path: /health, port: http }
  initialDelaySeconds: 30
  periodSeconds: 30
readinessProbe:
  httpGet: { path: /ready, port: http }
  initialDelaySeconds: 10
  periodSeconds: 10
startupProbe:
  httpGet: { path: /health, port: http }
  failureThreshold: 30
  periodSeconds: 10
```

Plus a sibling `Job` (or one pod with `ENABLE_DB_MIGRATIONS=true`) for migrations, and a `PodDisruptionBudget`:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: openwebui
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: open-webui
```

## See also

- `references/configuration.md` for what each env var does.
- `references/known-issues.md` for #383 (gateway-API) and other helm-side issues.
