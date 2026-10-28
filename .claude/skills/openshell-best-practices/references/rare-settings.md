# Rarely used settings (0.1.6)

Settings that stay at their defaults until one of them is the reason something fails. Read
from the `v0.1.6` tag: `deploy/helm/openshell/`, `crates/openshell-driver-kubernetes/src/`,
`docs/how-it-works/policies/schema.mdx`, `docs/how-it-works/providers/profiles.mdx`, the CLI.
Air-gap-specific settings (images, CAs, proxy, DNS, `allowed_ips`) are in
`air-gap-and-ca.md`; everyday Helm values in `kubernetes-gateway.md`.

The chart has **no `values.schema.json`** in 0.1.6, and provider profiles drop unknown keys:
a misspelled key in either is silently ignored. Diff the rendered `gateway.toml`
(`helm template … | grep -A40 gateway.toml`) and grep imported profiles after every change.

## Contents

- Gateway and Kubernetes driver
- Supervisor topology and control connection
- Policy endpoint fields
- Plain HTTP to internal services
- Filesystem, process and lifecycle fields
- Provider-profile fields
- `sandbox create` flags

## Gateway and Kubernetes driver

| Setting | Default | Consequence |
|---|---|---|
| `[openshell.gateway] image_preparation_timeout_seconds` | 1800 | Budget for image pull plus first supervisor start (1–86400) |
| `policy_validation_failure_mode` (gateway setting) | `fail_closed` | A bad policy revision blocks all network; `retain_last_valid` keeps the last good one |
| `workspace_default_storage_size` / `workspace_storage_class` (`openshell.drivers.kubernetes`) | 2Gi, cluster default class | RWO PVC per sandbox; new sandboxes only |
| `sandbox_uid` / `sandbox_gid` | OpenShift SCC annotation, else **10001**; GID = UID | Build images for this UID. `configuration.mdx` says 1000; the code says 10001 |
| `allowed_pod_annotations` / `allowed_pod_labels` | `[]` = reject all | Only via `gatewayConfig`; `<domain>/*` wildcards; `openshell.ai`, `agents.x-k8s.io` reserved. Allowed labels can match other NetworkPolicy selectors |
| `sa_token_ttl_secs` (`server.sandboxJwt.k8sSaTokenTtlSecs`) | — | Supervisor token, audience `openshell-gateway`, clamped 600–86400 s. The workload gets no token; the driver refuses projected tokens |
| Chart-owned driver keys | — | `namespace`, `service_account_name`, `host_gateway_ip`, `client_tls_secret_name` are **overwritten** from chart values (`server.sandboxNamespace`, `sandboxServiceAccount.*`, `server.hostGatewayIP`, TLS values) whatever `gatewayConfig` says; `shared_supervisor` / `supervisor_pool` are rejected |
| Per-sandbox supervisor resources | none | BestEffort QoS, no setting. Agent resources come from `--cpu`/`--memory` or driver config |
| Driver NetworkPolicies | always | `openshell-sandbox-workloads` (workload: zero egress incl. DNS, ingress only from supervisors on 5500) and `openshell-sandbox-supervisors` (all egress). `networkPolicy.enabled` toggles only the chart's SSH (2222) and shared-supervisor policies. A CNI that ignores NetworkPolicy removes the workload's containment |
| Hard-coded | — | Kubernetes API timeout 30 s, supervisor grace 30 s, health port 5501, bootstrap grace 5 min, admission repair window 300 s; the agent container's `/run` is a memory-backed emptyDir |
| `pkiInitJob.serverDnsNames` | — | The certgen hook **skips** when all three TLS Secrets exist, so SANs added after install never reach the certificate; deleting only some of the Secrets fails the hook. Delete all three to re-issue. Certificates are effectively non-expiring |
| `credentialDrivers.vault.*` (top level) | — | `server.credentialDrivers.vault.*` is the legacy fallback |
| `OPENSHELL_PEER_TLS_CA_FILE` | set only with pkiInitJob or cert-manager | Multi-replica relay otherwise uses the platform trust store |

## Supervisor topology and control connection

- `supervisor_topology` unset (default) = one supervisor pod per sandbox. `"gateway"` = one
  shared `<release>-supervisor` Deployment; `"workspace"` fails as not implemented. Shared mode
  requires gateway TLS, refuses `https_proxy`, `proxy_auth_*`, `proxy_ca_bundle` and the SPIFFE
  socket, needs `operator_namespace_label` as `key=value` in operator workspace mode, runs as
  UID 65534 with **hard-coded** 50m/64Mi requests and a 1Gi limit, and applies to new
  generations only.
