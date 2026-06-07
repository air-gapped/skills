---
name: jira-confluence-mcp
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Install, configure, secure, and troubleshoot the mcp-atlassian MCP server (sooperset/mcp-atlassian) that connects an agent to Jira/Confluence — including AIR-GAPPED setup (mirror the prebuilt image by digest; no PyPI/git mirror) and internal-CA / TLS handling (mount the CA vs JIRA_SSL_VERIFY=false). Self-hosted Data Center first: the #1 gotcha is DC uses JIRA_PERSONAL_TOKEN (a PAT), NOT the Cloud username+API-token pattern. Covers `claude mcp add`, the env-var catalog, hardening (READ_ONLY_MODE, TOOLSETS/ENABLED_TOOLS, project filters, the v0.22 default-toolset change), Cloud-vs-DC tool/format divergence, and 401/403/field/rate-limit/SSL fixes. NOT a catalogue of the 72 tools — those self-document at runtime; this is the setup/ops knowledge invisible at call time.
when_to_use: |-
  Use whenever the user wants to install, configure, secure, deploy, or debug the mcp-atlassian / "jira MCP" / "confluence MCP" / "atlassian MCP" server. Fires on "install mcp-atlassian", "set up the jira/confluence MCP", "claude mcp add atlassian", "mcp-atlassian air-gapped", "JIRA/CONFLUENCE_PERSONAL_TOKEN", "JIRA/CONFLUENCE_SSL_VERIFY", "mcp-atlassian 401/403", "mcp read-only mode", "TOOLSETS/ENABLED_TOOLS / CONFLUENCE_SPACES_FILTER", "limit which MCP tools", "atlassian MCP rate limit / field not found", "OAuth for atlassian MCP". NOT for USING the tools once connected (the live MCP self-documents its 72 tools), the `jira` CLI (→ jira-cli), or Jira/Confluence usage (→ jira-best-practices / confluence-best-practices).
---

# jira-confluence-mcp — install, secure & operate the mcp-atlassian MCP server

Scope: getting **[sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)** — the MCP server that gives an agent Jira/Confluence tools — *connected, hardened, and debugged*, including **air-gapped**. This is the **setup/ops layer**: the knowledge that is invisible at tool-call time.

**Hard boundary — what this skill does NOT do.** Once the server is connected, it **self-documents its 72 tools at runtime** (names, params, schemas) over the MCP protocol — so *using* the tools (`jira_search`, `jira_create_issue`, `jira_transition_issue`, …) needs no skill; just call them. For exhaustive tool/JQL/CQL docs, the project publishes an LLM-readable **`https://mcp-atlassian.soomiles.com/llms-full.txt`** — fetch it on demand instead of duplicating it here. Sibling skills: **`jira-cli`** (the `jira` CLI as an alternative execution path) and **`jira-best-practices`** (how to use Jira *well* — hierarchy, lean config). This skill is only the install/auth/hardening/air-gap/troubleshooting that those don't cover and the live MCP can't surface.

**Self-hosted Data Center is the default here.** Where Cloud differs, it's flagged.

## The #1 gotcha: Data Center auth is a PAT, not username+token

Claude's base instinct is the Cloud pattern — and it **fails on Data Center**.

| Deployment | Required env vars |
|---|---|
| **Data Center / Server** | `JIRA_URL` + **`JIRA_PERSONAL_TOKEN`** (a Personal Access Token). *No username.* |
| Cloud | `JIRA_URL` + `JIRA_USERNAME` (email) + `JIRA_API_TOKEN` |

DC PATs: created at profile → **Personal Access Tokens**; **max 10 per user**; set an expiry. Full auth matrix (OAuth 2.0, BYOT, multi-cloud) + the complete env-var catalog: **`references/auth-config.md`**.

## Enable Jira, Confluence, or both (the #1 setup miss)

mcp-atlassian runs a **separate client per product**, each gated on its own `*_URL` + auth. **Supply only `JIRA_*` and you get only `jira_*` tools** — Jira's vars do *not* carry over to Confluence (and vice-versa), and the missing product's tools just **don't appear, with no error**. To add Confluence:

