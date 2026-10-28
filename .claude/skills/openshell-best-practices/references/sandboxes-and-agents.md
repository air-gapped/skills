# Sandboxes, agent images and daily use (0.1.x)

Verified against `v0.1.6` (`docs/how-it-works/sandboxes/*.mdx`,
`examples/bring-your-own-container/`) and field reports dated after 2026-09-25.

## Contents

- Agent images
- Session model: main program, detach, exec
- Logins inside agents
- Laying out several agents
- Tools that break inside the sandbox
- File transfer and ports

## Agent images

OpenShell builds and ships no agent images. The default (`nvcr.io/nvidia/base/ubuntu:24.04`)
has no agent CLI, and `NVIDIA/OpenShell-Community` (the old `base`, `ollama`, `pi`, … images)
was **archived 2026-10-07** — its `base` image bakes a policy with the removed
`tls: terminate`, so sandboxes sit in `ConfigurationInvalid` until `ProvisioningTimedOut`
(#4467; workaround: pass an explicit `--policy`). Build your own:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make ripgrep fd-find && rm -rf /var/lib/apt/lists/*
# install the agent CLI(s) here (Claude Code, Codex, OpenCode, Pi, ...)
RUN useradd -m -u 1000 agent
USER agent
WORKDIR /sandbox
```

Requirements and conventions:

- A normal glibc Linux base; distroless and `scratch` agent images are unsupported. amd64 or arm64.
- **Non-root.** `USER root` fails with `IdentityResolutionFailed … UID or GID zero` (#4030);
  images without `USER` run as 1000:1000 on Docker/Podman; Kubernetes runs the workload as
  `sandbox_uid` (default 10001).
- The image's ENTRYPOINT/CMD are **replaced** by the sandbox runtime: pass the command after `--`.
- `/sandbox` content seeds the persistent workspace on first start; `/sandbox` is `$HOME`.
- Pre-install everything the agent would otherwise download at runtime (ripgrep/fd, MCP
  servers, language toolchains) — the sandbox has no network until policy allows it, and
  in air-gapped sites never will.
- Bake agent config the sandbox needs, e.g. opencode keybindings (below), under `/sandbox`.
- Note each agent binary's **real path** for provider `binaries` (`readlink -f $(which claude)`).
- Optional default policy at `/etc/openshell/policy.yaml` (used only when the sandbox has no
  saved policy and the gateway has no global policy; an invalid file blocks provisioning).
  The built-in default policy lacks `/dev/pts`, so terminal multiplexers (herdr, tmux) fail
  with `openpty: Permission denied`: bake a policy that adds it to `read_write`. A
  `filesystem_policy` section flips `include_workdir` to false — set it to `true` explicitly.
- Bake mirror settings and model base URLs too; proxy variables are stripped inside sandboxes
  (`air-gap-and-ca.md`).
- No image allowlist exists; to restrict images use admission control (Kyverno/Gatekeeper) or
  a gateway interceptor on `CreateSandbox`. Sandbox templates help users pick, not enforce.

## Session model

| Action | Behaviour |
|---|---|
| `sandbox create --name x --from IMG [--provider P] -- agent` | The agent is the sandbox's **main program**; your terminal attaches to it |
| Ctrl-D, or Ctrl-P then Ctrl-Q | **Detach** from the main program; it keeps running with stdin open. OpenShell consumes these keys on the main session — the program never sees Ctrl-D there |
| `sandbox connect x` | Reattach to the main program; replays up to 1 MiB of output; auto-reconnects for 60 s after sleep/network loss |
| `sandbox exec -n x --tty -- bash -l` | A separate shell. **Cannot detach**; leaving it ends what runs in it. Ctrl-D reaches the program |
| main program exits | With the default `--restart-policy never`: sandbox → `Completed` (exit 0) or `Error`; `connect`/`exec` are refused, SSH/upload/download/forward still work (#4949). Detach rather than quit an agent you want to come back to; `--restart-policy on-failure`/`always` restarts it (backoff 1 s → 3 min) |
| `sandbox stop` / `start` | Keeps the workspace. `suspend`/`resume` exist in the 0.1.6 CLI but every built-in driver returns "does not support sandbox suspend" |

Make the agent the main program (`-- opencode`, or **Command** in the TUI create dialog), not
something started from an extra shell, when you want detach/reattach.

**opencode quits on Ctrl-D** by its own default (`app_exit: ctrl+c,ctrl+d,<leader>q`), which
bites in `exec` shells. Bake into the image:

```json
// /sandbox/.config/opencode/tui.json
{"$schema": "https://opencode.ai/tui.json", "keybinds": {"app_exit": "ctrl+c,<leader>q"}}
```

## Logins inside agents

- OAuth logins that redirect to `http://127.0.0.1:<port>/callback` fail: your browser's
  127.0.0.1 is your laptop, the agent listens in the sandbox. Use the agent's **device-code**
  login (opencode: "Codex device code"; Claude Code prints a code to paste back), or forward
  the callback port first: `openshell forward start <port> <sandbox> -d` (OpenAI/Codex browser
  login uses 1455).
- Any login done inside the agent leaves the real token on the sandbox disk, readable by
  everything in that sandbox. Use providers when that matters (`providers-and-policy.md`).

## Laying out several agents

| Layout | Trade-off |
|---|---|
| One sandbox per agent, a terminal multiplexer on the client with each pane running `openshell sandbox connect <name>` | Isolation per agent (own policy, own providers). Client-side tools see only `openshell` as the pane process: herdr needs `HERDR_AGENT=claude openshell sandbox connect …` for state detection, and integrations that call back into the multiplexer (hooks, socket API, session restore) can't reach it from the sandbox |
| One sandbox with a multiplexer (herdr, tmux) as main program and many agents in panes | Everything native, survives the laptop being off; all agents share one policy, one set of providers and one filesystem. Size `--cpu`/`--memory` for all of them; set `XDG_CONFIG_HOME=/sandbox/.config` so state persists; Ctrl-D never reaches the multiplexer (OpenShell detaches) |

Both are valid; the second is often the pragmatic choice for one person's own work.

## Tools that break inside the sandbox

The child seccomp filter and namespace hardening break some common tools (open at 0.1.6):

| Symptom | Cause | Workaround |
|---|---|---|
| `make: true: Operation not permitted` | `setresuid/setresgid` denied even with unchanged IDs (#4102) | GNU Make ≥ 4.4.1 in the image |
| `cannot set niceness`, dotnet thread priority errors | `setpriority`/`ioprio_set` denied (#4026) | `DOTNET_gcServer=0`; avoid `nice` |
| Chromium/Playwright `No usable sandbox!` | `CLONE_NEWUSER` blocked (#4098) | `--no-sandbox` |
| .NET SqlClient connects time out | non-blocking `connect` returns 0 (#4980) | `Connect Timeout=0` |
| `dd if=/dev/zero` fails | not in default read list | add to filesystem policy |
| Docker-in-Docker | unsupported (#4970) | — |
| `sandbox download` fails on Alpine/busybox | probe uses GNU `realpath -e` (#4909) | `apk add coreutils` |

## File transfer and ports

- `sandbox upload <sb> ./dir` respects `.gitignore` and fails closed when Git filtering fails
  (`--no-git-ignore` to override); uploads from WSL2 `/mnt/<drive>` arrive as NUL bytes (#3728)
  — copy to a WSL-native path first.
- `--upload` at create time cannot be combined with a trailing command: create, upload, then
  `exec` or `connect`.
- `openshell forward start <port> <sb> -d` / `forward list` / `forward stop`; SSH reverse
  forwarding is unsupported by design (#4379) — use `host.openshell.internal` for host services.
- `--editor vscode|cursor` or `sandbox ssh-config <sb>` for remote editors.
- Every transfer goes through the gateway's single gRPC endpoint (one port).
