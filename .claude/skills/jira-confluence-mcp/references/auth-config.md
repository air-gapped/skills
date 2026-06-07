# Authentication & configuration

Auth methods (Cloud vs Data Center) and the full environment-variable catalog. mcp-atlassian reads config from env vars (or the IDE's `env` block / `claude mcp add -e`).

## Auth methods

| Method | Cloud | Server / Data Center | Env vars |
|---|---|---|---|
| **API token** (username + token) | ✅ | ✅ (username + **password**) | `JIRA_USERNAME` + `JIRA_API_TOKEN` |
| **Personal Access Token (PAT)** | ❌ | ✅ **(use this on DC)** | `JIRA_PERSONAL_TOKEN` (no username) |
| **OAuth 2.0** | ✅ 3LO | ✅ Application Links | see OAuth below |
| **BYOT** (bring your own token) | ✅ | ✅ | `ATLASSIAN_OAUTH_CLOUD_ID` + `ATLASSIAN_OAUTH_ACCESS_TOKEN` |

Confluence mirrors every Jira var (`CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`, `CONFLUENCE_PERSONAL_TOKEN`, `CONFLUENCE_SSL_VERIFY`) — each product is a **separate client gated on its own vars**. Supply only one service's vars and only that service's tools register; the other product's tools simply don't appear (no error). On **Cloud the same email + API token authorise both products** (Atlassian Cloud tokens are account-scoped), so **reuse the Jira values — only the URL differs: `CONFLUENCE_URL` ends `/wiki`** (`https://<site>.atlassian.net/wiki`) where `JIRA_URL` is the bare domain. On DC, Confluence uses its own host/context path + `CONFLUENCE_PERSONAL_TOKEN`.

### Cloud — API token (simplest)
Create at `id.atlassian.com/manage-profile/security/api-tokens`. `JIRA_USERNAME` is your **email**.
```bash
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=you@company.com
JIRA_API_TOKEN=<token>
```

### Data Center — PAT (the default for this skill)
Profile (avatar) → **Personal Access Tokens** → Create token, set expiry. **Max 10 PATs per user.**
```bash
JIRA_URL=https://jira.internal.company.com
JIRA_PERSONAL_TOKEN=<pat>
JIRA_SSL_VERIFY=false   # only if the internal CA isn't trusted; prefer mounting the CA
```
For older Confluence servers that reject PATs, fall back to basic auth: `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` where the "token" is the account password.

### OAuth 2.0 (Cloud, advanced)
For most users API token is simpler. Setup wizard: `uvx mcp-atlassian --oauth-setup -v` (or the Docker equivalent with `-p 8080:8080 -v ${HOME}/.mcp-atlassian:/home/app/.mcp-atlassian`). Callback `http://localhost:8080/callback`. After setup:
```bash
ATLASSIAN_OAUTH_CLOUD_ID=...
ATLASSIAN_OAUTH_CLIENT_ID=...
ATLASSIAN_OAUTH_CLIENT_SECRET=...
ATLASSIAN_OAUTH_REDIRECT_URI=http://localhost:8080/callback
ATLASSIAN_OAUTH_SCOPE=read:jira-work write:jira-work read:confluence-content.all write:confluence-content offline_access
```
Include `offline_access` for refresh-token rotation. **Multi-cloud** (users supply their own tokens): `ATLASSIAN_OAUTH_ENABLE=true` + HTTP transport, then per-request `Authorization: Bearer <token>` + `X-Atlassian-Cloud-Id` headers. **OAuth proxy / DCR** (remote endpoint onboarding MCP clients): `ATLASSIAN_OAUTH_PROXY_ENABLE=true` + `PUBLIC_BASE_URL` + allowed-redirect/grant vars.

## Environment-variable catalog

### Connection
| Var | Purpose |
|---|---|
| `JIRA_URL` / `CONFLUENCE_URL` | Instance URL (Confluence URL ends `/wiki` on Cloud) |
| `JIRA_USERNAME` / `CONFLUENCE_USERNAME` | Username (email on Cloud) |
| `JIRA_API_TOKEN` / `CONFLUENCE_API_TOKEN` | Cloud API token |
| `JIRA_PERSONAL_TOKEN` / `CONFLUENCE_PERSONAL_TOKEN` | DC/Server PAT |
| `JIRA_SSL_VERIFY` / `CONFLUENCE_SSL_VERIFY` | `true`/`false` TLS verification |
| `MCP_ATLASSIAN_USE_SYSTEM_TRUSTSTORE` | Use OS trust store (default `true`); `false` = bundled certifi |
| `JIRA_CLIENT_CERT` / `JIRA_CLIENT_KEY` | mTLS client cert/key |
| `JIRA_TIMEOUT` / `CONFLUENCE_TIMEOUT` | Request timeout (default 75s) — raise for slow instances |

### Filtering & scope (see `references/hardening.md`)
| Var | Purpose | Example |
|---|---|---|
| `JIRA_PROJECTS_FILTER` | Limit to projects | `PROJ,DEV,SUPPORT` |
| `CONFLUENCE_SPACES_FILTER` | Limit to spaces | `DEV,TEAM,DOC` |
| `ENABLED_TOOLS` | Allow-list individual tools | `jira_search,jira_get_issue` |
| `TOOLSETS` | Enable tool groups | `default,jira_agile` / `all` |
| `READ_ONLY_MODE` | Disable all writes | `true` |

### Server / transport
| Var | Purpose |
|---|---|
| `TRANSPORT` | `stdio` (default for Claude Code) / `sse` / `streamable-http` |
| `STATELESS` | Stateless streamable-http (`true`/`false`) |
| `PORT` / `HOST` | HTTP transport bind (default `8000` / `0.0.0.0`) |
| `MCP_VERBOSE` / `MCP_VERY_VERBOSE` | Logging verbosity |
| `MCP_LOGGING_STDOUT` | Log to stdout instead of stderr |
| `IGNORE_HEADER_AUTH` | Ignore proxy-injected auth headers (GCP Cloud Run / AWS ALB) |

### Proxy & custom headers
`HTTP_PROXY` / `HTTPS_PROXY` / `SOCKS_PROXY` / `NO_PROXY` (global); `JIRA_HTTPS_PROXY` / `CONFLUENCE_HTTPS_PROXY` (service-specific, override global). Custom headers: `JIRA_CUSTOM_HEADERS` / `CONFLUENCE_CUSTOM_HEADERS` as comma-separated `key=value` (no quotes, `=` not `:`, no spaces): `X-Forwarded-User=svc,X-ALB-Token=secret`.

Full list: the repo's [.env.example](https://github.com/sooperset/mcp-atlassian/blob/main/.env.example).

## Transport for Claude Code
Default is **stdio** — the server is launched as a subprocess (`uvx mcp-atlassian` or `docker run -i …`). HTTP transports (`sse`, `streamable-http`) are for remote/multi-user deployments; see the upstream HTTP Transport guide. For a single developer on Claude Code, stdio is correct.

## Sources
See `references/sources.md`. Anchors: Authentication, Configuration, Compatibility docs.
