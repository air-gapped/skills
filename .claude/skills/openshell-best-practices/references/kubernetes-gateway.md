# Kubernetes gateway — deployment reference (0.1.x)

Verified against the `v0.1.6` tag (chart `helm-chart` 0.1.6, `deploy/helm/openshell`,
`docs/kubernetes/*.mdx`). Re-read the chart's `values.yaml` and the docs at the tag you
deploy: the chart has ~220 values plus a free-form `gatewayConfig`, and weekly releases move
them.

## Contents

- Components and prerequisites
- Agent Sandbox (the CRD + controller OpenShell needs)
- The two charts
- Values that matter
- Ingress
- Authentication on Kubernetes
- Rendering offline, image lists
- Upgrades
- RBAC, HA and scale
- Known Kubernetes issues (open at 0.1.6)
- Verification

## Components and prerequisites

| Piece | What it is |
|---|---|
| Gateway | StatefulSet `openshell` (SQLite on a PVC) or Deployment (with PostgreSQL via `server.externalDbSecret`) |
| Agent Sandbox controller | kubernetes-sigs project; turns `Sandbox` objects (`agents.x-k8s.io/v1beta1`) into workload pods + `/sandbox` PVC |
| Supervisor | One pod per sandbox (default) or a shared pool (`supervisor_topology = "gateway"`, experimental in 0.1.6); owns the network boundary, policy, credential injection |
| Sandbox runtime | Init container `openshell-sandbox-bootstrap` copies a static binary into the workload pod; the workload image's entrypoint is replaced |

Prerequisites (setup.mdx): Kubernetes 1.29+, a CNI that **enforces** ingress and egress
NetworkPolicy in sandbox namespaces (Kubernetes accepts policies no CNI enforces — then
workloads bypass the supervisor), Helm 3, Agent Sandbox installed first. Nodes need Landlock
ABI v3 (Linux 6.2+) and seccomp user-notify.

## Agent Sandbox

Upstream ships one plain manifest per release (`sandbox.yaml`; `manifest.yaml` up to v0.5.1);
`extensions.yaml` (SandboxTemplate/Claim/WarmPool) is not needed by OpenShell. Its in-repo
Helm chart is not published and does not upgrade its CRD — use the manifest.

- Apply **server-side** (`kubectl apply --server-side -f sandbox.yaml`): the CRD is ~200 KB.
- Version: the docs install the floating `releases/latest`; OpenShell's CI tests pinned
  versions (`AGENT_SANDBOX_VERSION` in `e2e/support/install-agent-sandbox.sh`,
  `.github/workflows/release-canary.yml`, lanes in `branch-e2e.yml` — v1.0.3 for v1beta1,
  v0.4.6 for v1alpha1 at 0.1.6). Pin a version yourself. Treat CI's pin as tested-with, not a
  ceiling: upstream releases weekly; read the core-controller
  sections of every release between, diff the manifest (`kubectl diff --server-side`), and
  sweep issues. Router and warm-pool bugs don't affect OpenShell (not installed by `sandbox.yaml`).
- The controller's ClusterRole can create/delete pods, PVCs and Services cluster-wide, so
  whoever may create a `Sandbox` object effectively creates pods. Pod Security admission still
  applies to them.
- **After any Agent Sandbox upgrade, restart the gateway**: it detects the served `Sandbox`
  API once and caches it for the process lifetime.
- The chart's `agent-sandbox-preflight.yaml` fails the install when neither `v1beta1` nor
  `v1alpha1` is served.

## The two charts