| | Cloud | Data Center |
|---|---|---|
| URL | `CONFLUENCE_URL=https://<site>.atlassian.net/wiki` — **note the `/wiki`** (Jira is the bare domain) | its own host / context path, e.g. `https://confluence.internal.company.com` |
| Auth | `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` — **the same email + token as Jira** (Cloud API tokens are account-scoped; reuse the Jira values) | `CONFLUENCE_PERSONAL_TOKEN` (a PAT, like Jira) |

`TOOLSETS=all`/`default` already covers both products, so **missing tools mean missing creds, not a toolset problem.** After any env change, **reconnect** (`/mcp` → reconnect, or restart — env is read only at spawn) and verify with `claude mcp list` + the tool count. Symptom row: `references/troubleshooting.md`.

## Install & connect (Claude Code)

`uvx` is the runner for a connected host; **Docker/image** is the path for production and air-gap. Add it to Claude Code with `claude mcp add` (the upstream docs only show Claude-Desktop/Cursor JSON):

```bash
# Data Center, Jira only (add CONFLUENCE_URL + CONFLUENCE_PERSONAL_TOKEN for Confluence too):
claude mcp add mcp-atlassian \
  -e JIRA_URL=https://jira.internal.company.com \
  -e JIRA_PERSONAL_TOKEN=<pat> \
  -- uvx mcp-atlassian

# Cloud, BOTH products — same email + token; Confluence URL ends /wiki:
claude mcp add mcp-atlassian \
  -e JIRA_URL=https://your-co.atlassian.net -e CONFLUENCE_URL=https://your-co.atlassian.net/wiki \
  -e JIRA_USERNAME=you@co.com -e CONFLUENCE_USERNAME=you@co.com \
  -e JIRA_API_TOKEN=<token> -e CONFLUENCE_API_TOKEN=<token> \
  -- uvx mcp-atlassian
```

Other install methods (pip, uv, source) exist but pull from PyPI — see `references/air-gapped.md` for why that matters offline.

## TLS / internal CA — add the CA *or* disable verification

Self-hosted Jira usually presents an **internal-CA or self-signed cert**. mcp-atlassian trusts the **OS trust store** by default (via `truststore`), so a CA already in the host's Windows/macOS/Linux store works with no config. Two fixes when it doesn't (e.g. inside a container, which only has the stock bundle):

