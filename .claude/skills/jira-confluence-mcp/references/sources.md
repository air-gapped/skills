# Sources

External claims in this skill, with source, tier, and verify date. Re-verify dated/volatile facts (latest image tag/digest, the v0.22 default change, env-var names) before relying on them — the project moves fast.

Tiers: **A** = primary (project README / official docs site / repo files) · **B** = derived/secondary.

| Source | Tier | Supports | Verified |
|---|---|---|---|
| github.com/sooperset/mcp-atlassian (README) | A | MCP server for Jira+Confluence; **DC supported (Jira v8.14+, PAT)**; key tools; 72 tools; `uvx`/Docker quick start | 2026-06-07 |
| github.com/sooperset/mcp-atlassian `pyproject.toml` | A | `requires-python>=3.10`; ~26 runtime deps; `uv-dynamic-versioning` build backend (version from git tags); entry point `mcp-atlassian` | 2026-06-07 |
| github.com/sooperset/mcp-atlassian `Dockerfile` | A | Build pulls deps via `uv sync` (PyPI); base images `ghcr.io/astral-sh/uv:python3.13-alpine` + `python:3.13-alpine`; `.venv` baked into final image; `ENTRYPOINT mcp-atlassian` | 2026-06-07 |
| github.com/sooperset/mcp-atlassian releases (gh) | A | Latest release **v0.21.1** (2026-04-10); repo live, not archived | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/installation | A | uvx (recommended) / Docker / pip / uv / source install methods | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/authentication | A | API token (Cloud), **PAT (Server/DC)**, OAuth 2.0, BYOT, multi-cloud, OAuth proxy; PAT-vs-token env vars; SSL note | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/configuration | A | Env-var catalog (connection, filtering, server, proxy, custom headers); IDE configs; tool filtering; v0.22 toolset-default warning | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/compatibility | A | Cloud-vs-DC matrix: auth methods, tool availability (Cloud-only changelogs/forms/page-views), content format (ADF vs wiki markup), accountId vs username, ~100 req/min Cloud rate limit | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/tools-reference | A | 72 tools; **15 Jira + 6 Confluence toolsets** with core flags; `TOOLSETS`/`ENABLED_TOOLS`/`READ_ONLY_MODE` mechanics | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/troubleshooting | A | 401/403, OAuth-expired, SSL (truststore + `JIRA_SSL_VERIFY=false` + `MCP_ATLASSIAN_USE_SYSTEM_TRUSTSTORE`), mTLS, field-not-found→`jira_search_fields`, 50 MB attachment cap, 429→batch tools, timeout (75s default), MCP Inspector, custom-header format | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/advanced/docker-production | A | Docker Compose / production deployment + read-only mode + Kubernetes notes | 2026-06-07 |
| mcp-atlassian.soomiles.com/llms-full.txt | A | The complete LLM-readable docs bundle (this skill points users here for tool/JQL/CQL depth rather than duplicating it) | 2026-06-07 |
| Claude Code `claude mcp add` | A | Adding a stdio MCP server to Claude Code with `-e KEY=val -- <command>` (upstream docs only show Claude-Desktop/Cursor JSON) | 2026-06-07 |
| skopeo / OCI digest pinning (supply-chain practice) | B | `skopeo copy --all` to mirror an image by digest into an internal registry; `@sha256:` pin over mutable tags | 2026-06-07 |