- The control connection is not configurable. New generations are runtime-initiated: the
  workload dials its supervisor's Service on `boundary_port` 5500 (≥ 1024) through a per-pair
  NetworkPolicy. Generations created before 0.1.6 (no `openshell.ai/sandbox-runtime-control-connection`
  annotation) stay supervisor-initiated until replaced.

## Policy endpoint fields

| Field | Default | Use it when | Gotcha |
|---|---|---|---|
| `protocol` | none (L4; TLS still auto-terminated) | `rest`, `websocket`, `graphql`, `mcp`, `json-rpc` for L7 rules; `tcp` for non-HTTP | `tcp` rejects IP-literal and hostless hosts. An undocumented passthrough-only `sql` exists (`enforce` rejected) |
| `tls` | `""` = peek, terminate if TLS | `skip` for server-speaks-first protocols (SMTP, IMAP, MySQL) and clients presenting their own certificate | `terminate` / `passthrough` are gone (0.1.0). `skip` turns off inspection and credential rewrite |
| `port` / `ports` | — | `ports: [80, 443]` for one rule over several ports | Mutually exclusive; `--add-endpoint` takes one port |
| `path` | all paths | Several inspected endpoints on one host:port; most specific wins | Its glob `*` crosses `/`, unlike rule paths |
| `enforcement` | `audit` (every protocol) | Always set `enforce` | Audit still refuses malformed requests, authority mismatches, MCP `invalid_mcp_request` and `Upgrade` to graphql/mcp/json-rpc |
| `access` | none | Presets `read-only`, `read-write`, `full`; exclusive with `rules` | No effect without `protocol`: `host:443:read-only` from the CLI is silently L4-only. On WebSocket `read-only` allows only the upgrade |
| `rules` / `deny_rules` / `query` | — | Method + path allows; denies win from any rule | `*` in query values and MCP tool names does not cross `.`; `deny_rules` need a `protocol` and an allow set |
| `allow_encoded_slash` | false | `%2F` in paths: npm scoped packages, GitLab project paths | Works only on inspected endpoints (`protocol` set); L4 passthrough always rejects `%2F` |
| `websocket_credential_rewrite` | false | Placeholder inside WebSocket frames | `rest`/`websocket` only; ignored with a warning elsewhere |
| `request_body_credential_rewrite` | false | Placeholder inside a JSON/form/text body (≤ 256 KiB) | `rest` only, not with request signing |
| `allow_uninspected_credentials` | false | A credentialed endpoint that is L4-only (no `protocol`) **or** `tls: skip` | Without it the gateway refuses the policy (`FAILED_PRECONDITION`); token-grant profiles refuse `tls: skip` even with it |
| `persisted_queries`, `graphql_max_body_bytes` | `deny`, 65536 | GraphQL clients that send persisted query IDs (`allow_registered` + `graphql_persisted_queries`) | — |
| `mcp.versions`, `strict_tool_names` | `["2025-11-25"]`, true | Older MCP servers | A request without `MCP-Protocol-Version` is treated as 2025-03-26; allow `initialize` and `notifications/initialized` explicitly |
| `allowed_ips` | none | Internal addresses on wildcard, hostless or advisor-approved endpoints (`air-gap-and-ca.md`) | Same list on every endpoint matching that host:port; cannot overlap loopback/link-local |
| top-level `network_middlewares` | `on_error: fail_closed` | Up to 10 request filters (built-in `openshell/regex`) | A matching `fail_closed` middleware also denies uninspectable traffic (tcp, h2c) to that host |

`policy update --add-endpoint` takes `host:port[:access[:protocol[:enforcement[:options]]]]`;
options are `allowed-ip=…`, `allow-uninspected-credentials` and the two rewrite flags.
`--rule-name` is optional there (auto-generated); `--add-allow` / `--add-deny` require
`--rule-name` plus the complete `--binary` list or `--any-binary`.

## Plain HTTP to internal services

`http://litellm.ai.svc.cluster.local:4000` style endpoints work with `protocol: rest`; the
proxy peeks the first bytes and relays HTTP/1. Know these first:

- Credentials are injected over **plaintext** HTTP — there is no scheme check. Front internal
  model endpoints with TLS when a provider key travels to them.
- The request's `Host` header must carry the port (`:4000`), or it fails with
  `request_authority_mismatch`.
- h2c (cleartext HTTP/2) is refused on inspected endpoints.
- The supervisor strips `HTTP(S)_PROXY`, `ALL_PROXY`, `NO_PROXY`, `grpc_proxy` and
  `NODE_USE_ENV_PROXY` from every sandbox process, including values from `--env` and providers
  (`crates/openshell-sandbox/src/process.rs`). Tools cannot be pointed at a site proxy from
  inside; the corporate proxy is a gateway setting (`air-gap-and-ca.md`).

