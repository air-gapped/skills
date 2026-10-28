---
name: openshell-best-practices
description: >-
  Run NVIDIA OpenShell 0.1.x — the sandboxed runtime for autonomous AI agents (gateway,
  per-sandbox supervisor, Landlock/seccomp/netns isolation, L7 network policy, credential
  placeholders via providers/profiles) — the way current practitioners do. Core knowledge: the
  0.1.0 breaking cutover and which 0.0.x patterns are now wrong (inference.local, built-in
  profiles, --from Dockerfile builds, community base image, config v1); local gateway installs
  (RPM/deb/brew/snap, clean reinstall from 0.0.x); Kubernetes Helm deployment with Agent Sandbox,
  ingress without Gateway API, OIDC/Keycloak, gatewayConfig vs deprecated server.* aliases, HA;
  agent images and session model (detach, exec, device-code logins); providers, binaries real
  paths, policy approval and its limits; air-gap operation (mirrors, telemetry, supervisor CAs,
  RFC 1918 destinations and allowed_ips, 198.18 stand-in DNS, corporate proxy); rarely used
  gateway, policy, profile and sandbox settings; automation; and a gotcha list with issues.
when_to_use: >-
  Use whenever the user mentions OpenShell, `openshell` CLI commands (sandbox create/connect/exec,
  gateway add/login, provider/profile, policy, rule approve, term), `openshell-gateway`,
  gateway.toml, the OpenShell Helm chart (`oci://ghcr.io/nvidia/openshell/helm-chart`,
  `openshell-workspace`), Agent Sandbox (`agents.x-k8s.io`, `sandbox.yaml`) as OpenShell's
  prerequisite, or running Claude Code / Codex / OpenCode / Pi / herdr inside OpenShell
  sandboxes. Also trigger on symptoms: sandbox stuck ConfigurationInvalid or
  ProvisioningTimedOut, `NET:OPEN ... DENIED`, `credential_endpoint_mismatch`, `invalid token:
  ExpiredSignature` in the TUI, gateway refusing to start after 0.1.6, Docker Desktop supervisor
  never ready, Landlock/seccomp probe failures, OAuth callback to 127.0.0.1 failing inside a
  sandbox, a connection "allowed" then rejected (`resolves to internal address`, `internal IP
  without allowed_ips`, `ssrf`), `Could not resolve host` or `198.18.x.x` addresses inside a
  sandbox, `request_authority_mismatch`, an internal LiteLLM/mirror/Git server unreachable
  despite a rebuilt CA, and on planning questions ("should we run agents in OpenShell",
  "upgrade OpenShell", "air-gapped OpenShell", "OpenShell with Keycloak", "what does setting X
  do"). Prefer upstream's `openshell-cli` /
  `debug-openshell-cluster` / `generate-sandbox-policy` skills for exhaustive flag references and
  policy generation; this skill is the decisions, deployment patterns and current gotchas. Do
  NOT trigger for NemoClaw-only questions (it pins OpenShell 0.0.116), unrelated "OpenShift",
  or generic container sandboxes (E2B, Daytona, Docker sandboxes) with no OpenShell context.
---

# OpenShell best practices (0.1.x)

Snapshot: OpenShell **0.1.6** (2026-10-27), researched 2026-10-28 from the v0.1.6 tag, release
notes, GitHub issues filed since 0.1.0, and practitioner write-ups. OpenShell releases about
weekly and breaks things between minors — **check the installed and latest versions before
advising** (`openshell --version`, `gh release list --repo NVIDIA/OpenShell`) and read every
release note in between. When this skill and the code at the user's tag disagree, the code wins.

## Mental model

| Piece | Role |
|---|---|
| **Gateway** | Control plane (gRPC on one HTTPS port). Creates sandboxes through a compute driver (Docker, Podman, Kubernetes, VM), stores sandboxes, policies, profiles and provider secrets, authenticates users (OIDC / mTLS). The CLI and TUI are thin clients; `openshell gateway select` switches between gateways |
| **Supervisor** | One per sandbox (or a shared pool on Kubernetes). Owns the network boundary: every agent connection goes through it, it evaluates policy, terminates TLS with a per-sandbox CA, injects real credentials only at approved endpoints, and opens the upstream connection itself |
| **Sandbox** | The workload (your agent image) under Landlock + seccomp + network namespace. `/sandbox` is persistent `$HOME`; default network policy is deny-all |
| **Profile → provider → attachment** | Profile = provider type (endpoints, env vars, allowed binaries); provider = profile + real secret, stored in the gateway; attaching gives the sandbox a placeholder, never the secret |

OpenShell is **governance on a shared kernel**: it controls egress, credentials and audit very
precisely, but it contains rather than detects prompt injection, and it isn't a VM boundary.
Layer Kata/VM runtimes when kernel isolation matters.

## The 0.1.0 cutover — recognise outdated advice

Material written before 2026-09-25 (and some copied after) describes 0.0.x. These are now
wrong: `inference.local` / `openshell inference set`; built-in provider profiles and aliases
`claude`/`gh`; `--from base` or `--from ./Dockerfile`; `sandbox create -- claude` expecting a
preinstalled agent; `ghcr.io/nvidia/openshell-community/*` images (archived 2026-10-07, broken
on 0.1.x); gateway.toml `version = 1` / `compute_drivers`; `tls: terminate`; `openshell gateway
start`. NemoClaw still pins OpenShell 0.0.116, so its docs describe the old model. Full mapping
in `references/versions.md`.

## Best practices

1. **Pin versions and read every hop.** CLI, gateway, supervisor and sandbox runtime should be
   the same release (0.1.6 requires supervisor/runtime pairing). Security fixes ship as plain
   "bug fixes" and the GHSA page is empty — read release notes and NVIDIA product-security
   bulletins. Upgrade off 0.0.x only by clean reinstall.
2. **Build your own agent images**: glibc base, non-root `USER`, `WORKDIR /sandbox`, agents and
   their runtime downloads (ripgrep, MCP servers, toolchains) baked in, agent config baked in.
   Pass the start command after `--`.
3. **Make the agent the sandbox's main program** so detach (Ctrl-D, Ctrl-P Ctrl-Q) and
   reattach (`sandbox connect`) work; separate `exec` shells can't detach.
4. **Keep secrets in providers.** Copy profiles from upstream `providers/` at your tag, set
   `binaries` to the agents' **real** paths, lint, import, then `provider create --credential ENV`.
   Logins done inside an agent leave tokens on the sandbox disk.
5. **Keep proposal approval `manual`** and never let an agent approve its own rules; set
   `enforcement: enforce` explicitly (L7 rules default to `audit`, which forwards traffic).
6. **Treat every allowed write channel as an exfiltration path** — including the model endpoint.
   Don't put untrusted input, private data and egress in the same sandbox.
7. **Turn telemetry off** (on by default) for anything private or air-gapped.
8. **Use OIDC for any shared gateway**; public CLI client with PKCE and a loopback redirect,
   a separate confidential client for unattended jobs, roles mapped to admin/user.
9. **On Kubernetes**: install a pinned Agent Sandbox first and restart the gateway after
   upgrading it; require a NetworkPolicy-enforcing CNI; write new settings in `gatewayConfig`;
   set the data StorageClass at install (immutable).
10. **Private CA for agent egress is the supervisor's to trust**, never the agent image's. On
    0.1.6: `upstreamProxy.caBundle` with an unused proxy URL and `noProxy: "*"` (no rebuild,
    verified), or a rebuilt supervisor image.
11. **Give every internal endpoint `allowed_ips` and an FQDN.** Private destinations (RFC 1918,
    CGNAT, VIPs) are rejected for approved proposals, wildcards and unlisted binaries even when
    the policy "allows" them, and sandboxes resolve no short names. This, not the CA, is the
    usual reason an air-gapped install can't reach its mirrors or model endpoint.

## Where to read next

| Task | Reference |
|---|---|
| Versions, upgrade notes, CVE history, outdated-pattern table | `references/versions.md` |
| Workstation install, 0.0.x → 0.1.x clean reinstall, Docker Desktop/WSL2/Podman problems | `references/local-gateway.md` |
| Kubernetes/OpenShift deployment, Agent Sandbox, Helm values, ingress, HA, known K8s issues | `references/kubernetes-gateway.md` |
| OIDC/Keycloak client, interactive vs unattended login, token lifetimes, TUI expiry, mTLS | `references/auth.md` |
| Profiles, providers, binaries, Claude Code/Codex/OpenCode/local-model credentials, policy loop, limits | `references/providers-and-policy.md` |
| Agent images, session model, device-code logins, multi-agent layouts (herdr/tmux), broken tools | `references/sandboxes-and-agents.md` |
| Air-gapped sites: mirror list, telemetry, internal destinations and `allowed_ips`, sandbox DNS, private CAs per component, corporate proxy, agents against mirrors, bring-up order | `references/air-gap-and-ca.md` |
| Rarely used settings: gateway/driver knobs, supervisor topology, every policy endpoint field, plain HTTP, filesystem/lifecycle fields, profile fields, `sandbox create` flags | `references/rare-settings.md` |
| Headless agents, CI, SDKs, fleets, Claude self-hosted sandboxes, middleware/interceptors | `references/automation.md` |
| Denials, stuck sandboxes, auth errors, where logs live | `references/troubleshooting.md` |

## Working method

- Verify against the source at the user's tag: a local clone of `NVIDIA/OpenShell`
  (`git show <tag>:docs/...`) or `gh` — docs on `main` run ahead of releases, and in-repo
  examples lag (some still assume built-in profiles).
- Before claiming a bug is fixed or open, check the issue and the release notes; open fixes
  often wait as unmerged PRs (external PRs are auto-closed until the author is vouched for).
- Name commands with the exact 0.1.x shape (`--rule-name` and `--binary` on `policy update`,
  `-g <gateway>` in scripts, `--workspace` in SDK calls). There is no `openshell policy validate`;
  the offline checker is `openshell-prover check`.
- Upstream skills for depth: `npx skills add NVIDIA/OpenShell` installs `openshell-cli`,
  `debug-openshell-cluster`, `generate-sandbox-policy`, `debug-inference`.
