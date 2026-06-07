# Hardening — scope the tools deliberately

The server exposes **72 tools, most write-capable** (create/update/delete/transition issues, edit pages, etc.). Default-on for everything is rarely what you want for an agent. Three layered controls, plus the v0.22 default change.

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

## The v0.22.0 default change (version gotcha)

Today (≤ v0.21.x), an **unset `TOOLSETS` enables all 72 tools**. **In v0.22.0 the default flips to the 6 core toolsets only.** Consequences:
- An agent relying on `jira_agile`/`jira_links`/etc. without setting `TOOLSETS` will **lose those tools** on upgrade to 0.22.
- To preserve current behavior across the upgrade, set **`TOOLSETS=all` explicitly**.
- **Unknown toolset names are silently ignored**; if *every* name is unknown, **zero tools** are enabled (fail-closed) — a typo in `TOOLSETS` can silently disable the server.

## Recommended baselines

- **Read/report agent:** `READ_ONLY_MODE=true` (+ project filter).
- **Scoped write agent (typical):** `TOOLSETS=default` (+ `jira_agile`/`jira_links` if needed) + `JIRA_PROJECTS_FILTER` + `ENABLED_TOOLS` if you want a tight allow-list.
- **Full access (power use):** `TOOLSETS=all` — pin it now so the 0.22 default flip doesn't surprise you.

## Sources
See `references/sources.md`. Anchors: Tools Reference (toolset tables), Configuration (tool filtering + the v0.22 warning).
