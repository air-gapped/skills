# Air-gapped sites and private CAs (0.1.x)

Verified against `v0.1.6` (source and docs). The internal-destination behaviour was also
measured on a live 0.1.6 Kubernetes gateway on 2026-10-28. Two fixes landed on main after
0.1.6: #3292 (additional destination CAs as a ConfigMap) and #3672 (OIDC CA scoped to the
OIDC client).

## Contents

- What reaches the internet
- Images to mirror
- Internal destinations: the usual blocker
- DNS inside sandboxes
- Private CA: which component needs it
- Corporate forward proxy
- Agents and package managers against mirrors
- Bring-up order

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
| `ghcr.io/nvidia/openshell/gateway:<ver>` | `global.image.*` (also used by the certgen hook) |
| `ghcr.io/nvidia/openshell/supervisor:<ver>` | `global.image.*` |
| `ghcr.io/nvidia/openshell/sandbox:<ver>` | `global.image.*`. Rendered into `gateway.toml` as soon as `global.image.registry` or `.tag` is set; with stock values the gateway binary's built-in default applies |
| `nvcr.io/nvidia/base/ubuntu:24.04` | `sandbox.image.*`: the default workload image, a full reference **not** prefixed by `global.image.registry`. Empty tag → `latest`; null pull policy → Kubernetes default (`Always` for `:latest`), also for the `workspace-init` init container |
| `registry.k8s.io/agent-sandbox/agent-sandbox-controller:<ver>` | Edit in the Agent Sandbox manifest |
| Your agent images | Per `sandbox create --from` (the old `openshell-community` images are archived and break on 0.1.x — see `sandboxes-and-agents.md`) |

- Keep the `openshell/...` repository path under the mirror prefix. `global.image.pullPolicy`
  also sets the supervisor and sandbox runtime pull policies.
- Pull secrets. `server.sandboxImagePullSecrets` goes on the workload pod **and** the
  per-sandbox supervisor pod. The Secret must exist in the sandbox namespace; managed
  workspace mode copies it there. `imagePullSecrets` (release namespace) covers the gateway,
  the certgen hooks and the shared supervisor.
- Every pod start of a `:latest` image pulls from the mirror again. Slow mirrors or large
  agent images: raise `[openshell.gateway] image_preparation_timeout_seconds` (default 1800).
- Upstream `docs/kubernetes/setup.mdx` names `server.sandboxImage`; that key does nothing. The
  key is `sandbox.image.*`.

## Internal destinations: the usual blocker

At an air-gapped site every mirror, model endpoint and Git server sits on a private address,
often a load-balancer VIP. Mirrors that keep the public hostnames (`registry.npmjs.org`,
`pypi.org`) resolve to private addresses too. The supervisor treats these as **internal**:
RFC 1918, CGNAT `100.64.0.0/10`, `198.18.0.0/15`, the TEST-NETs, `192.0.0.0/24`, broadcast and
IPv6 ULA (`crates/openshell-core/src/net.rs`, `is_internal_ip`). Whether a connection to one
gets through depends on how the endpoint is written, not on the CA:

| Endpoint | Internal address |
|---|---|
| Exact `host` + port in a hand-written policy rule or provider profile whose `binaries` include the caller (children inherit) | Allowed without `allowed_ips` |
| Any endpoint with `allowed_ips` covering **every** address the name resolves to | Allowed |
| Rule approved from a pending proposal | **Blocked**, even when a provider lists the same host for another binary (`docs/how-it-works/policies/advisor.mdx`). The marker (`advisor_proposed`) never shows in `policy get` |
| Wildcard host (`*.corp.example`) or hostless endpoint without `allowed_ips` | **Blocked** |
| Loopback, link-local (incl. `169.254.169.254`), unspecified | Always blocked; `allowed_ips` cannot open them |
| Ports 2379, 2380, 6443, 10250, 10255 on any path that can reach internal addresses | Always refused (`BLOCKED_CONTROL_PLANE_PORTS`): `kubectl` in a sandbox needs the API behind a 443 front end (Rancher proxy, ingress) |

What the operator sees (each one sends people to the CA first):

- The log shows the policy **allowing** the binary and host, then an immediate denial with
  `firewall_rule` `ssrf`: `<host> resolves to internal address <ip>, connection rejected`
  (CONNECT) or `FORWARD blocked: internal IP without allowed_ips for <host>:<port>` (plain
  HTTP). Find it: `openshell logs <sb> --since 10m | grep -E 'ssrf|internal|allowed_ips'`.
- Inside the sandbox every name resolves to a **stand-in `198.18.x.x`** (see DNS below), never
  the real VIP — including names no rule allows, so that the connection can become a pending
  rule. A `198.18` answer does not mean a rule matched.