## Filesystem, process and lifecycle fields

| Field | Default | Note |
|---|---|---|
| `filesystem_policy.include_workdir` | true when `filesystem_policy` is **absent**, false when present | A custom `filesystem_policy` loses `/sandbox` unless it sets `include_workdir: true` |
| Baseline paths | added when the policy has ≥ 1 network rule (provider rules count) | `/usr`, `/lib`, `/etc`, `/app`, `/var/log`, `/proc` ro; `/tmp`, `/dev/null` rw. Not `/dev/pts`: terminal multiplexers (tmux, herdr) need it added |
| `landlock.compatibility` | `best_effort` | `hard_requirement` fails startup if Landlock can't be applied; ABI v3 (Linux 6.2) is required either way |
| `process.run_as_user` / `_group` | driver default | Docker and Podman only; Kubernetes uses the driver's identity |
| Live vs startup | network + middlewares live | Filesystem, Landlock and process are startup-only, except within the 300 s admission window before the workload first starts. Each new network revision closes existing connections, including keep-alives and WebSockets |
| Policy precedence | — | Gateway global policy > saved policy (`--policy`, `OPENSHELL_SANDBOX_POLICY`) > image `/etc/openshell/policy.yaml` > built-in default. A global policy also blocks sandbox changes and approvals |
| `policy_validation_failure_mode` (gateway setting) | `fail_closed` | `retain_last_valid` keeps the last good policy instead of blocking all network on a bad revision |
| `proposal_approval_mode` | `manual` | Gateway value overrides `--approval-mode` per sandbox. Even `auto` holds private-IP hosts, wildcards, `allowed_ips`, ports > 49152 and database/cache ports for review |
| `policy update --wait` | — | Exit 1 = rejected, 124 = timed out |

## Provider-profile fields

| Field | Note |
|---|---|
| `auth_style`, `header_name`, `query_param`, `path_template` | Metadata only for static credentials: injection replaces `openshell:resolve:env:` placeholders wherever they appear (headers incl. Basic auth, request line, query). Only token-grant header placement reads `auth_style`. Lint still requires them |
| `token_grant` | `client_credentials` or `token_exchange` with a SPIFFE JWT-SVID; `token_endpoint` must be https except loopback or `*.svc(.cluster.local)` |
| `refresh.strategy` | `static` (default), `oauth2_refresh_token`, `oauth2_client_credentials`, `google_service_account_jwt`, `aws_sts_assume_role` |
| `stable_placeholder` | Keep one placeholder across value updates (external rotators) |
| `discovery.credentials` | What `provider create --from-existing` reads; nothing else (never `*_BASE_URL`) |
| `files[]` | Undocumented, experimental: renders `{{config.KEY}}` into `/run/openshell/providers/<p>/` |
| `category`, `inference_capable` | Informational |
| Endpoints | Same fields as policy endpoints, no per-credential binding: every credential binds to every endpoint; emitted as one `_provider_<name>` rule. **Unknown keys are dropped silently** |
| `*_BASE_URL` naming a foreign host | The provider becomes endpointless: rule dropped, credentials withheld |

## `sandbox create` flags

| Flag | Note |
|---|---|
| `--restart-policy never\|on-failure\|always` | Default `never`; backoff 1 s → 3 min. With `never`, a main program that exits leaves the sandbox not ready for `connect`/`exec` |
| `--approval-mode` | Per-sandbox proposal approval mode |
| `--no-keep` | Deletes on exit; conflicts with `--editor`, `--forward`, `--expose`, `-o`; discards audit logs (#4295). On Kubernetes it has left `Sandbox` objects behind, which the controller keeps re-creating pods for: check `kubectl get sandboxes.agents.x-k8s.io` and delete ones the gateway no longer lists |
| `--upload` | Conflicts with a trailing command; run the agent with `exec` afterwards |
| `--cpu` / `--memory` / `--gpu [N]` | Kubernetes sets request = limit |
| `--driver-config-json` | Per-sandbox `runtimeClassName` / `nodeSelector`; needs gateway `allow_driver_config` and admission labels |
| `--template` | Conflicts with `--from`, `--env`, `--cpu`, `--memory`, `--gpu` |
| `--label` / `--annotation` | Sandbox metadata, not pod labels |
| `--env-from <file>` | Keeps values out of argv; 128 vars, 8 KiB each, 256 KiB total |
| `sandbox download` | Only paths under the working directory; `/tmp` is refused |
| `forward service` | gRPC-tunnelled forward to a loopback port inside the sandbox |
