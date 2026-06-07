---
name: jira-cli
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Drive Atlassian Jira from the terminal with the `jira` CLI (jira-cli, v1.7.0) against ANY Jira — Cloud or on-premise/Data Center. Covers the full command surface (issue / epic / sprint / board / project / release), the non-interactive automation contract (`--no-input` + `--plain`/`--raw`/`--csv` for agent-safe, parseable output), JQL filtering, GitHub/Jira markdown → Atlassian Document Format (ADF) conversion, authentication for every backend (Cloud API token, on-prem basic, PAT/bearer, mTLS), and live-discovery of instance-specific values (project keys, issue types, statuses, priorities, link types, custom fields) instead of guessing them.
when_to_use: |-
  Trigger whenever the user wants to create, read, search, edit, transition, assign, comment on, link, clone, or report on Jira issues / epics / sprints / boards / releases FROM THE COMMAND LINE or a script — even when the tool is not named. Fires on "jira-cli", "jira issue list/create/edit/move", "jira sprint", "jira epic", "jira me/init", "transition a ticket from the CLI", "bulk-update Jira", "script Jira", "JQL from the terminal", "export Jira to CSV/JSON", "create a Jira ticket non-interactively", "automate Jira in CI", "the jira command hangs / prompts", "jira 401", "JIRA_API_TOKEN", "JIRA_AUTH_TYPE=bearer", "PAT or mTLS for Jira", "Jira markdown / ADF not rendering" — against Cloud OR Server/Data Center. NOT for the Jira REST API directly, the Jira web UI, or Confluence.
---

# jira-cli — Atlassian Jira from the terminal

Target audience: an operator or agent driving Jira non-interactively — creating and transitioning tickets, running JQL, exporting issues, and scripting bulk changes — against any Jira deployment (Cloud, Server, or Data Center). This skill is **instance-agnostic**: it never assumes the target's project keys, workflows, or field schemes — it shows how to *discover* them and then act safely.

