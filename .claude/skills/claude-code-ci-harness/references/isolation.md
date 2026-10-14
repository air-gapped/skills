# Isolation

What `scripts/isolated-run.sh` enforces. Keep all of it when editing the runner.

| Mechanism | Setting |
|---|---|
| Environment | `env -i`, plus a throwaway `CLAUDE_CONFIG_DIR`, `HOME`, `XDG_{CONFIG,DATA,STATE,CACHE}_HOME` and `TMPDIR` |
| Customizations | `--safe-mode` and `--disable-slash-commands` |
| Hooks | `--settings` set to `{"disableAllHooks":true}` |
| Sessions | `--no-session-persistence` |
| MCP | `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`, `--disallowed-tools 'mcp__*'` and `--no-chrome` |
| Permissions | `--permission-mode dontAsk`, and `--tools` set the same as `--allowed-tools` |
| Telemetry | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_TELEMETRY=1` and `DISABLE_ERROR_REPORTING=1` |

## Auth

| Mode | Env set in the child |
|---|---|
| Endpoint (`--base-url`) | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN=<token>` and `ANTHROPIC_API_KEY=` (empty; the token goes here instead with `--x-api-key`). `ANTHROPIC_MODEL` and `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` are all set to `--model`. |
| Subscription (no `--base-url`) | `CLAUDE_CODE_OAUTH_TOKEN=<token>` and `ANTHROPIC_API_KEY=` (empty). Nothing else. |

## Secrets file

The runner rejects the file if it is a symlink, not owned by the user, readable by group or world, or inside a Git worktree. It parses `KEY=value` and never sources the file. It reads only the `--token-var` key.

## Verify after a CLI upgrade

- The `system/init` event's `tools` array lists exactly the `--tools` set.
- `tests/test-offline.sh` passes.
