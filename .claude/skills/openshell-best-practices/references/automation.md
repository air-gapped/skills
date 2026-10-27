# Automation: headless agents, SDKs, fleets (0.1.x)

Verified against `v0.1.6` (`docs/how-it-works/sandboxes/overview.mdx`, `docs/sdk/*.mdx`,
`scripts/agents/` "gator", `examples/multi-agent-notepad`, `examples/codex-app-server`).

## Contents

- Headless runs from the CLI
- Limits
- Login for unattended jobs
- SDKs
- Reference patterns (gator, fan-out, Claude self-hosted sandboxes)
- Extension points

## Headless runs from the CLI

```bash
# fire-and-forget: the gateway deletes the sandbox when the main program exits
openshell -g prod sandbox create --name job-42 --from $IMG \
  --provider openai --no-auto-providers --no-tty --detach --no-keep \
  -- opencode run "fix the failing tests" </dev/null
# keep it, restart on crash (backoff 1 s doubling to 3 min)
openshell sandbox create ... --detach --restart-policy on-failure -- worker
# drive step by step
openshell sandbox exec -n job-42 --no-tty --no-login-shell -- claude -p "now write the docs" </dev/null
openshell sandbox get job-42 -o json        # phase: Ready / Completed (exit 0) / Error (MainProcessFailed)
openshell logs job-42 --since 10m --source sandbox
openshell sandbox download job-42 /sandbox/out ./out
```

- Redirect stdin (`</dev/null`) in scripts and CI. The main program's stdin stays open by design,
  so a headless agent run as the main program waits forever on stdin (`opencode run` hang,
  #3883) — wrap it: `-- sh -c 'opencode run "..." </dev/null'`.
- `--no-login-shell` skips `bash -lc` startup files for `exec`.
- `--env-from KEY[=ENVVAR]` (0.1.5) keeps values out of argv; credential-looking `--env` keys
  warn — attach secrets as providers instead.
- `-o json` on list/get commands for parsing; don't scrape tables (columns change).
- Sandbox names: DNS-1123 labels; keep them short (the gator harness caps at 19 characters).

## Limits

- Trailing command: ≤ 256 arguments, ≤ 32 KiB each, ≤ 256 KiB total — upload long prompts as files.
- `--upload` can't be combined with a trailing command: create `--detach`, `upload`, then `exec`.
- Streamed stdin capped at 4 MiB.
- After the main program exits, `connect`/`exec` are refused; `download`, SSH and `forward`
  still work (#4949).

## Login for unattended jobs

A person's browser login doesn't fit cron/CI. Create a **confidential** OIDC client
(client credentials, service account, audience mapper for the gateway audience, a role such as
`openshell-user` on its service-account user), register the gateway with
`--oidc-client-id <that client>`, and set `OPENSHELL_OIDC_CLIENT_SECRET`. Open bug: the CLI
can't renew client-credentials tokens when they expire (#4287, PR #4389) — re-run
`openshell gateway login` before each job or keep jobs shorter than the token lifetime. The
SDKs handle client credentials in memory and renew within 30 s of expiry.

## SDKs

| Language | Install | Notes |
|---|---|---|
| Python ≥ 3.11 | `uv add openshell` | `SandboxClient.from_active_cluster(client_credentials=ClientCredentialsAuth(client_secret=lambda: ...))`; `create(workspace=, name=, labels=)`, `wait_ready`, `exec_stream` (`ExecChunk` … `ExecResult`), `list_all(label_selector=)`, `sandbox_templates()`, `create_from_template`, `delete` + `wait_deleted`. PyPI can lag a release |
| TypeScript | `@nvidia/openshell-sdk` from GitHub Packages (`.npmrc` `@nvidia:registry=https://npm.pkg.github.com`, token with `read:packages`) | `execStream`, `execInteractive`, `forward()`, `rawSpec` escape hatch (e.g. `runtimeClassName: 'gvisor'`), `client.raw`; no upload/download |
| Go ≥ 1.25 | `go get github.com/NVIDIA/OpenShell/sdk/go@<tag>` | client-go style, watches, `fake.Client`; `oidc.NewClientCredentialsAuth`. Token file incompatible with the CLI's (#4508): log in via the CLI only; edge token cached for client lifetime (#4515) |
| Rust | `cargo add openshell-sdk --git https://github.com/NVIDIA/OpenShell --tag <tag>` | |

API rules since 0.1.0: always pass the **workspace** (omission no longer means `default`);
page tokens, not offsets; `DeletionOutcome.ACCEPTED` is asynchronous; mutations are not
auto-retried — reuse `request_id` and reconcile on `REQUEST_OUTCOME_UNCERTAIN`. There is no
REST API; the gateway is gRPC (`openshell.v1.OpenShell`).

## Reference patterns

- **Manifest-driven agent fleet ("gator", `scripts/agents/`)**: an `agent.yaml` names harness,
  providers (credential sources: host command, JSON file, gateway-managed OAuth refresh),
  prompt and poll interval; the payload is baked into the image read-only; launch is
  `sandbox create --provider … --no-auto-providers --no-tty --detach -- entrypoint`. The agent's
  own sandbox is disabled (`codex exec --sandbox danger-full-access`) because OpenShell is the
  boundary. Long-lived harnesses must store the current-name placeholder
  (`openshell:resolve:env:TOKEN`), not a revision-scoped one, so refreshed credentials resolve.
  Note: it enables `proposal_approval_mode=auto` for its own bot — don't copy that into
  interactive use.
- **Fan-out (`examples/multi-agent-notepad`)**: N detached sandboxes, each uploads a payload
  and runs one `exec`; agents coordinate only through a narrowly allowed API path; per-run
  providers are created and deleted in a shell `EXIT` trap.
- **Claude Managed Agents self-hosted sandboxes**: Anthropic keeps the agent loop; your worker
  polls a `self_hosted` environment and runs tool calls. Per-session pattern: the
  `ant beta:worker poll --on-work ./spawn.sh` script starts one OpenShell sandbox per session
  running `ant beta:worker run` with only the environment key and work secret, and policy
  allowing that binary to reach the Anthropic API (Red Hat demonstrated this on Podman and
  OpenShift AI). The worker's default workdir is `/workspace`; Kubernetes sandboxes use
  `/sandbox`, so pass `--workdir /sandbox`. There is no OpenShell-specific code on either side.

## Extension points

- **Supervisor middleware** (`[[openshell.supervisor.middleware]]` gRPC service, attached per
  policy via `network_middlewares`): inspects requests after policy, before credential
  injection (never sees secrets); payload cap 4 MiB; `binding_policy` allowlist (0.1.6). API
  still evolving.
- **Gateway interceptors** (`[[openshell.gateway.interceptors]]`): `modify_operation` /
  `validate` / `post_commit` on allowlisted write RPCs (e.g. enforce image allowlists or signed
  policy on `CreateSandbox`, block `proposal_approval_mode=auto`); static registration, restart
  to change; can be the authoritative profile catalog (`provider_profile_sources`).
