Freshened: 2026-10-20

# Sources

External references backing this skill's claims. Freshen mode probes every row.

| Ref | URL | Pinned / notes |
|---|---|---|
| Claude Code environment variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN` → Bearer, `ANTHROPIC_API_KEY` → X-Api-Key, `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`, `ENABLE_TOOL_SEARCH` — `false` loads all tools upfront, telemetry vars, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_SKIP_PROMPT_HISTORY`) | https://code.claude.com/docs/en/env-vars | — |
| Claude Code CLI reference (`--safe-mode`, `--strict-mcp-config`, `--no-session-persistence`, `--permission-mode dontAsk`, `--disable-slash-commands`, `--tools`, `--no-chrome`, `--bare` — never reads OAuth, `--restricted`, `setup-token`) — also checked via `claude --help` | https://code.claude.com/docs/en/cli-reference | claude 2.1.304 |
| Claude Code changelog 2.1.221–2.1.304: `--bare` added 2.1.81, MCP-only-named 2.1.286, `/login` fix 2.1.288; `--restricted` 2.1.248; `-p` default auto mode 2.1.285, reverted to `default` 2.1.302; 1M window behind a custom base URL for models that have one 2.1.285; `CLAUDE_CODE_OAUTH_TOKEN` headless 401 fix 2.1.225; tool search on by default behind a custom base URL 2.1.304 | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md | claude 2.1.304 |
| Claude Code headless mode (stream-json `system/init` with `tools` and `model`, final `result` event, `--include-partial-messages` → `stream_event`) | https://code.claude.com/docs/en/headless | — |
| Claude Code permissions (deny → ask → allow order; `dontAsk` auto-denies every call that would prompt) | https://code.claude.com/docs/en/permissions | — |
| Claude Code LLM gateway guidance ("doesn't support routing Claude Code to non-Claude models through any gateway") | https://code.claude.com/docs/en/llm-gateway | — |
| Local execution evidence: `claude --help`; `tests/test-offline.sh`; live smoke through a Messages-compatible gateway — 400 "Deferred custom tools are only supported on Anthropic models" with `result.subtype=success`, `is_error=true` until `ENABLE_TOOL_SEARCH=false`, then pass; planted-leak reproduction of `scan-token-leakage.sh` | n/a (local run) | claude 2.1.304 |
