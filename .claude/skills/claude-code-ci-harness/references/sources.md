# Sources

External references backing this skill's claims, with verification stamps.
Freshen mode probes these rows first.

| Ref | URL | Last verified | Pinned |
|---|---|---|---|
| Claude Code environment variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN` → Bearer, `ANTHROPIC_API_KEY` → X-Api-Key) | https://code.claude.com/docs/en/env-vars | 2026-08-01 | — |
| Claude Code CLI reference (`--safe-mode`, `--strict-mcp-config`, `--no-session-persistence`, `--permission-mode dontAsk`, `--disable-slash-commands`, `--tools`, `--no-chrome`, `--bare`, `--restricted`, `setup-token`) — checked via `claude --help` | https://code.claude.com/docs/en/cli-reference | 2026-10-14 | claude 2.1.296 |
| Claude Code changelog 2.1.221–2.1.296 (`--bare` 2.1.288, `--restricted` 2.1.248, `-p` auto-mode default and 1M window behind base URL 2.1.285, `CLAUDE_CODE_OAUTH_TOKEN` headless fixes) | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md | 2026-10-14 | claude 2.1.296 |
| Claude Code headless mode (stream-json event shapes, `--include-partial-messages`) | https://code.claude.com/docs/en/headless | 2026-08-01 | — |
| Claude Code permissions (deny/ask/allow precedence, `dontAsk`) | https://code.claude.com/docs/en/permissions | 2026-08-01 | — |
| Claude Code LLM gateway guidance (third-party base URLs are unsupported configurations) | https://code.claude.com/docs/en/llm-gateway | 2026-08-01 | — |
| Local execution evidence: `claude --help`, offline test incl. subscription mode, one live smoke run against a Messages-compatible endpoint | n/a (local run) | 2026-10-14 | claude 2.1.296 |