- A wildcard endpoint without `allowed_ips` whose name resolves internal gets **no DNS answer
  at all** (`curl: (6) Could not resolve host`).
- The site CA never appears inside the sandbox, working or not: the workload always sees a
  leaf certificate from the per-sandbox OpenShell CA. Adding the CA to more images is wasted
  effort; only the supervisor's trust matters (next sections).

**Practice: put `allowed_ips` on every internal endpoint**, in profiles and policies, as tight
as the address plan allows (`/32` per VIP, or the VIP range):

```yaml
endpoints:
  - host: litellm.ai.example.internal   # FQDN: no DNS search domains in sandboxes
    port: 443
    protocol: rest
    access: read-write
    enforcement: enforce
    allowed_ips: ["10.20.30.40/32"]
```

- All endpoints that can match one host:port — wildcards and hostless rules included — must
  carry the **same** `allowed_ips` list, or the policy update is refused (#4662).
- To rescue an approved proposal, add `allowed_ips`, or turn it into a hand-written rule:
  `openshell policy update <sb> --rule-name <key> --binary <every binary of that rule>
  --add-endpoint host:443:read-write:rest:enforce:allowed-ip=10.20.30.40/32 --wait`.
- **Typos pass silently**: profile parsing drops unknown keys, and `profile lint` passed a
  misspelled `allowd_ips` (checked 2026-10-28). Grep imported profiles for the exact key.

## DNS inside sandboxes

- The workload pod has `dnsPolicy: None`, nameserver `127.0.0.53` and **zero egress**; the
  supervisor answers its queries (policy DNS) with stand-in addresses from `198.18.0.0/15`,
  TTL ≤ 30 s, and maps connections back to the real destination.
- The supervisor resolves real names with the **first literal `nameserver`** of its own
  `/etc/resolv.conf` (cluster DNS on Kubernetes). Split-horizon behaviour is whatever that
  server answers; point it at the site resolver.
- **No search domains, no `/etc/hosts`.** `litellm` or `litellm.ai` fail; use the FQDN
  (`litellm.ai.svc.cluster.local`) in the rule *and* the client config. Kubernetes
  `hostAliases` count only for endpoints with `allowed_ips` (`docs/security/best-practices.mdx`).
- AAAA queries get an empty answer: IPv6-only services are unreachable by name.
- Clients that cache an address forever fail when the stand-in expires.
- The chart hard-codes `.svc.cluster.local` (default `grpc_endpoint`, gateway certificate SAN,
  peer TLS name). Clusters with another cluster domain: set `server.grpcEndpoint` to
  `https://<release>.<ns>.svc:8080`, a name already in the SAN (from the templates, untested).

## Private CA: which component needs it

Agent traffic is intercepted: the workload talks to the supervisor, which terminates TLS with
a per-sandbox CA and opens the real upstream connection itself. So the trust decision for an
internal HTTPS service is made by the **supervisor**, not the agent image.

| Path | 0.1.6 mechanism |
|---|---|
| Gateway → OIDC issuer | `server.oidc.caConfigMapName` (key `ca.crt`) → `SSL_CERT_FILE`. **Replaces** the system roots for the whole gateway process — include every root it needs (scoped to OIDC only after 0.1.6, #3672) |
| Gateway → Vault | `credentialDrivers.vault.caConfigMapName` (top level; `server.credentialDrivers.vault.*` is the legacy fallback) |
| CLI → gateway | CLI pins `~/.config/openshell/gateways/<name>/mtls/ca.crt` if present, else the OS trust store |
| Supervisor → internal HTTPS upstream (Kubernetes) | No dedicated setting in 0.1.6. Rebuild the supervisor image (below). It reads only the **first non-empty** of `/etc/ssl/certs/ca-certificates.crt`, `/etc/pki/tls/certs/ca-bundle.crt`, `/etc/ssl/ca-bundle.pem`, `/etc/ssl/cert.pem`, plus bundled Mozilla roots — a CA in a later file is ignored. Main (#3292) adds `supervisor.network.additionalCaConfigMapName` |
| Supervisor → intercepting corporate proxy | `upstreamProxy.caBundle.configMapName` (release namespace, ≤ 256 KiB). This CA is trusted for **all** upstreams, proxied or not, and lands in the sandbox bundle too. Supply only the proxy/interception CA: a full merged bundle (e.g. OpenShift's injected trusted bundle) can exceed the sandbox boundary's control-frame budget. Per-sandbox supervisors only |
| Supervisor → upstream (Podman) | `additional_ca_bundle` (0.1.5) |
| Agent → supervisor | Automatic: the CA lands in `/run/openshell-supervisor-ca/material/` — `ca-bundle.crt` (system roots + sandbox CA) for `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO`; `ca.crt` for `NODE_EXTRA_CA_CERTS`, `DENO_CERT`. Tools that ignore these (Java keystores) need the CA imported |

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

Point the supervisor image at it (same registry path and tag as the sandbox runtime) and
recreate sandboxes; running ones keep their supervisor until they stop. Untested alternative
that avoids the rebuild: because the proxy CA is trusted for every upstream,
`upstreamProxy.url` set to any syntactically valid proxy plus `noProxy: "*"` plus
`caBundle` should inject a site CA with per-sandbox supervisors.

## Corporate forward proxy

`upstreamProxy.*` (deprecated alias; the `gatewayConfig."openshell.drivers.kubernetes"` keys
are `https_proxy`, `no_proxy`, `proxy_auth_secret_{name,key}`, `proxy_auth_allow_insecure`,
`proxy_connect_by_hostname`, `proxy_ca_bundle`):

- Only TLS (CONNECT) egress is chained through the proxy; **plain HTTP always dials directly**.
- `http://` and `https://` proxies are supported (scheme and port required); credentials in
  the URL are rejected — use the auth Secret, which must live in the **sandbox** namespace and
  is not copied in managed workspace mode. `docs/kubernetes/setup.mdx` still calls https
  proxies and CA bundles unsupported; the code supports both.
- `no_proxy` takes hosts, domain suffixes, IPs, CIDRs, `:port` qualifiers and `*`; IP/CIDR
  entries also match resolved addresses. Internal mirrors belong here.
- The supervisor still resolves every destination itself and runs the internal-address check
  **before** proxying, so public names must resolve in the supervisor's DNS. The CONNECT
  target is the validated IP; `proxy_connect_by_hostname = true` sends the name instead, which
  hands egress control to the proxy's ACLs.
- The shared supervisor (`supervisor_topology = "gateway"`) refuses all proxy settings.
- Sandbox processes cannot use a proxy of their own: the supervisor strips `HTTP(S)_PROXY`,
  `ALL_PROXY`, `NO_PROXY`, `grpc_proxy` and `NODE_USE_ENV_PROXY` from every child, including
  values from `--env` and providers.

## Agents and package managers against mirrors

- Bake mirror settings into the agent image (npm `registry`, pip/uv index URL, `GOPROXY` and
  `GOSUMDB`, cargo source replacement, container registries) — nothing inside the sandbox can
  fetch them at runtime, and proxy variables are stripped.
- Mirrors that keep public hostnames: upstream `providers/*.yaml` keep working for exact hosts
  as long as `binaries` match the image; add `allowed_ips` anyway and to every wildcard entry.
  Mirrors on their own hostnames: write those FQDNs into the profile. A provider whose
  `*_BASE_URL` names a host its profile doesn't list becomes endpointless (rule dropped,
  credentials withheld).
- Model endpoint (LiteLLM, vLLM): a custom profile for its FQDN with `allowed_ips`, binaries =
  the agent's real path. Claude Code: `ANTHROPIC_BASE_URL`, key via the provider placeholder,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_AUTOUPDATER=1`. OpenCode: a custom
  provider `baseURL` in `opencode.json`, `OPENCODE_DISABLE_MODELS_FETCH=1`,
  `OPENCODE_DISABLE_AUTOUPDATE=1`.
- Plain-HTTP endpoints (`http://…:4000`) work with `protocol: rest`, but a provider key then
  crosses the network in cleartext (no scheme check), and the `Host` header must include the
  port or the request fails with `request_authority_mismatch`. h2c is refused.
- Git over HTTPS to an internal forge: a credential helper that prints the provider's
  placeholder as the password; the proxy resolves placeholders inside Basic auth too. SSH
  (port 22) needs a hand-written `protocol: tcp` rule and carries no credential injection.

## Bring-up order

Each step is done when its check passes; later failures are then attributable.

1. Images and chart mirrored, telemetry off, offline render passes (`kubernetes-gateway.md`).
2. Gateway up with OIDC behind the site CA: `openshell status` shows `Authenticated`.
3. Supervisor image with the site CA set; a throwaway sandbox whose policy allows `curl` to
   one internal HTTPS host by FQDN with `allowed_ips` returns HTTP 200.
4. Profiles: FQDN hosts, `allowed_ips` on every internal endpoint, `binaries` checked with
   `readlink -f` in the image, keys grepped for typos; imported and linted.
5. One throwaway sandbox per provider: `getent hosts <fqdn>` gives a `198.18.x.x` address,
   the tool's request succeeds, and `openshell logs` shows no `ssrf` denial.
