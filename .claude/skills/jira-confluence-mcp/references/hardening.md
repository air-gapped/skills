# Hardening — scope the tools deliberately

The server exposes **70+ tools, most write-capable** (72 as measured at v0.21.1; v0.22.0 and v0.23.0 each added a batch — treat 72 as a floor and read the live list, which is authoritative) (create/update/delete/transition issues, edit pages, etc.). Default-on for everything is rarely what you want for an agent. Three layered controls, plus the v0.22 default change.

## 1. Read-only mode (the blunt, safe default)

```bash
READ_ONLY_MODE=true
```
Disables **all write operations regardless of `ENABLED_TOOLS`/`TOOLSETS`**. Use for reporting/analysis agents, demos, or any context where the agent should never mutate Jira/Confluence. A 403 on a write while this is set is expected, not a bug.

## 2. Toolsets (group-level)

`TOOLSETS` enables whole groups. `TOOLSETS=default` ≈ 23 core tools across 6 core toolsets; add extras comma-separated; `TOOLSETS=all` = all 72.

```bash
TOOLSETS=default,jira_agile,jira_attachments     # core + two extras
TOOLSETS=all                                     # everything (current implicit default)
```

**Jira toolsets (15)** — `core` marked ✔:
| Toolset | Core | Representative tools |
|---|:--:|---|
| `jira_issues` | ✔ | get/search/create/update/delete/batch-create issues, batch changelogs |
| `jira_fields` | ✔ | `jira_search_fields`, `jira_get_field_options` |
| `jira_comments` | ✔ | add/edit comment |
| `jira_transitions` | ✔ | `jira_get_transitions`, `jira_transition_issue` |
| `jira_projects` | | projects, versions, components, create version |
| `jira_agile` | | boards, sprints, board/sprint issues, create/update sprint |
| `jira_links` | | link types, link-to-epic, issue links, remote links |
| `jira_worklog` | | get/add worklog |
| `jira_attachments` | | download attachments, render images |
| `jira_users` | | user profile |
| `jira_watchers` | | get/add/remove watchers |
| `jira_service_desk` | | service-desk queues + queue issues |
| `jira_forms` | | ProForma forms (Cloud-only) |
| `jira_metrics` | | issue dates, SLA |
| `jira_development` | | development info (commits/PRs) |

**Confluence toolsets (6)** — core: `confluence_pages`, `confluence_comments`. Extras: `confluence_labels`, `confluence_users`, `confluence_analytics` (Cloud-only page views), `confluence_attachments`.

## 3. Enabled-tools (individual allow-list)

```bash
ENABLED_TOOLS="jira_search,jira_get_issue,jira_get_transitions,jira_transition_issue"
```
When **both** `TOOLSETS` and `ENABLED_TOOLS` are set they **intersect** — a tool must pass both. Command-line equivalents: `--toolsets`, `--enabled-tools`.

## 4. Scope filters (blast radius)

`JIRA_PROJECTS_FILTER=PROJ,DEV` and `CONFLUENCE_SPACES_FILTER=DEV,DOC` restrict which projects/spaces the tools touch — orthogonal to tool filtering, and worth setting so an agent can't wander the whole instance.

## The v0.22.0 default change — **SHIPPED 2026-07-10**

**This is no longer a forecast.** v0.22.0 released 2026-07-10 (v0.22.1 the next
day, v0.23.0 on 2026-07-18). If the server has been upgraded past v0.21.x, the
flip has already happened.

Previously (≤ v0.21.x), an **unset `TOOLSETS` enabled all tools**. **From v0.22.0 the default is the 6 core toolsets only.** Consequences:
- An agent relying on `jira_agile`/`jira_links`/etc. without setting `TOOLSETS` will **lose those tools** on upgrade to 0.22.
- To preserve current behavior across the upgrade, set **`TOOLSETS=all` explicitly**.
- **Unknown toolset names are silently ignored**; if *every* name is unknown, **zero tools** are enabled (fail-closed) — a typo in `TOOLSETS` can silently disable the server.

## Recommended baselines

- **Read/report agent:** `READ_ONLY_MODE=true` (+ project filter).
- **Scoped write agent (typical):** `TOOLSETS=default` (+ `jira_agile`/`jira_links` if needed) + `JIRA_PROJECTS_FILTER` + `ENABLED_TOOLS` if you want a tight allow-list.
- **Full access (power use):** `TOOLSETS=all` — required from v0.22.0 onward, not merely advisable.

## ⚠ v0.22.0 security hardening — two changes that alter behaviour

v0.22.0 resolved a **37-advisory security audit**. Two items matter operationally
even if you never read a CVE:

**1. Unauthenticated HTTP transport no longer borrows the operator's credentials
(critical).** Before v0.22.0, an unauthenticated `streamable-http` request **fell
back to the server's own global credentials** — i.e. anyone who could reach the
transport acted as the operator. From v0.22.0 such requests are **rejected with
401**, and the old behaviour is opt-in via **`ALLOW_GLOBAL_CRED_FALLBACK`
(default off)**.

- If you run **stdio only** (the default for `claude mcp add`), you were never
  exposed — there is no listening transport.
- If you run **streamable-http**, treat any pre-0.22 deployment that was
  network-reachable as having had an **unauthenticated credential-proxy hole**,
  and do not re-enable `ALLOW_GLOBAL_CRED_FALLBACK` to "fix" a 401 after
  upgrading — that restores the vulnerability.

**2. Attachment/content paths are now confined to the working directory.**
`upload_attachment` / `download_attachment` (Jira and Confluence) and the new
`content_file` page input validate every caller-supplied path via
`validate_safe_path`. **Paths must now resolve inside the server's working
directory** — this closes arbitrary-file-read/exfiltration and an intra-CWD
overwrite RCE variant, and it **breaks workflows that passed absolute paths**.
v0.22.0 also adds **`content_base64`** for `upload_attachment` precisely for the
case where the server cannot read host file paths (#1366) — that is the intended
replacement, not a path workaround.

## Sources
See `references/sources.md`. Anchors: Tools Reference (toolset tables), Configuration (tool filtering + the v0.22 warning).
