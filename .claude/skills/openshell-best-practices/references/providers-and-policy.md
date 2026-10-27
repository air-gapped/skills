# Providers, profiles and policy (0.1.x)

Verified against `v0.1.6` docs (`docs/how-it-works/providers/*.mdx`,
`docs/how-it-works/policies/*.mdx`, `providers/*.yaml`). For exhaustive CLI flags and policy
generation, upstream ships the `openshell-cli` and `generate-sandbox-policy` skills
(`npx skills add NVIDIA/OpenShell`).

## Contents

- Mental model
- Provider workflow
- Writing `binaries`
- Agents: Claude Code, Codex, OpenCode, local models
- Policy lifecycle
- What policy does not protect

## Mental model

- **Profile** = a provider *type*: credential names and env vars, the endpoints the
  credential may reach, the binaries allowed to use them, refresh behaviour. The gateway ships
  **none**; you import them (global or per workspace). Upstream's `providers/*.yaml` are
  reviewable starting points, not defaults.
- **Provider** = an instance: a profile plus the real secret, stored in the **gateway** (DB,
  Kubernetes Secrets, or Vault), never on the client.
- **Attachment** = provider ↔ sandbox. The sandbox env gets an opaque placeholder; the
  supervisor substitutes the real value only on requests to the profile's endpoints.
  Detaching revokes it.
- **Policy** = filesystem (Landlock), process, and network rules. Network rules hot-reload;
  filesystem/Landlock/process settings are fixed at creation (recreate to change).

## Provider workflow

```bash
# 1. profile: copy from the clone at your release tag, edit binaries, lint, import
git -C ~/src/OpenShell show v0.1.6:providers/openai.yaml > providers/openai.yaml
openshell profile lint -f providers/openai.yaml
openshell profile import -f providers/openai.yaml --global        # or --url <raw https>
# 2. provider: secret from the local env var, never on the command line
openshell provider create --name openai --type openai --global-profile --credential OPENAI_API_KEY
#    (--from-existing loads all of a profile's env vars from local state)
# 3. attach
openshell sandbox create --name work --from <image> --provider openai -- opencode
openshell sandbox provider attach work openai     # existing sandbox
# verify the agent only sees a placeholder
openshell sandbox exec -n work --no-tty -- printenv OPENAI_API_KEY </dev/null
```

`--provider <name>` naming a missing provider whose name matches an imported profile prompts
to create it from local credentials; `--auto-providers` / `--no-auto-providers` decide that
non-interactively. Pass `-g <gateway>` in scripts — profiles and providers are per gateway.

## Writing `binaries`

The single most common failure: the profile is listed, but the credential is never injected
and traffic is denied, because `binaries` don't match the image.

