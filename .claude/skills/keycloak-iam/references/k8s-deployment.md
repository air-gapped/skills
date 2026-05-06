# Keycloak on Kubernetes — operator and raw-manifest deployment

Targets Keycloak 26.6.x on K8s 1.27+. The Keycloak Operator is the recommended path; raw manifests are documented for environments where the operator can't run (no cluster-scoped RBAC, OLM-only, etc.).

## TOC
1. [Container image](#image)
2. [Operator: install + the `Keycloak` CR](#operator)
3. [The full Keycloak CR shape](#cr-shape)
4. [`KeycloakRealmImport` CR](#realm-import)
5. [Raw manifest deployment (no operator)](#raw-manifests)
6. [High-availability topology](#ha)
7. [Database: CloudNativePG, RDS, Crunchy](#db)
8. [Reverse proxy / ingress](#proxy)
9. [Probes](#probes)
10. [Resources, JVM tuning](#resources)
11. [Secrets and the Vault SPI](#secrets)
12. [Why HPA is a trap](#hpa)

---

## <a id="image"></a>1. Container image

Official: `quay.io/keycloak/keycloak:26.6.1`. UBI 9 base, OpenJDK 21 (the 21 is intentional; the FIPS-certified Bouncy Castle path is on 21, not 25, so the image stays on 21 even though Keycloak supports running on JDK 25). Multi-arch (amd64, arm64).

Custom image pattern (for `--optimized` + theme/provider bundling):

```dockerfile
FROM quay.io/keycloak/keycloak:26.6.1 AS builder
ENV KC_HEALTH_ENABLED=true \
    KC_METRICS_ENABLED=true \
    KC_DB=postgres \
    KC_FEATURES=organizations,admin-fine-grained-authz:v2,dpop
COPY my-custom-theme.jar /opt/keycloak/providers/
COPY my-custom-spi.jar /opt/keycloak/providers/
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.6.1
COPY --from=builder /opt/keycloak/ /opt/keycloak/
ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start", "--optimized"]
```

Then in the Keycloak CR:

```yaml
spec:
  image: registry.example.com/keycloak:26.6.1-mycorp
  startOptimized: true       # tells the operator NOT to override your --optimized
```

If `startOptimized` is unset, the operator decides based on whether `image` is the upstream stock image (skips `--optimized`) or a custom image (uses `--optimized`).

**Don't bake DB credentials, hostname, or TLS secrets into the image.** Bake build-time config (features, db vendor, themes, providers) only. Runtime config goes in the CR / env / Secrets.

---

## <a id="operator"></a>2. Operator: install + the `Keycloak` CR

### Install (without OLM)

The operator manifests live in `https://github.com/keycloak/keycloak-k8s-resources` — three files per version tag, under `kubernetes/`. Apply to install:

```bash
KC_VERSION=26.6.1
BASE=https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/$KC_VERSION/kubernetes

# CRDs first (cluster-scoped)
kubectl apply -f $BASE/keycloaks.k8s.keycloak.org-v1.yml
kubectl apply -f $BASE/keycloakrealmimports.k8s.keycloak.org-v1.yml

# Operator deployment + RBAC + ServiceAccount (namespace-scoped to keycloak namespace by default)
kubectl create namespace keycloak
kubectl -n keycloak apply -f $BASE/kubernetes.yml
```

The `kubernetes.yml` deploys the operator with namespace-scoped RBAC. To watch multiple namespaces, edit the operator deployment env to set `WATCH_NAMESPACES=ns1,ns2,ns3` (or `*` for all-namespaces, requires extra ClusterRole).

### Install (with OLM)

`kubectl apply -f https://operatorhub.io/install/keycloak-operator.yaml` if you're on OperatorHub-flavored OpenShift / OLM. Lifecycle is owned by OLM after that.

### Pin operator and Keycloak versions together

The operator at tag `26.6.1` is built and tested against Keycloak `26.6.1`. When you upgrade, upgrade both — the CRD schema can change between minor versions. Mismatched pairs fail in confusing ways (CRD validation rejects `spec.update.strategy=Auto` if you forgot to upgrade the CRD).

---

## <a id="cr-shape"></a>3. The full Keycloak CR shape

Authoritative source: the `keycloaks.k8s.keycloak.org-v1.yml` CRD at the version tag you're targeting. Use `python3 -c "import yaml; print(...)"` against the file, or browse the OpenAPIV3 schema. Top-level `spec` fields in 26.6.1:

| Field                            | Type     | What it does                                                                              |
|----------------------------------|----------|-------------------------------------------------------------------------------------------|
| `instances`                      | int      | Replica count. **Always ≥3 for HA** (JGroups quorum survives 1 pod restart).              |
| `image`                          | string   | Override image (defaults to the operator's bundled version)                               |
| `startOptimized`                 | bool     | Force `--optimized`. Set true if your image is pre-built; otherwise leave unset.          |
| `hostname`                       | object   | `{hostname, strict, backchannelDynamic, admin}`                                           |
| `http`                           | object   | `{httpEnabled, httpPort, httpsPort, tlsSecret, serviceName, serviceHttpPort, serviceHttpsPort, annotations, labels}` |
| `httpManagement`                 | object   | `{port}` for the management interface (default 9000)                                      |
| `proxy`                          | object   | `{headers}` — `xforwarded` or `forwarded`                                                 |
| `db`                             | object   | `{vendor, host, port, database, schema, url, usernameSecret, passwordSecret, poolInitialSize, poolMinSize, poolMaxSize}` |
| `cache`                          | object   | `{configMapFile}` — point at a ConfigMap holding `cache-ispn.xml`                          |
| `features`                       | object   | `{enabled: [], disabled: []}`                                                              |
| `bootstrapAdmin`                 | object   | `{user: {secret}, service: {secret}}` — Secret keys are `username`/`password` (or `client-id`/`client-secret`) |
| `admin`                          | object   | `{tlsSecret}` for mTLS to the admin endpoint                                              |
| `transaction`                    | object   | `{xaEnabled}`                                                                              |
| `truststores`                    | object   | Map of name → `{secret, configMap}` for additional CA bundles                              |
| `tracing`                        | object   | `{enabled, endpoint, protocol, samplerType, samplerRatio, compression}`                    |
| `telemetry`                      | object   | `{endpoint, protocol, serviceName, resourceAttributes}` — shared OTel settings             |
| `update`                         | object   | `{strategy: Auto|Recreate|Explicit, revision, scheduling, labels}` — **see §zero-downtime** |
| `import`                         | object   | `{scheduling}` — config for the realm-import Job                                           |
| `additionalOptions`              | array    | `[{name, value, secret}]` — pass through any `KC_*` option                                |
| `env`                            | array    | Extra env vars (use this for `KCRAW_*`, custom JVM opts, etc.)                            |
| `resources`                      | object   | Standard K8s resource requests/limits                                                      |
| `livenessProbe` / `readinessProbe` / `startupProbe` | object | Override probe timing (defaults are usually fine)                          |
| `scheduling`                     | object   | `{affinity, tolerations, topologySpreadConstraints, priorityClassName}`                    |
| `networkPolicy`                  | object   | `{enabled, http: [...], https: [...], management: [...]}` — operator-generated NetworkPolicy |
| `ingress`                        | object   | `{enabled, className, tlsSecret, annotations, labels}` — operator-managed Ingress (basic) |
| `serviceMonitor`                 | object   | Generate a Prometheus-Operator `ServiceMonitor`                                            |
| `imagePullSecrets`               | array    | Standard K8s                                                                               |
| `automountServiceAccountToken`   | bool     | `false` to opt out of K8s default token automount                                          |
| `unsupported`                    | object   | `{podTemplate}` — full pod template override. **Use sparingly** — anything you put here can break across operator versions. |

### Zero-downtime patch updates (`spec.update.strategy`)

New in 26.6 (now supported). Strategies:

| Strategy                  | Behavior                                                                                                  |
|---------------------------|-----------------------------------------------------------------------------------------------------------|
| `Recreate`                | Operator shuts down all pods, then starts the new ones. Default for non-zero-downtime upgrades.           |
| `Auto`                    | Operator picks: rolling update if it detects a compatible image change, recreate otherwise.               |
| `Explicit`                | You bump `spec.update.revision` to signal "I've verified this is a rolling-update-compatible change."     |

`Auto` runs a small probe to detect whether the new image's protocol/serialization formats are wire-compatible with the running ones. Across patch versions (26.6.0 → 26.6.1) this is always true. Across minor versions (26.5.x → 26.6.x) it's usually true. Across major (25.x → 26.x) it's often not.

For multi-cluster / cross-DC zero-downtime, the documented pattern lives at `https://www.keycloak.org/operator/rolling-updates`.

### Adding an option not in the spec

Use `spec.additionalOptions`. Either inline value or Secret reference:

```yaml
spec:
  additionalOptions:
    - name: log-level
      value: "info,org.keycloak.events:debug"
    - name: db-pool-max-size
      value: "200"
    - name: cache-remote-password
      secret:
        name: infinispan-creds
        key: password
```

These map to `--<option-name>=<value>` on the kc.sh start command. Use this for anything from server-config.md that's not a top-level CR field.

---

## <a id="realm-import"></a>4. `KeycloakRealmImport` CR

```yaml
apiVersion: k8s.keycloak.org/v2alpha1
kind: KeycloakRealmImport
metadata:
  name: my-realm
  namespace: iam
spec:
  keycloakCRName: keycloak              # the Keycloak CR to import into
  realm:
    realm: my-realm
    enabled: true
    displayName: "My Realm"
    sslRequired: external
    registrationAllowed: false
    bruteForceProtected: true
    permanentLockout: false
    failureFactor: 30
    waitIncrementSeconds: 60
    maxFailureWaitSeconds: 900
    clients:
      - clientId: my-app
        publicClient: true
        redirectUris: ["https://app.example.com/*"]
        webOrigins: ["https://app.example.com"]
        protocol: openid-connect
        attributes:
          "pkce.code.challenge.method": "S256"
```

Behavior:
- Operator runs a one-shot `Job` that calls `kc.sh import` against the Keycloak StatefulSet
- **Realm import is create-or-replace**, not merge. If the realm already exists, the import overwrites it. There's no "upsert just these fields" mode at the operator level.
- For incremental edits, use `kcadm.sh` or terraform-provider-keycloak — neither blows away the rest of the realm.

For complex realms, prefer terraform-provider-keycloak. For simple GitOps-style "this CR is the source of truth, blow away everything else" realm-as-config, the CR is fine.

---

## <a id="raw-manifests"></a>5. Raw manifest deployment (no operator)

Pattern: a `StatefulSet` (not a Deployment — sticky pod identity helps JGroups discovery and Postgres connection patterns), a headless `Service` for JGroups, a regular `Service` for app traffic, an `Ingress`, and Secrets for DB and bootstrap admin.

Skeleton (incomplete — fill in tracing, scheduling, etc.):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: keycloak-headless
  namespace: iam
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: keycloak
  ports:
    - { name: tcp-jgroups, port: 7800 }
---
apiVersion: v1
kind: Service
metadata:
  name: keycloak
  namespace: iam
spec:
  selector:
    app.kubernetes.io/name: keycloak
  ports:
    - { name: http, port: 8080, targetPort: 8080 }
    - { name: https, port: 8443, targetPort: 8443 }
    - { name: management, port: 9000, targetPort: 9000 }
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: keycloak
  namespace: iam
spec:
  serviceName: keycloak-headless
  replicas: 3
  selector:
    matchLabels: { app.kubernetes.io/name: keycloak }
  template:
    metadata:
      labels: { app.kubernetes.io/name: keycloak }
    spec:
      containers:
        - name: keycloak
          image: quay.io/keycloak/keycloak:26.6.1
          args: ["start", "--optimized"]
          env:
            - name: KC_HOSTNAME
              value: "https://auth.example.com"
            - name: KC_HOSTNAME_STRICT
              value: "true"
            - name: KC_PROXY_HEADERS
              value: "xforwarded"
            - name: KC_HTTP_ENABLED
              value: "true"
            - name: KC_DB
              value: "postgres"
            - name: KC_DB_URL_HOST
              value: "postgres-rw.iam.svc"
            - name: KC_DB_URL_DATABASE
              value: "keycloak"
            - name: KC_DB_USERNAME
              valueFrom: { secretKeyRef: { name: keycloak-db, key: username } }
            - name: KC_DB_PASSWORD
              valueFrom: { secretKeyRef: { name: keycloak-db, key: password } }
            - name: KC_HEALTH_ENABLED
              value: "true"
            - name: KC_METRICS_ENABLED
              value: "true"
            - name: KC_CACHE
              value: "ispn"
            - name: KC_CACHE_STACK
              value: "kubernetes"
            - name: KUBERNETES_NAMESPACE
              valueFrom: { fieldRef: { fieldPath: metadata.namespace } }
            - name: JAVA_OPTS_APPEND
              value: "-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
            # bootstrap admin — only set on first install, then remove
            - name: KC_BOOTSTRAP_ADMIN_USERNAME
              valueFrom: { secretKeyRef: { name: keycloak-bootstrap, key: username } }
            - name: KC_BOOTSTRAP_ADMIN_PASSWORD
              valueFrom: { secretKeyRef: { name: keycloak-bootstrap, key: password } }
          ports:
            - { containerPort: 8080, name: http }
            - { containerPort: 8443, name: https }
            - { containerPort: 9000, name: management }
            - { containerPort: 7800, name: tcp-jgroups }
          startupProbe:
            httpGet: { path: /health/started, port: management }
            periodSeconds: 1
            failureThreshold: 600
          livenessProbe:
            httpGet: { path: /health/live, port: management }
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet: { path: /health/ready, port: management }
            periodSeconds: 10
            failureThreshold: 3
          resources:
            requests: { cpu: 500m, memory: 1Gi }
            limits:   { cpu: "2",  memory: 2Gi }
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels: { app.kubernetes.io/name: keycloak }
                topologyKey: kubernetes.io/hostname
```

For `KC_CACHE_STACK=kubernetes`, the pod's ServiceAccount needs `pods` `get,list,watch` RBAC in its own namespace. The operator generates this; for raw manifests, add it yourself.

For non-K8s discovery (or stricter PSPs), `KC_CACHE_STACK=jdbc-ping` works without K8s API access — peers discover each other via a Postgres table.

---

## <a id="ha"></a>6. High-availability topology

### Single-cluster HA (the default expectation)

3+ Keycloak replicas in the same K8s cluster, embedded clustered Infinispan with `kubernetes` or `jdbc-ping` discovery, single Postgres (preferably HA-Postgres like CloudNativePG or RDS multi-AZ). This handles single-pod and single-node failures, with bounded session loss for users on the dying pod.

### Multi-cluster / cross-DC HA

Two patterns supported in 26.x:

1. **Active-passive**: One cluster takes traffic, the other is warm. DB replicates between sites (CNPG cross-cluster, AWS RDS read replica, etc.). On failover, switch DNS + promote the replica.
2. **Active-active with external Infinispan**: Both clusters serve traffic. Each Keycloak cluster points at its local Infinispan, and the Infinispan clusters do site-to-site replication. Sessions survive a DC outage.

The active-active pattern was rewritten in 26.x to use external Infinispan (the legacy embedded JGroups cross-site path is deprecated and being removed). The full guide lives at `https://www.keycloak.org/high-availability/`. Don't roll your own — the failure modes are subtle (split-brain handling, session ownership, lock service).

---

## <a id="db"></a>7. Database: CloudNativePG, RDS, Crunchy

26.6 release notes specifically call out **CloudNativePG 1.29** as the recommended K8s-native Postgres. Why: it does WAL archiving, point-in-time recovery, multi-AZ replicas, automated failover, and `PgBouncer` connection pooling out of the box. Crunchy Postgres for K8s is the equivalent commercial option.

Outside K8s: **RDS for Postgres / Aurora Postgres** is the most widely deployed combo. Aurora multi-region was specifically called out in the 26.x release stream.

### Connection pool sizing

Keycloak ships with the Agroal connection pool (default `KC_DB_POOL_MAX_SIZE=100`). With 3 replicas, that's 300 max connections at the DB. Verify Postgres `max_connections` (default 100, often bumped to 200–500). For really large deployments, drop `KC_DB_POOL_MAX_SIZE` to ~50 per pod and put a real PgBouncer in front in transaction-pooling mode (PgBouncer in session-pooling mode + Keycloak's pool double-pools and gives you nothing).

### Database TLS

Required for any setup where DB traffic crosses an untrusted network. As of 26.6, use the simplified `--db-tls-mode=verify-full` + `--db-tls-trust-store-file` instead of stuffing `?ssl=true&sslmode=verify-full&sslrootcert=...` into `--db-url-properties`. Both work; the new options are clearer.

---

## <a id="proxy"></a>8. Reverse proxy / ingress

Common patterns:

| Proxy             | Required setup                                                                                            |
|-------------------|-----------------------------------------------------------------------------------------------------------|
| ingress-nginx     | `nginx.ingress.kubernetes.io/proxy-buffer-size: 16k` (admin console + large auth requests blow the default 4k). `nginx.ingress.kubernetes.io/backend-protocol: HTTPS` if Keycloak runs HTTPS. |
| Istio Gateway     | `VirtualService` with `match.uri.prefix: /` to the Keycloak service. Set `EnvoyFilter` headers if you want `Forwarded` rather than `X-Forwarded-*`. |
| OpenShift Route   | Reencrypt (Route TLS to Keycloak HTTPS) or Edge (Route TLS to Keycloak HTTP). Edge needs `--http-enabled=true`. |
| AWS ALB / GCP LB  | Cloud LB sets `X-Forwarded-*` automatically. Just `KC_PROXY_HEADERS=xforwarded`.                          |
| Cloudflare        | Cloudflare sets `Cf-Connecting-IP` and `X-Forwarded-Proto`. `KC_PROXY_HEADERS=xforwarded` works; lock `--proxy-trusted-addresses` to Cloudflare's IP ranges. |

26.6 added client-cert lookup providers for **Traefik** and **Envoy** (`--spi-x509cert-lookup-provider=traefik|envoy`) for mTLS scenarios where the proxy terminates the cert and forwards it via header.

---

## <a id="probes"></a>9. Probes

All probes go to the **management port** (9000 by default), HTTP scheme (unless you've forced management HTTPS). Operator defaults:

| Probe         | Path             | periodSeconds | failureThreshold | Notes                                                              |
|---------------|------------------|---------------|------------------|--------------------------------------------------------------------|
| startup       | `/health/started` | 1            | 600              | 600s is generous — covers slow boots and Liquibase migration.      |
| readiness     | `/health/ready`   | 10           | 3                | 26.6: returns UP during DB migration so K8s doesn't kill mid-migrate.|
| liveness      | `/health/live`    | 10           | 3                |                                                                    |

The 26.6 change to `/health/ready` is the kind of thing operators shouldn't need to know about — but if you've inherited a manifest with cargo-culted `failureThreshold: 60` on readiness from a 25.x setup to "survive migrations," you can remove it now.

---

## <a id="resources"></a>10. Resources, JVM tuning

Baseline for production (3 replicas, ~50 RPS, ~20k users):

```yaml
resources:
  requests: { cpu: 500m,  memory: 1Gi }
  limits:   { cpu: "2",   memory: 2Gi }
env:
  - name: JAVA_OPTS_APPEND
    value: "-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError -XX:+UseG1GC"
```

`MaxRAMPercentage=75` sizes the JVM heap to 75% of the container memory limit, leaving room for off-heap caches (Infinispan, JIT, native libs). `+UseG1GC` is the default on JDK 17+ but doesn't hurt to be explicit. `+ExitOnOutOfMemoryError` makes K8s restart the pod on OOM (without it, the JVM stalls).

For higher throughput, scale **vertically first** (bump CPU + memory) before adding replicas — JGroups overhead grows with cluster size. 5 replicas is reasonable; 10 is the upper end before you should consider external Infinispan.

`keycloak-benchmark` (`https://github.com/keycloak/keycloak-benchmark`) is the upstream load harness — run it against your target topology before committing to a sizing.

---

## <a id="secrets"></a>11. Secrets and the Vault SPI

Three Secret bundles a Keycloak deployment typically needs:

1. **DB credentials** — `keycloak-db` with keys `username`/`password`. Referenced by `spec.db.usernameSecret` / `passwordSecret`.
2. **Bootstrap admin** — `keycloak-bootstrap` with keys `username`/`password`. Referenced by `spec.bootstrapAdmin.user.secret`. Remove after first reconcile.
3. **TLS cert** — `keycloak-tls` (type `kubernetes.io/tls`). Referenced by `spec.http.tlsSecret`. Cert-manager auto-renews, and Keycloak hot-reloads on `--https-certificates-reload-period` (default 1h).

Beyond that, **Vault SPI** (now supports client secrets in 26.6) lets realm-level secrets live in HashiCorp Vault rather than the Keycloak DB:

- `--vault=keystore` (file-based, simpler) or `--vault=hashicorp` (Vault HTTP API)
- Reference vault keys in client config with `${vault.my-key}` syntax
- 26.6 expanded this to client secrets specifically — previously only SMTP/LDAP/IdP secrets

For broader integration, the **External Secrets Operator** + **CSI Secrets Store** provider pattern works with any Keycloak version: ESO syncs from your secret store into K8s Secrets, Keycloak consumes them via env. Less Keycloak-specific magic, more cluster-wide consistency.

`KCRAW_*` (vs `KC_*`) is what to use when an env-injected secret might contain literal `$` — e.g. a bcrypt hash or a generated password.

---

## <a id="hpa"></a>12. Why HPA is a trap

Tempting: "scale Keycloak based on CPU." Don't. Reasons:

- User sessions live in **clustered Infinispan caches**. Adding a pod triggers JGroups rebalance — load spikes during the rebalance, the autoscaler may scale up *more*, …
- Removing a pod migrates session ownership to surviving pods. If the autoscaler scales down aggressively (e.g. during a brief lull), sessions get redistributed unnecessarily.
- The scale-up signal lags real demand by minutes (HPA's metric scrape window + container startup). For a login-spike workload (e.g. 9am at a corp), the autoscaler is always behind.
- Keycloak boots in 30–60s, *then* JGroups joins, *then* it's ready to take real load. Not a fast scaler.

What to do instead:
- **Provision for peak.** A 3-replica deployment sized for 2× peak handles load spikes and survives a pod failure.
- **`PodDisruptionBudget` with `minAvailable: 2`** — protects against eviction storms.
- If you really need elasticity, scale **the layer in front** (ingress controllers / API gateway) and keep Keycloak fixed.

If you must HPA anyway: limit the range tightly (e.g. `minReplicas: 3, maxReplicas: 5`), use a long stabilization window (`scaleDown.stabilizationWindowSeconds: 600`), and watch session-loss metrics carefully.