| Chart | Purpose |
|---|---|
| `oci://ghcr.io/nvidia/openshell/helm-chart` | The gateway. Literally named `helm-chart`; `helm pull` writes `helm-chart-<ver>.tgz`. By default also creates the sandbox namespace's ServiceAccount/Role/NetworkPolicy |
| `oci://ghcr.io/nvidia/openshell/openshell-workspace` | Only those per-namespace pieces, for platform-managed namespaces (`workspaceMode: operator`) where the gateway must not get cluster-wide rights. Install with `workspaceResources.enabled=false` on the gateway. README says **Experimental**; multi-tenant proxy (#2385) is a GA blocker in #4218 |

Workspace modes (`server.drivers.kubernetes.workspaceMode`): `shared` (default, one
namespace), `managed` (gateway creates `openshell-{gateway_id}-{workspace}` namespaces, needs
cluster RBAC), `operator` (pre-provisioned allowlisted namespaces + workspace chart in each).

## Values that matter

| Value | Why |
|---|---|
| `server.telemetryEnabled: false` | On by default; posts anonymous events to `events.telemetry.data.nvidia.com` from gateway and supervisors |
| `server.dataStorageClass`, `server.dataStorageSize` | Feed the StatefulSet's **immutable** `volumeClaimTemplates`: set at install. Use block storage, not NFS |
| `gatewayConfig."openshell.gateway.oidc"` `{issuer, audience, roles_claim, admin_role, user_role}` | OIDC user auth; set both roles or neither (auth-only mode). `server.oidc.*` still works as a deprecated alias |
| `server.tls.clientCaSecretName: ""` | HTTPS-only transport when users authenticate with OIDC. Use `""`, never `null` |
| `server.oidc.caConfigMapName` | Chart-owned (not an alias). Issuer behind a private CA (key `ca.crt`); becomes `SSL_CERT_FILE`, which **replaces** the gateway's trust roots |
| `server.credentialStorage.existingSecret` | Required for GitOps/`helm template` workflows: without Helm's `lookup`, the chart regenerates the credential key-encryption key on every render and stored credentials become unreadable |
| `global.image.registry` / `.tag` | Mirror for gateway, supervisor and sandbox runtime. Keep supervisor and sandbox runtime on the same release — a mismatch fails at sandbox start |
| `sandbox.image.*` | Default workload image (`nvcr.io/nvidia/base/ubuntu:24.04`); a full reference, not rewritten by `global.image.registry` |
| `server.sandboxImagePullSecrets`, `imagePullSecrets` | Pull secrets for sandbox workload **and** per-sandbox supervisor pods (must exist in the sandbox namespace; managed workspace mode copies them), and for gateway/hook/shared-supervisor pods |
| `upstreamProxy.*` | Corporate forward proxy for policy-approved TLS egress; `caBundle` for an intercepting proxy. Plain HTTP is never proxied, the auth Secret lives in the sandbox namespace, and the CA is trusted for all upstreams — details in `air-gap-and-ca.md` |
| `server.externalDbSecret` + `workload.kind: deployment` | PostgreSQL; required for `replicaCount > 1` |
| `server.credentialDrivers.kubernetesSecrets` / `.vault` | Store provider credentials outside the gateway DB |
| `pkiInitJob.serverDnsNames` | Extra SANs on the gateway cert (a wildcard also enables sandbox service URLs). Set at install: the certgen hook skips while its three Secrets exist |
| `agentSandbox.preflight.enabled` | Leave on for installs; offline renders pass the API instead (below) |

**Chart schema v2 (since 0.1.x, #3060):** application settings live in `gatewayConfig`,
keyed by flat gateway.toml table names, with snake_case fields:

```yaml
gatewayConfig:
  openshell.gateway.oidc: {issuer: https://idp/realms/x, audience: openshell-cli,
                           roles_claim: realm_access.roles, admin_role: openshell-admin, user_role: openshell-user}
  openshell.drivers.kubernetes: {workspace_mode: shared}
  openshell.gateway: {log_level: info}
```

The old `server.*` application values (`server.oidc.*`, `server.logLevel`, `server.otlp.*`,
`server.drivers.kubernetes.*`, `server.credentialDrivers.*`, `supervisor.image.*`,
`upstreamProxy.*`, …) are **deprecated aliases**: they still render, `gatewayConfig` wins on
conflict, and they will go away — write new values in `gatewayConfig`
(`docs/kubernetes/migrate-gateway-config.mdx` has the full mapping). Values that own
Kubernetes resources stay chart values: `server.disableTls`, TLS Secret names,
`server.externalDbSecret`, `server.sandboxNamespace`, `server.oidc.caConfigMapName`,
`server.telemetryEnabled`, Service and certificate settings. The chart rejects
`database_url`, inline URL credentials and PEM keys in `gatewayConfig`, and silently
overwrites the driver keys `namespace`, `service_account_name`, `host_gateway_ip` and
`client_tls_secret_name` from chart values. There is no `values.schema.json`: a misspelled
value is ignored. Less common driver and gateway knobs: `rare-settings.md`.

## Ingress

The chart offers only Gateway API (`grpcRoute.*`, e.g. Envoy Gateway) and an OpenShift Route.
Everything the CLI does — API, `connect`/`exec` sessions, `openshell forward` — is gRPC over
one HTTP/2 endpoint, so any HTTP/2-capable proxy works. Without a GatewayClass, write the
route yourself. Traefik pattern (TLS terminated at Traefik with a public cert, re-encrypted to
the gateway):

```yaml
apiVersion: traefik.io/v1alpha1
kind: ServersTransport
metadata: {name: openshell-gateway, namespace: openshell}
spec:
  serverName: openshell.openshell.svc      # a SAN the chart's certgen always adds
  rootCAs: [{secret: openshell-client-tls}] # Traefik reads its ca.crt key
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata: {name: openshell, namespace: openshell}
spec:
  entryPoints: [websecure]
  routes:
    - match: Host(`openshell.example.com`)
      kind: Rule
      services:
        - {name: openshell, port: 8080, scheme: https, serversTransport: openshell-gateway}
  tls: {secretName: cert-openshell}          # e.g. a cert-manager Certificate
```

Long-lived streams (`connect`, `exec`, watches) need the entrypoint's read timeout disabled
(Traefik v3 defaults `readTimeout` to 60 s: set `respondingTimeouts.readTimeout=0`).
TLS termination at the proxy means client certificates never reach the gateway, so this
pattern implies OIDC. For mTLS users, use TLS passthrough (SNI) and add the hostname to
`pkiInitJob.serverDnsNames`. Smoke test without the CLI:

```bash
curl -sS --http2 -X POST -H 'content-type: application/grpc' -H 'te: trailers' --data-binary '' \
  -D - -o /dev/null https://openshell.example.com/openshell.v1.OpenShell/ListSandboxes
# expect grpc-status: 16, grpc-message: missing authorization header
```

## Authentication on Kubernetes

See `auth.md`. Short version: OIDC for people (public client, PKCE, loopback redirect),
client credentials for unattended jobs, mTLS only for single-operator setups. Since 0.1.6
the gateway refuses to start with no user authentication unless
`[openshell.gateway.auth] allow_unauthenticated_users = true`.

## Rendering offline, image lists

- `helm template` cannot see cluster APIs, so the preflight fails. Pass the API instead of
  disabling the check: `-a agents.x-k8s.io/v1beta1 -a agents.x-k8s.io/v1beta1/Sandbox`.
- The rendered pods show only the gateway image. The supervisor and default workload images
  appear inside the `gateway.toml` ConfigMap (`supervisor_image`, `default_image`).
  `sandbox_runtime_image` is written only when `sandboxRuntime.image` or
  `global.image.registry`/`.tag` is set (a mirrored values file renders it); with stock values
  the gateway binary's default `ghcr.io/nvidia/openshell/sandbox:<version>` applies — derive it
  from the supervisor (same registry and tag) for the image list. Full mirror set: gateway,
  supervisor, sandbox, default workload, agent-sandbox-controller, plus every agent image users
  run (`air-gap-and-ca.md`).

## Upgrades

- 0.1.x → 0.1.y: `helm upgrade` with the new version and the same values; read every
  release's "Upgrade notes" in between (0.1.5: OCSF log file rename `.log`→`.jsonl`,
  annotation/label allowlists; 0.1.6: auth required, supervisor/sandbox runtime pairing,
  connection direction). Running sandboxes keep their supervisor and runtime images until
  they stop.
- From 0.0.x: not in place. Remove every sandbox, back up the DB, migrate `gatewayConfig` to
  schema v2 (`docs/kubernetes/migrate-gateway-config.mdx`), export provider profiles, then
  install 0.1.x and recreate sandboxes (`docs/upgrade/0-1-0.mdx`).

## RBAC, HA and scale

- The chart README itself still says "Experimental — the Kubernetes deployment path is under
  active development"; plan for breaking changes between 0.1.x releases.
- **Without cluster-admin** (0.1.3+): a cluster admin applies the rendered
  `clusterrole.yaml`/`clusterrolebinding.yaml`, the namespace admin installs with
  `rbac.clusterScoped.create=false` (shared mode with only the built-in `admin` role needs
  `rbac.create=false` and all RBAC pre-created).
- **Default-deny ingress namespaces**: allow TCP 5501 from the node (supervisor readiness probe).
- **Multi-replica**: `replicaCount > 1` requires `server.externalDbSecret` (Secret key `uri`)
  and normally `workload.kind: deployment`. Each pod opens up to 14 PostgreSQL connections,
  so size `max_connections ≥ (2 × replicas + surge) × 14` *before* upgrading; poolers must use
  **session** pooling (advisory locks). Replicas relay through the headless `openshell-peer`
  Service — no session affinity. Bring your own PDB and anti-affinity. Alert on
  `openshell_server_relay_rejected_total` and `openshell_server_mutation_lock_timeouts_total`
  (metrics port 9090, scrape pods).
- **Credentials at rest**: default store is AES-256-GCM in the gateway DB with the KEK in a
  retained Secret — back up the database and the KEK together. Kubernetes Secrets and
  Vault/OpenBao drivers exist; only one driver at a time, no migration between them.
- **Shared supervisor** (`supervisor_topology = "gateway"`, experimental in 0.1.6): one pool
  hosts many sandboxes, roughly doubling pod-limited capacity. Requires gateway TLS, rejects
  upstream proxy and SPIFFE settings, needs `supervisor.replicas ≥ 2` for failover; sandboxes
  freeze during takeover (`supervisor.recoveryTimeoutSeconds`, default 60). Readiness can
  report healthy before attachment (#4960). Resources are hard-coded (50m/64Mi, 1Gi limit) and
  only new generations switch topology (`rare-settings.md`).
- **OpenShift**: ≥ 4.19 (Landlock in RHCOS); null the pod/container `runAsUser`/`fsGroup`
  (`ci/values-openshift-scc.yaml`); passthrough Route + `certManager.serverIssuerRef`, or
  Gateway API on 4.22+.
- **Multi-tenancy reality**: OIDC RBAC is method-level; providers and sandboxes are not owned
  per subject. For hard tenant separation run separate gateways. No IdP-group → workspace
  mapping yet (#4286).

## Known Kubernetes issues (open at 0.1.6)

| Symptom | Issue | Workaround |
|---|---|---|
| Admission (Kyverno/Gatekeeper) rejects the agent pod: no `readOnlyRootFilesystem`; "timed out waiting for gated workload Pod" | #4290 | Exempt sandbox pods from that rule; the driver overwrites securityContext |
| Supervisor pod evicted under memory pressure (BestEffort QoS), sandbox dies | #3415 | Namespace `LimitRange` with default requests |
| `openshell policy set --global` makes every sandbox start fail ("policy is managed globally") | #4299 | Clear the global policy; pass `--policy` per sandbox |
| Gateway restart leaves sandboxes in `Error (StartFailed)` | #4910 | `sandbox stop` + `sandbox start` each (workspace kept) |
| Sandbox stuck `Provisioning` with replicas 0 after node reboot or fast stop/start | #4371 | None supported |
| Slow backends (Kata/CoCo peer-pods) killed by hard-coded 5-minute deadlines | #4364 | None in release images |
| v1beta1 stop/start hangs on supervisor readiness socket | #3566 | Recreate |
| No default StorageClass | — | Set `server.workspaceStorageClass` |

## Verification

- `kubectl -n openshell rollout status statefulset/openshell`
- Gateway log: `OIDC JWKS keys loaded`, `Compute driver connected configured_driver=kubernetes`,
  zero `WARN`/`ERROR`.
- `openshell status` → `Authenticated (OIDC)`, `Version` matches.
- A throwaway sandbox: `openshell sandbox create --name smoke --no-keep --no-tty -- sh -c 'id; uname -r'`
  (expect UID 10001) and nothing left behind in the namespace afterwards.