- OpenShell matches the **real path** of the executable as the kernel reports it. List real
  paths, not symlinks (`readlink -f` inside the sandbox). On Kubernetes boundary mode a
  symlinked path is matched literally with no log line (#4834, won't fix).
- Scripts match their **interpreter** (`pip` → `/usr/bin/python3.12`; npm-installed CLIs →
  node, or the package path such as `/usr/lib/node_modules/@anthropic-ai/**`).
- A listed binary's **child processes inherit the grant** — listing the agent lets every tool
  it spawns use the rule. `/**` globs defeat binary scoping.
- Executables are SHA-256 pinned on first use; replacing the file later is denied.
- An empty `binaries` list allows nothing.

## Agents

| Agent | Credential path |
|---|---|
| Claude Code | `claude-code` profile takes a Console **API key** (`ANTHROPIC_API_KEY`, sent as `x-api-key`); subscription tokens don't work through the provider. A subscription works only by `claude auth login --claudeai` *inside* the sandbox — the OAuth token then lives on the sandbox disk |
| Codex | `codex` profile: ChatGPT OAuth tokens (`CODEX_AUTH_ACCESS_TOKEN`, `_REFRESH_TOKEN`, `_ACCOUNT_ID`, `_ID_TOKEN`) taken from the host's `~/.codex/auth.json`, with gateway-managed `oauth2_refresh_token` refresh (see `examples/codex-app-server`). Codex also fetches `*.oaiusercontent.com`, which no profile allows (#4885) |
| OpenCode | Reads provider keys from env (`OPENAI_API_KEY`, …) → works with providers. Its own ChatGPT login inside the sandbox ("Codex device code") stores tokens in `/sandbox/.local/share/opencode/` |
| Local models | Profile naming the real endpoint, `credentials: []`, `--env OPENAI_BASE_URL=http://host.openshell.internal:<port>/v1` (never `localhost`) |
| LiteLLM / vLLM in the cluster | Custom profile for its hostname; private IPs need `allowed_ips: ["10.0.0.0/8"]` in the endpoint (SSRF guard; loopback/link-local always blocked). Don't point the stock `openai`/`anthropic` profiles at another host — a provider whose base URL is elsewhere is treated as endpointless |

Rule of thumb: an agent's **own** login inside the sandbox puts the real token in the
sandbox; only providers keep secrets out. Prefer providers for anything shared.

## Policy lifecycle

- Default policy: deny all network; read-write `/sandbox` (persistent, `$HOME`), `/tmp`,
  `/dev/null`.
- Blocked request → OpenShell drafts a narrow proposal (binary → host:port) automatically.
  Review: `openshell rule get <sb> --status pending`, `rule approve <sb> --chunk-id ID`,
  `rule reject <sb> --chunk-id ID --reason ".."` (the TUI requires a reason), `rule approve-all`
  (skips security-flagged chunks unless `--include-security-flagged`).
- Agent-driven: `openshell settings set --global --key agent_policy_proposals_enabled --value true --yes`
  gives the agent `/etc/openshell/skills/policy_advisor.md` and `http://policy.local`
  (`POST /v1/proposals`, `GET .../{id}/wait?timeout=300`).
- **Keep approval mode `manual`.** `auto` approves any new public host that carries no
  credential — tests show it grants exfiltration targets 12/12 times. Never let the agent
  approve its own proposals.
- Incremental edit: `openshell policy update <sb> --rule-name github_ro --binary /usr/bin/gh
  --add-endpoint api.github.com:443:read-only:rest:enforce --wait` (`--rule-name` and every
  `--binary`, or `--any-binary`, are mandatory). Some fields (`allow_encoded_slash`, `tls: skip`)
  can't be set this way (#4926, #4903) — edit the full policy.
- Full edit: `openshell policy get <sb> --base | sed '1,/^---$/d' > p.yaml` (the `--full` output
  has a header `policy set` rejects), edit, `openshell policy set <sb> --policy p.yaml --wait`.
- What is actually allowed: `policy get <sb> --full` — `rule get` lists only proposals and can
  read "No network rules" on a sandbox that has some (#4927).
- **L7 `enforcement` defaults to `audit`** (logs violations, forwards traffic). Set
  `enforcement: enforce` explicitly; run audit first, then enforce. An endpoint without
  `protocol` allows any method and path.
- MCP: `protocol: mcp` with method/tool rules; tool **arguments** are not matched; only MCP
  revision `2025-11-25` unless `mcp.versions` says otherwise; an MCP endpoint can't share
  host:port with another protocol.
- Offline check: `openshell-prover check --boundary boundary.yaml policy.yaml` (covers
  filesystem, L4, REST, process, Landlock; GraphQL/WebSocket/MCP/JSON-RPC return
  `unsupported`; doesn't resolve hostnames; not run automatically at sandbox start). The snap
  package lacked the prover before 0.1.6. There is no `openshell policy validate` command —
  agents frequently invent it (#4492).

## What policy does not protect

- **Exfiltration through allowed channels.** Any allowed write endpoint, GET query strings
  and headers, or the model endpoint itself can carry data the agent read. OpenShell
  *contains* prompt injection; it doesn't *detect* it. Keep untrusted input, private data and
  network egress from meeting in one sandbox.
- Placeholders are scoped by **endpoint**, not by calling binary: any binary the network
  policy lets reach a bound host can use the credential there.
- `tls: skip` (needed for pinned or mTLS clients) disables inspection and credential rewrite;
  credentialed endpoints then need `allow_uninspected_credentials`.
- Isolation is a shared kernel (Landlock + seccomp + network namespace). For stronger
  boundaries, layer a VM/Kata runtime (`server.defaultRuntimeClassName`, or the VM driver).
- Landlock and process events go to the workload container log only, not the gateway or
  supervisor OCSF stream; `exec`/SSH session output is not logged.