- **Preferred — trust the CA** (keeps TLS verification on):
  - *uvx / host install:* put the internal CA in the OS trust store (`update-ca-certificates` on Linux), or point at a bundle with `REQUESTS_CA_BUNDLE=/path/ca.pem` / `SSL_CERT_FILE=/path/ca.pem`.
  - *Docker:* mount the CA in and refresh the bundle — `-v /etc/pki/internal-ca.crt:/usr/local/share/ca-certificates/internal-ca.crt:ro` (Alpine image: the cert dir is `/usr/local/share/ca-certificates/`; the bundled `python:3.13-alpine` won't have the internal CA otherwise).
  - mTLS: `JIRA_CLIENT_CERT=/path/cert.pem` + `JIRA_CLIENT_KEY=/path/key.pem`.
- **Escape hatch — skip verification** (only when trusting the CA isn't practical):
  - `JIRA_SSL_VERIFY=false` (and `CONFLUENCE_SSL_VERIFY=false`). Disables cert checking for that service. Acceptable on a trusted internal network; flag it as a deliberate downgrade.
  - To fall back to the bundled `certifi` CA instead of the OS store: `MCP_ATLASSIAN_USE_SYSTEM_TRUSTSTORE=false`.

The container-CA step is the **most common air-gap surprise** — a self-contained image still doesn't trust the *internal* CA. Full detail in `references/air-gapped.md`.

## Air-gapped install (short version)

**A full git mirror of the repo is NOT enough** — the dependency wheels live on PyPI, not in git. If the environment can **serve container images**, the clean path is to **mirror the prebuilt image by digest** (it bakes Python + all deps in — no PyPI, no git needed at install or run):

```bash
# 1. resolve + mirror the prebuilt image, pinned by digest (supply-chain hygiene)
skopeo copy --all \
  docker://ghcr.io/sooperset/mcp-atlassian:v0.21.1 \
  docker://harbor.internal/mirror/mcp-atlassian:v0.21.1
# 2. connect (stdio needs -i); mount the internal CA so TLS verifies
claude mcp add mcp-atlassian \
  -e JIRA_URL=https://jira.internal.company.com \
  -e JIRA_PERSONAL_TOKEN=<pat> \
  -- docker run -i --rm -e JIRA_URL -e JIRA_PERSONAL_TOKEN \
       -v /etc/pki/internal-ca.crt:/usr/local/share/ca-certificates/internal-ca.crt:ro \
       harbor.internal/mirror/mcp-atlassian@sha256:<digest>
```

Critical nuance: **mirror the *prebuilt* image** (no PyPI). *Building* the image from a git mirror still needs a PyPI index for `uv sync` plus the two base images mirrored. The 3-artifact-type breakdown, the build-from-source path, and digest-pinning are in **`references/air-gapped.md`**.

## Hardening (do this by default)

The server exposes **72 write-capable tools**; scope it deliberately.

- **`READ_ONLY_MODE=true`** — disables *all* write tools regardless of other settings. Use for read/report-only agents.
- **`TOOLSETS`** — group-level control (15 Jira + 6 Confluence toolsets). `TOOLSETS=default` ≈ 23 core tools; add extras like `default,jira_agile`. **`ENABLED_TOOLS`** allow-lists individual tools; the two **intersect**.
- **`JIRA_PROJECTS_FILTER` / `CONFLUENCE_SPACES_FILTER`** — limit blast radius to named projects/spaces.
- **Version gotcha:** in **v0.22.0 the default flips from all-72-tools → 6 core toolsets only**. To keep current behavior set `TOOLSETS=all` explicitly; unknown toolset names are silently ignored (all-unknown = fail-closed, zero tools).

Toolset tables + the read-only/filter mechanics: **`references/hardening.md`**.

## Cloud vs Data Center divergence (so advice doesn't mislead)

| Aspect | Cloud | Data Center |
|---|---|---|
| Auth | username + API token / OAuth 3LO | **PAT** (`JIRA_PERSONAL_TOKEN`) / Application-Links OAuth |
| Content format | ADF | **wiki markup** (both auto-converted from Markdown by the tools) |
| User identifiers | `accountId` | `username` / `userKey` |
| Tools unavailable on DC | — | `jira_batch_get_changelogs`, proforma forms, `confluence_get_page_views` (Cloud-only APIs) |
| Custom field IDs | per-instance | per-instance — **differ from Cloud**; discover via `jira_search_fields` |
| Rate limit | ~100 req/min | instance-dependent |

## Troubleshooting (pointer)

401 (PAT vs token), 403 (perms / `READ_ONLY_MODE` blocking writes), `customfield_XXXXX not found` (→ `jira_search_fields`), 429 (→ batch tools / `ENABLED_TOOLS`), SSL, timeouts, and verbose-logging/`MCP Inspector` debugging: **`references/troubleshooting.md`**.

## What to read next

| File | Read when… |
|---|---|
| `references/air-gapped.md` | Installing offline — the 3 artifact types, prebuilt-image mirror, build-from-source caveats, digest pinning, in-container CA |
| `references/auth-config.md` | Choosing/setting auth (DC PAT, Cloud token, OAuth, BYOT, multi-cloud) + the full env-var catalog (SSL, proxy, headers, timeouts) |
| `references/hardening.md` | Restricting tools — `READ_ONLY_MODE`, the 15+6 toolset tables, `ENABLED_TOOLS`, project/space filters, the v0.22 default change |
| `references/troubleshooting.md` | A specific failure — 401/403, field-not-found, rate limits, SSL, timeouts, debug logging, MCP Inspector |
| `references/sources.md` | Verifying/freshening a claim — per-row source + tier + verify date |

For tool usage and exhaustive references, go to the **live MCP** (tool schemas at runtime) and **`llms-full.txt`** — not this skill.
