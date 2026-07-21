# Sources

External claims in this skill, with source, tier, and verify date. Re-verify dated/volatile facts (latest image tag/digest, the v0.22 default change, env-var names) before relying on them — the project moves fast.

Tiers: **A** = primary (project README / official docs site / repo files) · **B** = derived/secondary.

| Source | Tier | Supports | Verified |
|---|---|---|---|
| github.com/sooperset/mcp-atlassian (README) | A | MCP server for Jira+Confluence; **DC supported (Jira v8.14+, PAT)**; key tools; 72 tools; `uvx`/Docker quick start | 2026-06-07 |
| github.com/sooperset/mcp-atlassian `pyproject.toml` | A | `requires-python>=3.10`; ~26 runtime deps; `uv-dynamic-versioning` build backend (version from git tags); entry point `mcp-atlassian` | 2026-06-07 |
| github.com/sooperset/mcp-atlassian `Dockerfile` | A | Build pulls deps via `uv sync` (PyPI); base images `ghcr.io/astral-sh/uv:python3.13-alpine` + `python:3.13-alpine`; `.venv` baked into final image; `ENTRYPOINT mcp-atlassian` | 2026-06-07 |
| github.com/sooperset/mcp-atlassian releases (gh) | A | Latest release **v0.23.0** (2026-07-18); also v0.22.1 (07-11) and **v0.22.0 (07-10)**. Three releases since the v0.21.1 baseline — the project resumed a fast cadence after a ~3-month gap | 2026-07-21 |
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
| github.com/sooperset/mcp-atlassian/issues — tracked set | A | **Re-probed 2026-07-21; three closed.** **FIXED:** #1262 transition+comment ADF (closed 2026-07-11 — v0.22.1 window), #1343 markdown pipe tables mangled (closed 2026-07-08), #1234 FastMCP CVEs (closed 2026-07-17 — v0.23.0 ships the FastMCP + Starlette bumps). **STILL OPEN:** #1274 `jira_create_issue_link` direction swapped, #1279 DC-behind-WAF 403 despite valid PAT, #1311 `jira_add_comment` strips `[~username]` mentions on Server/DC, #1340 underscores stripped from inline code, #1341 `jira_edit_comment` strips Markdown entirely | 2026-07-21 |
| GitHub Security Advisories — `fastmcp` | A | FastMCP `<3.2.0` CVEs scoped to OpenAPI-provider / OAuth-proxy+client / Windows-installer paths — none reached by local stdio+PAT. **#1234 closed 2026-07-17**; v0.23.0 ships security updates to FastMCP and Starlette, so the deferred-upgrade reasoning is now moot on current builds | 2026-07-21 |
| mcp-atlassian `src/mcp_atlassian/jira/transitions.py` (local clone @ v0.21.1, codegraph) | A | #1262 root cause: `_add_comment_to_transition_data` → `_markdown_to_jira` (wiki markup) not ADF; standalone `add_comment` converts ADF correctly | 2026-06-07 |


## 2026-07-21 freshen — the v0.22 warning came true, plus a critical transport fix

The 2026-06-07 header said "the project moves fast" and flagged a *forecast*
v0.22 default change. Three releases landed since: **v0.22.0 (2026-07-10),
v0.22.1 (07-11), v0.23.0 (07-18)**, after a ~3-month gap.

**v0.22.0 — a 37-advisory security audit.** Two items change behaviour for
operators regardless of CVE interest:

1. **Unauthenticated `streamable-http` no longer falls back to the operator's
   global credentials** (rated critical upstream). Pre-0.22, anyone who could
   reach the transport effectively acted as the operator. Now rejected with
   **401**; old behaviour opt-in via **`ALLOW_GLOBAL_CRED_FALLBACK`** (default
   off). **stdio deployments — the `claude mcp add` default — were never
   exposed.** The trap to warn about: setting that variable to silence a
   post-upgrade 401 re-opens the hole.
2. **Attachment / `content_file` paths are confined to the working directory**
   via `validate_safe_path` (closes arbitrary file read/exfiltration and an
   intra-CWD overwrite RCE variant). **Absolute paths now fail.** v0.22.0 adds
   **`content_base64`** for `upload_attachment` (#1366) as the intended route
   when the server can't read host paths.

Both recorded in `hardening.md`, with the toolset-default section rewritten from
forecast to shipped fact.

**v0.23.0 — new capability surface** worth knowing before answering "can the MCP
do X": JSM customer-request tools (`jira_get_request_types`,
`jira_get_request_type_fields`, `jira_create_customer_request`, #1241), epic
hierarchy and cross-project dependency mapping (`jira_get_project_epic_hierarchy`,
`jira_get_cross_project_dependencies`, #1286), `use_display_names` so custom
fields return `Story Points` rather than `customfield_10243` (#1156), `browse_url`
on issues and search results (#1471), plus **PAC/WPAD proxy and mTLS
connectivity** and external auth passthrough — the last two directly relevant to
the corporate-proxy and internal-CA scenarios this skill covers.

**Cross-check without calling anything:** this session's own MCP tool surface
includes `jira_get_request_types`, `jira_get_request_type_fields`,
`jira_create_customer_request`, `jira_get_project_epic_hierarchy` and
`jira_get_cross_project_dependencies` — all **v0.23.0-only** tools. That is
direct evidence the connected server is already at **≥ v0.23.0**, established
from the advertised tool list rather than by invoking a live Atlassian call.

**Not re-probed:** the docs-site pages (installation / authentication /
configuration / compatibility / tools-reference / troubleshooting). The tool
count and toolset tables they back are very likely stale after two feature
releases — see the backlog item.