`jira` is [ankitpokhrel/jira-cli](https://github.com/ankitpokhrel/jira-cli), a single static Go binary inspired by GitHub's `gh`. It is **not** an official Atlassian tool.

## Why this matters

Three things make jira-cli easy to get wrong, and all three are what this skill exists to prevent:

1. **It is interactive by default.** `create`, `edit`, `assign`, `move`, `comment add`, and `worklog add` open a TUI or prompt for missing fields. A script (or an agent) that forgets `--no-input` — or omits a required flag — **hangs forever** waiting on a prompt that no one will answer. Reads (`list`, `view`, `epic list`, `sprint list`) default to an interactive pager/table UI; without `--plain`/`--raw`/`--csv` the output is terminal-control gibberish, not parseable data. **The automation contract is non-negotiable: writes get `--no-input` + every required flag; reads get a plain/raw/csv format flag.**

2. **Almost every value is instance-defined and case-sensitive.** Issue types, statuses, priorities, resolutions, link types, components, and custom fields are configured per-project on the Jira side — the CLI invents none of them. `-tBug` fails on a project that calls it `Defect`; `move ISSUE-1 "Done"` fails if the workflow's state is `Closed` or `done` (lowercase). **Discover before acting** (see below). Hardcoding values from memory is the most common cause of confusing failures.

3. **Descriptions/comments are converted to Atlassian Document Format (ADF).** Markdown is not stored verbatim — it's translated. Some constructs (Jira `{code}` blocks, strikethrough, `@mentions`, emoji shortcodes, raw HTML) translate imperfectly or are dropped. See `references/markdown-adf.md`.

## Version & source of truth

- **Pinned at v1.7.0** (released 2025-08-31, the current latest). Verify locally: `jira version`.
- **`--help` is the authoritative flag reference**, always. `jira <cmd> <subcmd> --help` prints flags, arguments, aliases, and examples. If this skill ever disagrees with `--help` on a flag, trust `--help` (and update the skill). Generate full man pages with `jira man --generate --output <dir>`.
- This skill's exhaustive flag/argument tables live in `references/commands.md`, captured from the v1.7.0 binary.

## Cloud vs Server / Data Center — know which backend you're on

The CLI talks to two different Jira APIs and the behavior diverges in ways that change real commands. Check with `jira serverinfo` (`Deployment Type: Cloud` vs `Server`). The command *surface* is identical; these semantics are not:

| Aspect | Jira **Cloud** | Jira **Server / Data Center** |
|---|---|---|
| REST API | v3 | v2 |
| Description/comment format | GFM/Jira markdown → **ADF** (auto-converted) | **Jira wiki markup** — `create`/`comment` convert GFM→wiki, but `edit` sends it **verbatim** (#935); prefer `h2.`, `*bold*`, `{code}` |
| Auth | email + **API token** | **password** (basic), or **PAT** (`JIRA_AUTH_TYPE=bearer`), or **mTLS** |
| User identity for `-a`/`-r` | **accountId** (GDPR strict mode, #342) — email/display name may not resolve | **username** (or display name) |
| `--paginate <from>:` offset | **ignored** — can't page past the first 100 (#898) | **works** — old search API still honors `startAt` |
| SSO in front of the instance | rare | API must be reachable directly with a **PAT**; basic-auth/email hits the SSO HTML login → `401` / `invalid character '<'` (#477, #822) |
| Releases/Versions, sprints | feature-gated | same, plus older Agile API quirks |

When a recipe below assumes Cloud (ADF markdown, accountId, the pagination cap), the Server/DC equivalent is in the right-hand column. Auth/SSO specifics: `references/config-auth.md`. Markdown specifics: `references/markdown-adf.md`.

## Step 0 — ALWAYS discover the instance before acting

A skill that hardcodes project keys or status names is wrong on the next Jira. Before any create/edit/move/assign, learn what the target instance actually offers. These are read-only and safe:

```bash
jira me                                   # confirm auth + identity (prints the account/email)
jira project list                         # KEY NAME TYPE LEAD — tab-separated table, takes no output flags
jira board list                           # ID NAME TYPE — board IDs for sprints (also takes no output flags)
# Discover the field VALUES a project accepts — read them off existing issues:
jira issue list -p PROJ --plain --no-truncate --paginate 5   # see real types/statuses/priorities in use
jira issue view PROJ-123 --raw | jq '.fields | {type:.issuetype.name, status:.status.name, priority:.priority.name, resolution:.resolution.name}'
jira issue view PROJ-123 --raw | jq '.fields | keys'         # custom field IDs (customfield_XXXXX)
```

For transitions specifically, the **valid target states depend on the issue's current status and the project workflow** — there is no global list. The reliable move is: read the issue, see its status, and use the exact target-state string the workflow allows (often surfaced in the Jira UI's transition buttons). When unsure, run `jira issue move <KEY>` interactively *once* to see the offered states, then script the exact string with `--no-input`-style full args. Full discovery recipes: `references/config-auth.md`.

## Command map

| Goal | Command | Notes |
|---|---|---|
| Who am I / is auth working | `jira me`, `jira serverinfo` | `$(jira me)` is the self-reference idiom |
| List/search issues | `jira issue list` (aliases `ls`, `search`) | Filters + JQL; see `references/jql-and-filters.md` |
| View one issue | `jira issue view KEY` | `--comments N`, `--raw` for JSON |
| Create issue | `jira issue create -t<Type> -s"..." --no-input` | `-P` parent (epic link / required for sub-task) |
| Edit issue | `jira issue edit KEY ... --no-input` | `--label` **appends**, `--component` **replaces** (asymmetric!) |
| Transition | `jira issue move KEY "State"` (aliases `transition`, `mv`) | `--comment`/`-a`/`-R` inline; state is workflow-defined |
| Assign | `jira issue assign KEY <user|$(jira me)|default|x>` | `x` = unassign; user must be exact email/display name |
| Comment | `jira issue comment add KEY "body"` | `--internal` for service-desk-internal; markdown→ADF |
| Worklog | `jira issue worklog add KEY "2d 1h 30m" --no-input` | `--started`, `--timezone`, `--new-estimate` |
| Link / unlink | `jira issue link IN OUT <Type>` / `unlink` / `link remote` | `<Type>` is instance-defined (`Blocks`, `Duplicates`, …) |
| Clone | `jira issue clone KEY -H"find:replace"` | copy + tweak fields |
| Delete (permanent) | `jira issue delete KEY [--cascade]` | irreversible; `--cascade` also deletes subtasks |
| Epics | `jira epic list [KEY]` / `create -n"Name"` / `add` / `remove` | `create` needs `-n/--name`; `add`/`remove` ≤50 at once |
| Sprints | `jira sprint list [ID]` / `add` / `close` | `--current`/`--prev`/`--next`/`--state`; get IDs from `--table` |
| Releases (versions) | `jira release list [-p PROJ]` | requires Releases/Versions enabled on the instance |
| Open in browser | `jira open [KEY]` | `--no-browser` prints the URL instead |
| Projects / boards | `jira project list`, `jira board list` | discovery |

Full flag tables, arguments, and aliases for every command: **`references/commands.md`**.

## The automation contract (read this before scripting)

Output flags (reads) — bare `list`/`view` open an interactive UI, so any piping needs one of:

- `--plain` (+ `--no-headers`, `--no-truncate`, `--columns key,summary,status`, `--delimiter "|"`) — tabular text; column names come from `--help`.
- `--raw` — Jira REST JSON (parse with `jq`; shape `.[].fields.*`).
- `--csv` — CSV with headers.
- `--paginate <limit>` — cap result count (max 100). **Jira Cloud, v1.7.0: the `<from>:` offset is silently ignored** — Atlassian's new JQL search API dropped `startAt`, so there is **no way to page past the first 100 issues** (#898). Narrow with JQL/filters instead. Server/Data Center (older API) still honors `<from>:<limit>`.

Write flags:

- `--no-input` — **the load-bearing flag.** Disables prompting for non-required fields. Pair with every required flag so the command runs unattended.
- `--web` — open the result in a browser after the write (skip in headless/CI).

Idioms:

```bash
# Self-reference
ME=$(jira me)

# Create → capture key → act on it
KEY=$(jira issue create -tTask -s"Automated task" --no-input --raw | jq -r '.key')
jira issue assign "$KEY" "$ME"
jira issue move "$KEY" "In Progress"

# Bulk: list keys, then loop
for k in $(jira issue list -q'assignee = currentUser() AND status = "To Do"' --plain --columns key --no-headers); do
  jira issue move "$k" "In Progress" --comment "Picking up"
done
```

More patterns (CSV/JSON pipelines, dashboards, safe bulk edits): **`references/scripting.md`**.

## Critical pitfalls

1. **Forgetting `--no-input` on a write hangs the process.** In a non-interactive context (CI, agent, `&&` chain) this looks like the command "froze". Every `create`/`edit`/`assign`/`move`/`comment add`/`worklog add` in a script needs `--no-input` plus all required positional/flag values. **Known bug:** even with `--no-input`, the body-reading writes (`create`, `edit`, `comment add`, `epic create`) can still block on stdin when it's a socket/subprocess pipe — jira-cli treats "stdin is not a TTY" as "read the body from stdin" and waits for EOF (#948/#984). Append `</dev/null` when shelling out from an agent.

2. **Guessing field values.** `-tBug`, `-sDone`, `-yHigh`, `link ... Blocks` all reference *instance-defined, case-sensitive* strings. Run Step-0 discovery first. A failed write with "specify a valid issue type" / "field cannot be set" almost always means the value doesn't exist on that project.

3. **`edit` append-vs-replace asymmetry.** `--label` and `--fix-version` **append/add**; `--component` **replaces**. Remove an existing value by prefixing minus: `jira issue edit KEY --label -stale --label fresh --component -OldComp --component NewComp --no-input`. Expecting `--label new` to *replace* the label set is a classic mistake — it only adds.

4. **`-b/--body` and the positional comment body beat `--template`.** If both are passed, the flag/positional wins and the template is silently ignored. Use one or the other.

5. **Epic creation quirks.** `jira epic create -n"Epic name" -s"Summary" [-b"body"] --no-input` works non-interactively on **both** classic and next-gen. Two gotchas: **`-n/--name` is required even on next-gen** (where its value is then ignored — the mandatory check still demands it), and `epic create` has **no `--raw`** flag (it prints `Epic created\n<url>`). To capture the new key as JSON, use `jira issue create -tEpic -s"…" --no-input --raw` instead (Epic is an issue type), then attach children with `-P/--parent EPIC-KEY` (the flag is "parent" because next-gen reuses the parent relationship). The `? Epic Key` prompt comes from `epic add` when its `EPIC-KEY` arg is missing — not from create.

6. **Sub-tasks require `-P/--parent`,** and the parent must be a type that allows sub-tasks. "Given parent work item does not belong to appropriate hierarchy" means `-P` points at something (e.g. an epic, or another sub-task) that can't hold sub-tasks.

7. **`delete` is irreversible and `--cascade` deletes subtasks too.** Never run it speculatively on someone's behalf — confirm the key and intent first. There is no undo.

8. **Markdown → ADF is lossy.** Prefer GitHub fenced code blocks (```` ``` ````) over Jira `{code}` (which can leak escape characters). `~~strike~~` renders as `-text-`; `@user` mentions need Jira's `[~accountid]` form; emoji shortcodes (`:rocket:`) and raw HTML are dropped. For anything structured, use `--template file.md` and test on one issue first. Details: `references/markdown-adf.md`.

9. **Assignee/watcher must match exactly.** Pass an exact email or display name. On many Jira Cloud instances, GDPR strict mode means assignment resolves by accountId — if `assign KEY "Jane Doe"` fails, try the email, or look up the accountId via `jira issue view ... --raw`. `x` unassigns; `default` uses the project's default assignee.

10. **`-q/--jql` runs *within the configured project's context*.** To query across all projects, add a project clause yourself: `-q'project IS NOT EMPTY'` or name projects in the JQL. Plain filter flags (`-s`, `-y`, `-l`, …) and a `-q` JQL can combine.

11. **Auth is via the `JIRA_API_TOKEN` environment variable, not the config file.** The token never lives in `.config.yml`. Cloud wants an **API token** (not the account password); on-prem basic wants the **password**; PAT wants the token **plus** `JIRA_AUTH_TYPE=bearer`. A 401 is nearly always a missing/wrong `JIRA_API_TOKEN` or the wrong auth type. See `references/config-auth.md`.

12. **Cloud vs Server/Data Center differ.** Some features and `--raw` JSON fields vary by backend; non-English on-prem instances may need manual `epic.name`/`epic.link`/`issue.types.*.handle` entries in the config. Don't assume Cloud behavior on Server.

## What to read next

| File | Read when… |
|---|---|
| `references/commands.md` | Looking up exact flags, arguments, aliases for any command. Full v1.7.0 surface. |
| `references/jql-and-filters.md` | Building a `list`/`epic list`/`sprint list` query — filter flags, the date syntax (`week`, `-7d`, `2025-09-15`), `~` negation, `x` unassigned, JQL examples. |
| `references/markdown-adf.md` | Writing a description/comment with formatting — GFM vs Jira markup, ADF conversion limits, templates, here-docs, `$'...'` newlines. |
| `references/scripting.md` | Automating — non-interactive recipes, `--raw`+`jq` and `--csv` pipelines, safe bulk edits, capturing created keys, dashboards. |
| `references/config-auth.md` | First-time setup, multi-instance configs, every auth type (Cloud/basic/PAT/mTLS), env vars, and the full instance-discovery recipes. |
| `references/troubleshooting.md` | A specific error or symptom — hangs, 401s, "valid issue type", parent-hierarchy errors, empty output, pager weirdness. |
| `references/known-issues.md` | Tracking an upstream bug the skill works around — `(#NNN)` tags in the body map to this table (status, what it affects). |
| `references/sources.md` | Verifying or freshening external claims; per-row `Last verified` dates. |

## Quick recipes

```bash
# Smoke test: am I connected and what can I see?
jira me && jira project list

# List my open issues, parseable
jira issue list -q'assignee = currentUser() AND statusCategory != Done' \
  --plain --no-headers --columns key,status,summary

# Create a bug, non-interactively, and print its key
jira issue create -tBug -s"Login 500 on submit" -yHigh -lregression \
  -b$'## Steps\n1. ...\n\n## Expected\n...' --no-input --raw | jq -r '.key'

# Transition with a comment and resolution
jira issue move PROJ-42 "Done" -RFixed --comment "Shipped in 1.2.3"

# Export everything in a project to CSV
jira issue list -p PROJ --csv --paginate 0:100 > issues.csv

# Add a sub-task under a story
jira issue create -t"Sub-task" -P PROJ-100 -s"Write tests" --no-input
```

For anything beyond these, drill into the `references/` files — they carry the exhaustive flag tables, JQL grammar, ADF rules, and auth matrix.
