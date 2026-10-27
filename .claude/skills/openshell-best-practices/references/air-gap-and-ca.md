# Air-gapped sites and private CAs (0.1.x)

Verified against `v0.1.6`; #3292 (additional destination CAs) landed on main after 0.1.6.

## Contents

- What reaches the internet
- Images to mirror
- Private CA: which component needs it

## What reaches the internet

| Caller | Destination | Control |
|---|---|---|
| Gateway + supervisors | `events.telemetry.data.nvidia.com` (anonymous telemetry, **on by default**) | `server.telemetryEnabled: false` (renders `OPENSHELL_TELEMETRY_ENABLED`, propagated to supervisors); `OPENSHELL_TELEMETRY_ENDPOINT` overrides; or build with `--features defaults-without-telemetry` |
| Gateway | OIDC issuer discovery + JWKS | Your IdP only |
| Kubelet | Every image below | Mirror |
| Sandboxes | Whatever policy + providers allow | Default policy denies all network |

No update checks. The chart itself comes from `oci://ghcr.io/nvidia/openshell/helm-chart` —
mirror it or vendor the `.tgz`.

## Images to mirror

| Image | Set by |
|---|---|
| `ghcr.io/nvidia/openshell/gateway:<ver>` | `gateway.image.*` / `global.image.*` (also used by the certgen hook) |
| `ghcr.io/nvidia/openshell/supervisor:<ver>` | `supervisor.image.*` / `global.image.*` |
| `ghcr.io/nvidia/openshell/sandbox:<ver>` | `sandboxRuntime.image.*` / `global.image.*` — not in the render unless overridden |
| `nvcr.io/nvidia/base/ubuntu:24.04` | `sandbox.image.*` (default workload image; full ref, not prefixed by `global.image.registry`) |
| `registry.k8s.io/agent-sandbox/agent-sandbox-controller:<ver>` | Edit in the Agent Sandbox manifest |
| Your agent images | Per `sandbox create --from` (the old `openshell-community` images are archived and break on 0.1.x — see `sandboxes-and-agents.md`) |

Keep the `openshell/...` repository path under the mirror prefix. Pull secrets:
`imagePullSecrets` (gateway, hooks, shared supervisor) and `server.sandboxImagePullSecrets`
(sandbox pods; Secret must live in the sandbox namespace).

## Private CA: which component needs it

Agent traffic is intercepted: the workload talks to the supervisor, which terminates TLS with
a per-sandbox CA and opens the real upstream connection itself. So the trust decision for
an internal HTTPS service is made by the **supervisor**, not the agent image.

| Path | 0.1.6 mechanism |
|---|---|
| Gateway → OIDC issuer | `server.oidc.caConfigMapName` (key `ca.crt`) → `SSL_CERT_FILE`. **Replaces** the system roots for the whole gateway process (rustls-native-certs) — include every root it needs |
| Gateway → Vault | `server.credentialDrivers.vault.caConfigMapName` |
| CLI → gateway | CLI pins `~/.config/openshell/gateways/<name>/mtls/ca.crt` if present, else the OS trust store |
| Supervisor → internal HTTPS upstream (Kubernetes) | **No config in 0.1.6.** Rebuild the supervisor image with the CA appended to `/etc/ssl/certs/ca-certificates.crt` (read first, plus bundled Mozilla roots). Main (#3292) adds `supervisor.network.additionalCaConfigMapName` |
| Supervisor → intercepting corporate proxy | `upstreamProxy.caBundle.configMapName` (only valid with a proxy configured, and not with the shared supervisor). Supply **only** the proxy/interception CA: a full merged bundle (e.g. OpenShift's injected trusted bundle) can exceed the sandbox boundary's control-frame budget |
| Supervisor → upstream (Podman) | `additional_ca_bundle` (0.1.5) |
| Agent → supervisor | Automatic: the supervisor writes `/etc/openshell-tls/{openshell-ca.pem,ca-bundle.pem}` and sets `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO`, `NODE_EXTRA_CA_CERTS`, `DENO_CERT`. Tools that ignore these (Java keystores) won't trust it |

The supervisor image is distroless (`gcr.io/distroless/base-nossl-debian13` + one binary): no
shell, no `update-ca-certificates`, no `RUN` possible on top. Build the bundle in a helper
stage and **append** (the sandbox's bundle is derived from this file, so replacing it drops
public roots for tools inside the sandbox):

```dockerfile
FROM debian:13-slim AS ca
COPY --from=ghcr.io/nvidia/openshell/supervisor:0.1.6 /etc/ssl/certs/ca-certificates.crt /bundle.crt
COPY site-root-ca.crt /site.crt
RUN cat /bundle.crt /site.crt > /out.crt

FROM ghcr.io/nvidia/openshell/supervisor:0.1.6
COPY --from=ca /out.crt /etc/ssl/certs/ca-certificates.crt
```

Point `supervisor.image` at it and keep the sandbox runtime on the same release tag.
Putting the CA into agent images does not help inspected egress — that common habit from
rebuilding app images targets the wrong pod.
