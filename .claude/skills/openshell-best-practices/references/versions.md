# Versions, upgrade notes and outdated patterns

Snapshot 2026-10-28. OpenShell ships roughly weekly; re-list releases before acting
(`gh release list --repo NVIDIA/OpenShell`) and read every note between installed and target.
From 0.1.5 on, upgrade notes live in the release notes, not in `docs/upgrade/` (#4398).

## Contents

- Release timeline
- Security history and support policy
- Outdated patterns (0.0.x) still in circulation
- Ecosystem version lag

## Release timeline

| Version | Date | What matters when upgrading |
|---|---|---|
| 0.0.x | –2026-08-28 (last 0.0.116) | Old model: managed inference routes, built-in profiles, config v1. Not upgradable in place |
| **0.1.0** | 2026-09-25 | Breaking cutover (`docs/upgrade/0-1-0.mdx`): recreate every sandbox; config schema v2; no built-in profiles (export/import); `--from` no longer builds Dockerfiles or expands aliases; default image `nvcr.io/nvidia/base/ubuntu:24.04` with no agents; trailing command no longer infers a provider; `inference.local` removed; unknown policy fields rejected; `tls: terminate/passthrough` removed; images without `USER` run as 1000:1000; chart split (gateway + workspace); sandbox templates; workspace selection explicit in APIs |
| 0.1.1 / 0.1.2 | 09-26 / 09-28 | Homebrew `post_install` gateway.toml crash fixed (0.1.2) |
| 0.1.3 | 10-09 | Ctrl-D detach; `sandbox upload` fails closed when Git filtering fails (`--no-git-ignore`); exec streams stdin without waiting for EOF; L7 hardening (HTTP framing, refuse upgrades on JSON-RPC/MCP); prover fails closed; install without cluster-admin; OCSF also to stderr |
| 0.1.4 | 10-13 | Stable credential placeholders; stale bootstrap image after gateway upgrade fixed (#4376); SSH connection sharing disabled; operator-only credential retrieval (mTLS `OU=operator`); provider labels |
| **0.1.5** | 10-20 | OCSF files `.log` → `.jsonl` (collect history first); Kubernetes template annotations/labels need operator allowlists; reserved `internal.openshell.ai/` keys rejected; **hostname policy bound to supervisor-controlled DNS** (private security review, #4602); Restricted PSA for chart; Docker `supervisor_network_mode = "bridge"`; Error sandboxes can be restarted; `--env-from`; snap no longer enables the user gateway for every user |
| **0.1.6** | 10-27 | Gateway **refuses to start without user auth** (`allow_unauthenticated_users = true` opt-out; earlier 0.1.x gave unauthenticated callers an admin-level dev principal, #4814); control connection now sandbox → supervisor: **upgrade supervisor and sandbox runtime together**; `sandbox suspend/resume` (CLI/SDK; no built-in driver implements it yet — use stop/start); experimental shared supervisor on Kubernetes; OCSF audit events for auth denials and credential misuse; `server.extraEnv`, `pkiInitJob.podLabels/podAnnotations`; webpki emSign distrust (CVE-2026-111943), russh GHSA-4wc5-f2rc-q74m |
| main after 0.1.6 | — | Additional destination CAs for the Kubernetes supervisor (#3292, `supervisor.network.additionalCaConfigMapName`); hashed service hostnames for multi-gateway clusters (#4842) |

## Security history and support policy

- NVIDIA bulletin 2026-08-25 (`github.com/NVIDIA/product-security`, 2026/5872): six OpenShell
  CVEs (sandbox escape CVE-2026-65093 9.9, provisioning denylist CVE-2026-65083 9.9, command
  injection via malicious gateway, L7 path traversal, exec handler injection, inference proxy
  escaping) — all `0 to 0.0.33`, fixed in 0.0.34. None published against 0.1.x so far.
- The repo's GitHub Security Advisories page is empty even though `SECURITY.md` names GHSA as
  the channel: watch NVIDIA product-security bulletins **and** read release notes (security
  fixes ship as ordinary "bug fixes", e.g. #4602).
- Support: newest patch of the latest minor; backports to N-1 only when affected. Stay current.
- Open L7 parser-differential concerns: #4475 (harness request), #3902 (`%3B` decoded before
  `;params` stripping retargets the path).

## Outdated patterns (0.0.x) still in circulation

Blog posts and AI answers written before 2026-09-25 (and some after, copied from them) use:

| Outdated | Current (0.1.x) |
|---|---|
| `openshell inference set`, `https://inference.local` | Provider attached to the sandbox; agent calls the real endpoint |
| `sandbox create -- claude` relying on a preinstalled agent | `--from <your image with the agent>`; default image has none |
| `--from base` / `--from ollama` / `--from ./Dockerfile` | Build and push yourself; pass a full image reference |
| Built-in profiles, aliases `claude`, `gh` | `profile import` first; IDs `claude-code`, `github` |
| `--provider` inferred from the command | `--provider <name>` explicit (or `--auto-providers`) |
| gateway.toml `version = 1`, `compute_drivers = [..]` | `version = 2`, `compute_driver = ".."`, driver tables `[openshell.drivers.<name>]` |
| `tls: terminate` / `tls: passthrough` in policies | Omit `tls` (automatic inspection); `skip` disables inspection |
| `openshell gateway start/stop`, `uv tool install openshell` | Package-managed user service (`install.sh`) or the Helm chart |
| `policy update` without `--rule-name`/`--binary` | Both mandatory (or `--any-binary`) |
| Offset pagination, scalar time fields, `deleted` booleans in SDKs | Page tokens, protobuf Timestamp/Duration, `DeletionOutcome` |
| `ghcr.io/nvidia/openshell-community/sandboxes/*` images | Archived 2026-10-07; `base` ships a policy with `tls: terminate` → `ConfigurationInvalid` (#4467) |
| Chart values `supervisor.topology`, `supervisor.sidecar.*`, AppArmor | Removed by RFC 0012 |

## Ecosystem version lag

- **NemoClaw** (OpenClaw/Hermes/Deep Agents on OpenShell) pins OpenShell **0.0.116**
  (`nemoclaw-blueprint/blueprint.yaml`; NemoClaw v0.0.139, 2026-10-26, still uses
  `inference.local`). Its docs describe 0.0.x behaviour; don't transplant them to a 0.1.x gateway.
- OpenClaw's OpenShell backend docs use bare `from: "openclaw"` (0.0.x).
- `langchain-ai/openshell-deepagent` archived 2026-10-16 (0.0.x CLI).
- Python SDK on PyPI can lag the GitHub release by a version.
- In-repo drift on main: `examples/local-inference` still mentions built-in profiles;
  `examples/multi-agent-notepad/demo.sh` creates providers without importing profiles first;
  an overview.mdx TypeScript example uses `image: 'base'`. Trust `docs/upgrade/0-1-0.mdx`.
