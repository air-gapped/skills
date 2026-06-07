# Troubleshooting mcp-atlassian

Symptom → cause → fix. Most failures are auth, TLS, field, or rate-limit. The server's own error text plus verbose logging usually pinpoints it.

## Tools missing (one product absent)

| Symptom | Cause | Fix |
|---|---|---|
| **`confluence_*` tools don't appear** though the server is ✓ Connected and `jira_*` work (or the reverse) | Only one product's env is set — mcp-atlassian runs a **separate client per product**, and `JIRA_*` vars do **not** carry over to Confluence. Missing creds ⇒ that product's tools silently don't register (no error). | Add `CONFLUENCE_URL` (**ends `/wiki` on Cloud**; DC = Confluence's own host/context path) + `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` (Cloud: **same email + token as Jira**). **Reconnect** (`/mcp` → reconnect, or restart Claude Code — env is read only at spawn). Verify with `claude mcp list` ✓ and the now-present `confluence_*` tools. |

`TOOLSETS=all`/default already includes both products' core tools, so absent tools point to **credentials, not toolset config**.

## Authentication

| Symptom | Cause | Fix |
|---|---|---|
| **401 — Cloud** | Wrong/expired API token, or `JIRA_USERNAME` isn't the email | Use an API token (not the account password); confirm username = email; test `curl -u "you@co:token" https://co.atlassian.net/rest/api/2/myself` |
| **401 — PAT (DC)** | Invalid/expired PAT or missing perms; over the 10-PAT cap | New PAT with sufficient perms; test `curl -H "Authorization: Bearer <pat>" https://jira.internal/rest/api/2/myself` |
| **403 Forbidden** | Account lacks permission for the op; **or `READ_ONLY_MODE=true` is blocking a write** | Check project perms / admin rights for admin-only fields; if it's a write, confirm `READ_ONLY_MODE` isn't set |
| **OAuth token expired** | Access token expired, refresh failed | Re-run `mcp-atlassian --oauth-setup`; ensure `offline_access` scope; confirm the OAuth app is still active |

## TLS / connection (self-hosted)

| Symptom | Cause | Fix |
|---|---|---|
| **SSL verification failed** | Internal-CA / self-signed cert not trusted (esp. inside the container) | Mount the CA (`-v …:/usr/local/share/ca-certificates/…:ro`) or `JIRA_SSL_VERIFY=false` / `CONFLUENCE_SSL_VERIFY=false`; `MCP_ATLASSIAN_USE_SYSTEM_TRUSTSTORE=false` to use certifi. See `references/air-gapped.md` |
| **mTLS required** | Instance demands client cert | `JIRA_CLIENT_CERT=/path/cert.pem` + `JIRA_CLIENT_KEY=/path/key.pem` |
| **Connection timeout** | Slow/unreachable instance, or proxy needed | Raise `JIRA_TIMEOUT=120`; set `HTTPS_PROXY=…` if a proxy is required |
| **Copilot: "Retrieved 0 tools"** | Old version / protocol mismatch | Use `mcp-atlassian >= 0.16.0` |

## Field & data

| Symptom | Cause | Fix |
|---|---|---|
| **`Field 'customfield_XXXXX' not found`** | Field ID wrong, not on that issue type's screen, or **differs Cloud↔DC** | `jira_search_fields {"keyword":"story points"}` to get the real ID; verify the field is on the target screen |
| **Issue type not found** | Type absent in project / case mismatch | `jira_get_all_projects` for available types; names are **case-sensitive**; "Epic" may need specific project config |
| **Attachment too large** | > 50 MB inline limit | Access via web UI / compress; the MCP caps inline downloads at 50 MB |

## Rate limiting

**429 Too Many Requests** — Cloud ≈ 100 req/min/user (varies), DC instance-dependent. Fixes: add delays between bulk ops; use **batch tools** (`jira_batch_create_issues`, `jira_batch_get_changelogs`) instead of N single calls; trim available tools with `ENABLED_TOOLS` so the agent does fewer round-trips.

## Debugging

```bash
MCP_VERBOSE=true            # standard verbose
MCP_VERY_VERBOSE=true       # request-level detail (header values masked)
MCP_LOGGING_STDOUT=true     # log to stdout instead of stderr
```
Logs: macOS `~/Library/Logs/Claude/mcp*.log`; Claude Code surfaces MCP server stderr in its logs. Test the config interactively, outside any client, with the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector uvx mcp-atlassian
# local build:
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-atlassian run mcp-atlassian
```

Custom-header format errors are common: `JIRA_CUSTOM_HEADERS=X-Custom=value` — **no surrounding quotes, `=` not `:`, no spaces around `=`**.

## Sources
See `references/sources.md`. Anchor: Troubleshooting doc + the per-tool references for tool-specific limits.
