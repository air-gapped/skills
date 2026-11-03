# Sources — openshell-best-practices

Freshened: 2026-10-28 — initial research pass. OpenShell 0.1.6 (2026-10-27) is latest; Agent Sandbox v1.0.8 (2026-10-22).

Authoritative external references the skill points at. `freshen` mode probes these and stamps `Last verified:` per row. Mark a row with `<!-- ignore-freshen -->` if the URL is intentionally pinned to a historical state.

## Upstream (NVIDIA/OpenShell)

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://github.com/NVIDIA/OpenShell/releases | Release list and per-version upgrade notes (0.1.0–0.1.6) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/upgrade/0-1-0.mdx | 0.0.x → 0.1.0 breaking changes | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/kubernetes/setup.mdx | Helm install, Agent Sandbox, values table | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/kubernetes/migrate-gateway-config.mdx | gatewayConfig schema v2, deprecated `server.*` aliases | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/kubernetes/access-control.mdx | OIDC, RBAC mode, trusted proxy | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/kubernetes/high-availability.mdx | PostgreSQL, replicas, connection sizing, shared supervisor | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/gateways/authentication.mdx | CLI login flows, token refresh, client credentials | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/policies/network-rules.mdx | Binary matching, MCP rules | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/policies/advisor.mdx | Proposals, approval modes, policy.local | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/sandboxes/overview.mdx | Session model, detach, exec, upload, suspend | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/about/installation.mdx | install.sh, packages, uninstall | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/observability/telemetry.mdx | Telemetry default and opt-out | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/tree/v0.1.6/providers | Example provider profiles | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/tree/v0.1.6/scripts/agents | Gator manifest-driven agent harness | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/policies/schema.mdx | Every policy and endpoint field, defaults | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/policies/manage-policies.mdx | Live vs startup sections, 300 s admission window, error codes | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/providers/profiles.mdx | Profile schema, token grants, refresh strategies | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/how-it-works/gateways/configuration.mdx | gateway.toml reference, upstream proxy, driver keys | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/docs/security/best-practices.mdx | Private-IP defaults, `allowed_ips`, hostAliases | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-core/src/net.rs | Internal / always-blocked address ranges | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/crates/openshell-supervisor-network/src/proxy/destination.rs | Address authorization modes (exact host, `allowed_ips`, default public-only) | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/blob/v0.1.6/deploy/helm/openshell/values.yaml | Chart values (no schema in 0.1.6) | 2026-10-28 | v0.1.6 |
| https://github.com/NVIDIA/OpenShell/pull/3292 | Additional destination CAs: merged 2026-10-27T18:45Z, after the v0.1.6 tag, first released in 0.1.7. Lifecycle (startup-only read, restart + stop/start), Helm key `ca.crt`, RBAC: v0.1.7 `docs/how-it-works/gateways/configuration.mdx` "Additional Destination CAs" | 2026-11-03 | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5065 | `OPENSHELL_CALLBACK_PORT` / `OPENSHELL_CALLBACK_BIND_ADDRESS` for CLI browser login from a container; v0.1.7 `docs/how-it-works/gateways/authentication.mdx` "Browser Login Callbacks" | 2026-11-03 | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5036 | OCSF native 1.8.0 only; schema-version downgrade settings deprecated and ignored (v0.1.7 breaking upgrade note; `docs/observability/ocsf-json-export.mdx` drops the downgrade section) | 2026-11-03 | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/4873 | Stopped-sandbox image/command/env updates (from issue #4623), `enable_sandbox_updates`; v0.1.7 `docs/how-it-works/sandboxes/overview.mdx` "Update the Image of a Stopped Sandbox", `docs/kubernetes/high-availability.mdx` "Activate Sandbox Updates", `crates/openshell-driver-kubernetes/README.md` (pods must be gone). Verified live on a 0.1.7 gateway 2026-11-03: protoc-encoded request over curl, `grpc-status: 0`, image swapped, PVC data intact; `grpc.reflection.v1` lists `openshell.v1.SandboxUpdates` | 2026-11-03 | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/pull/5155 | Podman `[openshell.drivers.podman] additional_ca_bundle` kept as a deprecated alias of `[openshell.supervisor.network]` | 2026-11-03 | v0.1.7 |
| https://github.com/NVIDIA/OpenShell/issues/4218 | Enterprise deployment blockers tracker | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell-Community | Archived 2026-10-07 (community images) | 2026-10-28 | — |
| https://raw.githubusercontent.com/NVIDIA/product-security/main/2026/5872/5872.md | Aug 2026 CVE bulletin (0.0.x) | 2026-10-28 | — |

## Issues the gotchas cite (state at 2026-10-28)

| URL | Topic | Last verified | Pinned |
|-----|-------|---------------|--------|
| https://github.com/NVIDIA/OpenShell/issues/3880 | Docker Desktop supervisor never Ready (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4467 | Community base image `tls: terminate` (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4834 | K8s symlink binaries matched literally (won't fix) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4287 | CLI client-credentials expiry (open, PR #4389) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4910 | Gateway restart → sandboxes Error (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4290 | readOnlyRootFilesystem admission (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/3415 | Supervisor BestEffort QoS (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4102 | Make setresuid denial (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4098 | Chromium sandbox (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4949 | Access after main program exits (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4515 | Go SDK caches edge token (TUI analogue) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/4662 | `allowed_ips` must agree across overlapping endpoints (open) | 2026-10-28 | — |
| https://github.com/NVIDIA/OpenShell/issues/3672 | OIDC CA scoped to the OIDC client: stale-bot closed NOT_PLANNED 2026-10-28, no fix; PR #3673 still open on 2026-11-03, and the v0.1.7 chart still sets process-wide `SSL_CERT_FILE` | 2026-11-03 | — |
| https://github.com/NVIDIA/OpenShell/issues/4295 | `--no-keep` discards audit logs (open) | 2026-10-28 | — |

## Kubernetes prerequisite

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://github.com/kubernetes-sigs/agent-sandbox/releases | Agent Sandbox releases (v1.0.8 latest) | 2026-10-28 | — |

## Field reports and ecosystem

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://news.ycombinator.com/item?id=50198675 | HN launch thread: critiques (exfiltration, telemetry, shared kernel) | 2026-10-28 | — |
| https://www.ssdnodes.com/learn/nvidia-openshell-sandbox-agents-on-a-vps | Practitioner walkthrough on 0.1.2 (2026-10-16) | 2026-10-28 | — |
| https://github.com/QuietFlare/openshell-claude | Claude Code image + policy on 0.1.2 | 2026-10-28 | — |
| https://github.com/jlaska/agent-sandbox/pull/42 | Agent images for 0.1.4 (real binary paths, non-root) | 2026-10-28 | — |
| https://github.com/nirmata/demo-openshell-prompt-injection | Prompt-injection containment demo on 0.1.2 | 2026-10-28 | — |
| https://www.redhat.com/en/blog/bringing-claude-self-hosted-sandboxes-to-openshell-on-red-hat-ai | Claude Managed Agents worker in OpenShell sandboxes (bare curl works; fetch tools get 404) | 2026-10-28 | — |
| https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes | Anthropic self-hosted environment worker model | 2026-10-28 | — |
| https://github.com/NVIDIA/NemoClaw | Pins OpenShell 0.0.116 (blueprint.yaml) | 2026-10-28 | — |
| https://infrazen.io/blog/ai-agent-sandboxes-compared-2026 | Comparison vs E2B/Daytona/Modal/Kata (2026-10-25) | 2026-10-28 | — |
