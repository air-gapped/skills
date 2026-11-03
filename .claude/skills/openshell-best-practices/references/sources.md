# Sources — openshell-best-practices

Freshened: 2026-11-03

Authoritative external references the skill points at. The `Freshened:` stamp means every row below was verified on that date; a row that could not be verified says so inline. History: authored 2026-10-28 against OpenShell 0.1.6 and Agent Sandbox v1.0.8; freshened 2026-11-03 against 0.1.7 (tag diff v0.1.6..v0.1.7, release notes, issue states, live checks on a 0.1.7 Kubernetes gateway).

## Upstream (NVIDIA/OpenShell)

| URL | Purpose | Pinned |
|-----|---------|--------|
| https://github.com/NVIDIA/OpenShell/releases | Release list and per-version upgrade notes (0.1.0–0.1.7; v0.1.7 latest on 2026-11-03) | — |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/upgrade/0-1-0.mdx | 0.0.x → 0.1.0 breaking changes | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/kubernetes/setup.mdx | Helm install, Agent Sandbox, values table (0.1.7: `server.serviceHostnameFormat`, larger namespaced Role) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/kubernetes/migrate-gateway-config.mdx | gatewayConfig schema v2, deprecated `server.*` aliases | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/kubernetes/access-control.mdx | OIDC, RBAC mode, trusted proxy | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/kubernetes/high-availability.mdx | PostgreSQL, replicas, connection sizing, shared supervisor (still experimental); 0.1.7 adds "Activate Sandbox Updates" | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/gateways/authentication.mdx | CLI login flows, token refresh, client credentials; 0.1.7 adds "Browser Login Callbacks" | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/policies/network-rules.mdx | Binary matching, MCP rules | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/policies/advisor.mdx | Proposals, approval modes, policy.local | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/sandboxes/overview.mdx | Session model, detach, exec, upload, suspend; 0.1.7 adds "Update the Image of a Stopped Sandbox" and stop on Completed/Error | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/about/installation.mdx | install.sh, packages, uninstall | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/observability/telemetry.mdx | Telemetry default and opt-out | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/tree/v0.1.7/providers | Example provider profiles | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/tree/v0.1.7/scripts/agents | Gator manifest-driven agent harness (0.1.7: Kubernetes gateways via image push, sandbox-scoped settings) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/policies/schema.mdx | Every policy and endpoint field, defaults | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/policies/manage-policies.mdx | Live vs startup sections, 300 s admission window, error codes | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/providers/profiles.mdx | Profile schema, token grants, refresh strategies | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/how-it-works/gateways/configuration.mdx | gateway.toml reference, upstream proxy, driver keys; 0.1.7 adds Additional Destination CAs, Sandbox Updates, Service Routing, OTLP transport/TLS, agent trace relay, supervisor app listener | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/security/best-practices.mdx | Private-IP defaults, `allowed_ips`, hostAliases | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/crates/openshell-core/src/net.rs | Internal / always-blocked address ranges | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/crates/openshell-supervisor-network/src/proxy/destination.rs | Address authorization modes (exact host, `allowed_ips`, default public-only) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/deploy/helm/openshell/values.yaml | Chart values (still no `values.schema.json` in 0.1.7; adds `supervisor.network.additionalCaConfigMapName`, `server.serviceHostnameFormat`; `server.ocsfLog.schemaVersion` ignored) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/3292 | Additional destination CAs: merged 2026-10-27T18:45Z, after the v0.1.6 tag, first released in 0.1.7. Lifecycle (startup-only read, restart + stop/start), Helm key `ca.crt`, RBAC: v0.1.7 `docs/how-it-works/gateways/configuration.mdx` "Additional Destination CAs" | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.7/docs/kubernetes/ingress.mdx | "Route Sandbox Service Traffic", hashed hostnames for multiple gateways (#4842) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5065 | `OPENSHELL_CALLBACK_PORT` / `OPENSHELL_CALLBACK_BIND_ADDRESS` for CLI browser login from a container; v0.1.7 `docs/how-it-works/gateways/authentication.mdx` "Browser Login Callbacks" | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5036 | OCSF native 1.8.0 only; schema-version downgrade settings deprecated and ignored (v0.1.7 breaking upgrade note; `docs/observability/ocsf-json-export.mdx` drops the downgrade section) | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/4873 | Stopped-sandbox image/command/env updates (from issue #4623), `enable_sandbox_updates`; v0.1.7 `docs/how-it-works/sandboxes/overview.mdx` "Update the Image of a Stopped Sandbox", `docs/kubernetes/high-availability.mdx` "Activate Sandbox Updates", `crates/openshell-driver-kubernetes/README.md` (pods must be gone). Verified live on a 0.1.7 gateway 2026-11-03: protoc-encoded request over curl, `grpc-status: 0`, image swapped, PVC data intact; `grpc.reflection.v1` lists `openshell.v1.SandboxUpdates` | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5155 | Podman `[openshell.drivers.podman] additional_ca_bundle` kept as a deprecated alias of `[openshell.supervisor.network]` | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/issues/4218 | Enterprise deployment blockers tracker | — |
| https://github.com/NVIDIA/OpenShell-Community | Archived 2026-10-07 (community images) | — |
| https://raw.githubusercontent.com/NVIDIA/product-security/main/2026/5872/5872.md | Aug 2026 CVE bulletin (0.0.x); still the only bulletin naming OpenShell (CVE index checked 2026-11-03) | — |

