---
name: claude-code-ci-harness
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Run Claude Code headlessly as an isolated CI harness against any Anthropic
  Messages-compatible endpoint (local engine, gateway or hosted API) or a
  Claude subscription token. Covers credential
  isolation, stream-json transcripts, tool-call assertions, multi-turn
  scenarios, and endpoint/model compatibility diagnosis.
when_to_use: |-
  Use for Claude Code CI harnesses, headless Claude Code tests, testing an
  endpoint through /v1/messages, Claude Code tool-call regressions,
  chat-template or tool-call parser testing, stream-json transcripts, model
  compatibility testing, or safely running Claude Code against a
  non-Anthropic model.
---

# Claude Code CI Harness

Never invoke `claude` directly for a test. Always use
`scripts/isolated-run.sh`. It isolates the run from the caller's profile.

## Run

```bash
${CLAUDE_SKILL_DIR}/scripts/isolated-run.sh MODE_FLAGS \
  --workdir DIR --transcript OUT.ndjson --prompt 'PROMPT'
```

| Mode | `MODE_FLAGS` |
|---|---|
| Endpoint, no auth | `--base-url URL --model SERVED_NAME` |
| Endpoint, bearer token | `--base-url URL --model SERVED_NAME --token-var VAR` |
| Endpoint, `X-Api-Key` header | `--base-url URL --model SERVED_NAME --token-var VAR --x-api-key` |
| Claude subscription | `--model CLAUDE_ALIAS_OR_ID` (no `--base-url`; token var defaults to `CLAUDE_CODE_OAUTH_TOKEN`) |

| Flag | Rule |
|---|---|
| `--base-url` | Endpoint root without `/v1`, local or remote. |
| `--model` | The exact name the endpoint serves; a Claude alias or ID in subscription mode. |
| `--token-var` | Name of a variable in the secrets file. |
| `--x-api-key` | Only for endpoints that require the token in an `X-Api-Key` header. |
| `--tools` | Built-in tool allowlist. Default: `Read,Glob`. |
| `--timeout` | Wall-clock limit in seconds. Default: 180. `0` disables it. |

## Secrets

The secrets file is `~/.config/claude-code-ci-harness/targets.env`. Each line is `KEY=value`. The file must be mode 0600, owned by the user, not a symlink, and outside Git. The runner rejects any other file.

- Subscription token: the user runs `claude setup-token` in a separate terminal and adds `CLAUDE_CODE_OAUTH_TOKEN=<token>` to the file. Never run `setup-token` inside an agent session, because the token would land in the transcript.
- Never copy `~/.claude/.credentials.json` into a run. Its refresh token rotates, and a rotated copy logs out the user.
- Never put a token in a flag, a transcript or the skill directory.

## Do not change in the runner

| Keep | Reason |
|---|---|
| `--safe-mode` | Disables CLAUDE.md, skills, plugins and hooks. |
| `--permission-mode dontAsk` | Without it, `-p` starts in auto mode. |
| `--strict-mcp-config` with an empty config | Blocks the caller's MCP servers. |
| Empty `ANTHROPIC_API_KEY` | Stops an inherited key from overriding the intended token. |
| No `--bare` | It disables OAuth and has dropped `Glob` from `--tools`. |

## Test

1. Run `scripts/make-fixtures.sh DIR` to build the workdir.
2. Run the smoke scenario. Then escalate through `references/scenario-bank.md`, and stop at the first failure.
3. Assert on events with `scripts/assert-events.sh` (result success, tool sequence, model, turn bounds). Exit status is not evidence.
4. For more than one endpoint, use `scripts/run-matrix.sh --run 'label|base-url|model[|token-var]'`. An empty base-url means subscription mode.
5. Scan every transcript with `scripts/scan-token-leakage.sh`.
6. When an endpoint fails, record it as an endpoint/model compatibility finding. Never change the scenario to make it pass.
7. Run `scripts/cleanup.sh` afterwards.

## References

- `references/scenario-bank.md`: scenarios and pass criteria
- `references/known-gaps.md`: symptom → cause → check
- `references/isolation.md`: what the runner isolates, for anyone editing it
- `references/sources.md`: verification stamps (freshen mode only)