## Issues the gotchas cite (state at 2026-11-03)

| URL | Topic | Pinned |
|-----|---------|--------|
| https://github.com/NVIDIA/OpenShell/issues/3880 | Docker Desktop supervisor never Ready (open, stale-labelled; PR #3924 unmerged) | — |
| https://github.com/NVIDIA/OpenShell/issues/4467 | Community base image `tls: terminate` (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/4834 | K8s symlink binaries matched literally: closed 2026-10-22 as won't fix (maintainer: add a symlink in the images) | — |
| https://github.com/NVIDIA/OpenShell/issues/4287 | CLI client-credentials expiry (open; PR #4389 still unmerged) | — |
| https://github.com/NVIDIA/OpenShell/issues/4910 | Gateway restart → sandboxes Error (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/4290 | readOnlyRootFilesystem admission (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/3415 | Supervisor BestEffort QoS: stale-bot closed NOT_PLANNED 2026-10-30, no fix or PR — still BestEffort at 0.1.7 | — |
| https://github.com/NVIDIA/OpenShell/issues/4102 | Make setresuid denial (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/4098 | Chromium sandbox (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/4949 | Access after main program exits (open) | — |
| https://github.com/NVIDIA/OpenShell/issues/4515 | Go SDK caches edge token (TUI analogue) | — |
| https://github.com/NVIDIA/OpenShell/issues/4662 | `allowed_ips` must agree across overlapping endpoints (open; retitled "Hostless web egress conflicts with a pinned provider endpoint", rejection confirmed intentional; PR #5088 unmerged) | — |
| https://github.com/NVIDIA/OpenShell/issues/3672 | OIDC CA scoped to the OIDC client: stale-bot closed NOT_PLANNED 2026-10-28, no fix; PR #3673 still open on 2026-11-03, and the v0.1.7 chart still sets process-wide `SSL_CERT_FILE` | — |
| https://github.com/NVIDIA/OpenShell/issues/4295 | `--no-keep` discards audit logs (open) | — |

## Kubernetes prerequisite

| URL | Purpose | Pinned |
|-----|---------|--------|
| https://github.com/kubernetes-sigs/agent-sandbox/releases | Agent Sandbox releases (v1.0.9 latest, 2026-10-29) | — |

## Field reports and ecosystem

| URL | Purpose | Pinned |
|-----|---------|--------|
| https://news.ycombinator.com/item?id=50198675 | HN launch thread: critiques (exfiltration, telemetry, shared kernel) | — |
| https://www.ssdnodes.com/learn/nvidia-openshell-sandbox-agents-on-a-vps | Practitioner walkthrough on 0.1.2 (2026-10-16) | — |
| https://github.com/QuietFlare/openshell-claude | Claude Code image + policy on 0.1.2 | — |
| https://github.com/jlaska/agent-sandbox/pull/42 | Agent images for 0.1.4 (real binary paths, non-root) | — |
| https://github.com/nirmata/demo-openshell-prompt-injection | Prompt-injection containment demo on 0.1.2 | — |
| https://www.redhat.com/en/blog/bringing-claude-self-hosted-sandboxes-to-openshell-on-red-hat-ai | Claude Managed Agents worker in OpenShell sandboxes (bare curl works; fetch tools get 404) | — |
| https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes | Anthropic self-hosted environment worker model | — |
| https://github.com/NVIDIA/NemoClaw | Pins OpenShell 0.0.116 (blueprint.yaml min and max) through tag v0.0.140 (2026-10-29) | — |
| https://infrazen.io/blog/ai-agent-sandboxes-compared-2026 | Comparison vs E2B/Daytona/Modal/Kata (2026-10-25) | — |
