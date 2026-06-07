# jira-cli command reference (v1.7.0)

Authoritative flag/argument tables, captured from the v1.7.0 binary's `--help`. When in doubt, run `jira <cmd> <subcmd> --help` — it is always correct for the installed build. Global/inherited flags below apply to **every** command.

## Table of contents
- [Global flags & env vars](#global-flags--env-vars)
- [Top-level commands](#top-level-commands)
- [issue list](#issue-list)
- [issue create](#issue-create)
- [issue edit](#issue-edit)
- [issue view](#issue-view)
- [issue assign](#issue-assign)
- [issue move (transition)](#issue-move-transition)
- [issue comment add](#issue-comment-add)
- [issue worklog add](#issue-worklog-add)
- [issue link / unlink / link remote](#issue-link--unlink--link-remote)
- [issue clone](#issue-clone)
- [issue delete](#issue-delete)
- [issue watch](#issue-watch)
- [epic](#epic)
- [sprint](#sprint)
- [release](#release)
- [project / board / open](#project--board--open)
- [init / me / serverinfo / completion / man / version](#init--me--serverinfo--completion--man--version)

## Global flags & env vars

Inherited by every command:

| Flag | Meaning |
|---|---|
| `-c, --config <file>` | Config file. Default `~/.config/.jira/.config.yml`; override with `JIRA_CONFIG_FILE`. |
| `-p, --project <KEY>` | Project to operate in. Defaults to the project in the config file. |
| `--debug` | Verbose debug output (HTTP traces etc.). Add this to diagnose anything. |
| `-h, --help` | Help for the command. |

Environment variables:

| Var | Purpose |
|---|---|
| `JIRA_API_TOKEN` | **Required.** Cloud → API token; on-prem basic → password; PAT → the token. Never stored in the config file. |
| `JIRA_AUTH_TYPE` | Set to `bearer` for PAT (Personal Access Token) auth. Unset/`basic` otherwise. |
| `JIRA_CONFIG_FILE` | Path to an alternate config (multi-instance). Same as `-c`. |

`~/.netrc` and OS keychain are also supported token sources — see `config-auth.md`.

## Top-level commands

```
board       Manage Jira boards in a project
epic        Manage epics in a project
issue       Manage issues in a project   (alias: issues)
open        Open issue/project in a browser
project     Manage Jira projects
release     Manage Jira project versions (releases)
sprint      Manage sprints in a project board
completion  Shell completion (bash/zsh)
init        Initialize jira config
man         Generate man(7) pages
me          Display configured Jira user
serverinfo  Display Jira instance info
version     Print CLI version
```

## issue list
Aliases: `lists`, `ls`, `search`. Positional `[text]` = free-text search (same as the UI search box).

Filter flags:

| Flag | Meaning |
|---|---|
| `-t, --type <T>` | Issue type (instance-defined, e.g. `Bug`, `Story`). |
| `-R, --resolution <R>` | Resolution (e.g. `Fixed`, `Won't Do`). |
| `-s, --status <S>` | Status; repeatable (`stringArray`). |
| `-y, --priority <P>` | Priority. |
| `-r, --reporter <email|name>` | Reporter. |
| `-a, --assignee <email|name>` | Assignee. `x` = unassigned (with `~` negation idioms). |
| `-C, --component <C>` | Component. |
| `-l, --label <L>` | Label; repeatable. |
| `-P, --parent <KEY>` | Filter by parent. |
| `--history` | Issues you accessed recently. |
| `-w, --watching` | Issues you watch. |
| `--created <D>` / `--updated <D>` | Date filter. Accepts `today\|week\|month\|year`, `yyyy-mm-dd`, `yyyy/mm/dd`, or a period `-7d`/`-3w`/`-2h`/`-30m`. Takes precedence over the `-after`/`-before` pair. |
| `--created-after` / `--created-before` / `--updated-after` / `--updated-before` | Bounded date filters. |
| `-q, --jql <JQL>` | Raw JQL, run in the project context. Combines with the flags above. |
| `--order-by <field>` | Sort field (default `created`). |
| `--reverse` | Reverse order (default sort is DESC). |
| `--paginate <from>:<limit>` | Caps results (max 100). **Cloud v1.7.0: `<from>:` offset is ignored** (new JQL API dropped `startAt`) — can't page past the first 100; use `--paginate <limit>` for the cap and JQL to narrow. Server/DC still honors the offset. (#898) |

Output flags: `--plain`, `--no-headers`, `--no-truncate`, `--delimiter "<str>"`, `--raw`, `--csv`, `--columns <list>`, `--fixed-columns <n>`, `--comments <n>`.

`--columns` accepts: `TYPE, KEY, SUMMARY, STATUS, ASSIGNEE, REPORTER, PRIORITY, RESOLUTION, CREATED, UPDATED, LABELS`.

## issue create
Output: `--raw` prints the created issue as JSON (use `jq -r '.key'`).

| Flag | Meaning |
|---|---|
| `-t, --type <T>` | Issue type (required in practice). |
| `-P, --parent <KEY>` | Parent — attaches an epic to the issue; **mandatory for a sub-task**. |
| `-s, --summary <S>` | Summary/title. |
| `-b, --body <B>` | Description (markdown). **Takes precedence over `--template`.** |
| `-y, --priority <P>` | Priority. |
| `-r, --reporter <user>` | Reporter. |
| `-a, --assignee <user>` | Assignee. |
| `-l, --label <L>` | Label; repeatable. |
| `-C, --component <C>` | Component; repeatable. |
| `--fix-version <V>` | fixVersions; repeatable. |
| `--affects-version <V>` | affectsVersions; repeatable. |
| `-e, --original-estimate <T>` | Original time estimate. |
| `--custom <k=v>` | Custom field(s); repeatable. The field must first be **configured under `issue.fields.custom`** in `.config.yml` (via `jira init` or by hand). Key = that field's `name` lowercased with spaces→hyphens (`Story Points` → `story-points`), e.g. `--custom story-points=3`. An **unconfigured key is warned about and silently dropped** (slated to become a hard error). (#346) |
| `-T, --template <file>` | Read body from file (`-` = stdin). |
| `--web` | Open in browser after creation. |
| `--no-input` | **Disable prompting.** Required for unattended runs. |

## issue edit
`jira issue edit ISSUE-KEY [flags]`. Aliases: `update`, `modify`.

| Flag | Behavior — note the asymmetry |
|---|---|
| `-P, --parent <KEY>` | Link to a parent key. |
| `-s, --summary <S>` | Replace summary. |
| `-b, --body <B>` | Replace description (also via stdin pipe). |
| `-y, --priority <P>` | Replace priority. |
| `-a, --assignee <user>` | Replace assignee. |
| `-l, --label <L>` | **Appends** a label (repeatable). Prefix `-` to remove: `--label -old`. |
| `-C, --component <C>` | **Replaces** components (repeatable). Prefix `-` to remove. |
| `--fix-version <V>` | **Adds/appends** fixVersions. Prefix `-` to remove. |
| `--affects-version <V>` | Adds/appends affectsVersions. |
| `--custom <k=v>` | Edit custom field(s). |
| `--skip-notify` | Don't email watchers about the update. |
| `--web` | Open in browser after update. |
| `--no-input` | Disable prompting. |

Remove example: `jira issue edit KEY --label -p2 --label p1 --component -FE --component BE --fix-version -v1.0 --fix-version v2.0`.

## issue view
`jira issue view ISSUE-KEY`. Alias: `show`. ADF → markdown in the terminal; uses `less` as pager by default.

| Flag | Meaning |
|---|---|
| `--comments <n>` | Show N recent comments (default 1). |
| `--plain` | Plain output (no pager UI). |
| `--raw` | Raw Jira API JSON for the issue. |

## issue assign
`jira issue assign ISSUE-KEY ASSIGNEE`. Alias: `asg`. No special flags.

ASSIGNEE values: exact email or display name · `$(jira me)` (self) · `default` (project default assignee) · `x` (unassign). A bare suffix prompts a picker if it matches multiple users.

## issue move (transition)
`jira issue move ISSUE-KEY STATE`. Aliases: `transition`, `mv`. STATE = exact workflow target state.

| Flag | Meaning |
|---|---|
| `--comment <C>` | Add a comment during the transition (workflow must allow it). |
| `-a, --assignee <user>` | Assign while transitioning. |
| `-R, --resolution <R>` | Set resolution while transitioning. |
| `--web` | Open in browser afterward. |

(There is no `--no-input` here — passing `ISSUE-KEY` + `STATE` is already non-interactive.)

## issue comment add
`jira issue comment add ISSUE-KEY [BODY]`. The positional BODY **beats** `--template`.

| Flag | Meaning |
|---|---|
| `--internal` | Mark the comment internal (Jira Service Management). |
| `-T, --template <file>` | Read body from file (`-` = stdin). |
| `--web` | Open in browser afterward. |
| `--no-input` | Disable prompting. |

Multi-line: `jira issue comment add KEY $'Line 1\n\nLine 2'`, or pipe: `echo "..." | jira issue comment add KEY`.

## issue worklog add
`jira issue worklog add ISSUE-KEY TIME_SPENT`. TIME_SPENT = `d`/`h`/`m` separated by spaces, e.g. `"2d 1h 30m"`.

| Flag | Meaning |
|---|---|
| `--started <datetime>` | When the work started, e.g. `"2022-01-01 09:30:00"` or Jira format `2022-01-01T09:30:00.000+0200`. |
| `--timezone <IANA>` | Timezone for `--started`, e.g. `Europe/Berlin` (default `UTC`). |
| `--comment <C>` | Worklog comment (markdown). |
| `--new-estimate <T>` | Set the remaining estimate, e.g. `0h`. |
| `--no-input` | Disable prompting. |

## issue link / unlink / link remote
- `jira issue link INWARD OUTWARD LINK_TYPE` (alias `ln`) — LINK_TYPE is instance-defined (`Blocks`, `Duplicates`, `Relates`, …). `--web` opens after.
- `jira issue unlink INWARD OUTWARD` (alias `uln`). `--web`.
- `jira issue link remote ISSUE_KEY WEBLINK_URL WEBLINK_TITLE` (alias `rmln`) — adds a remote web link. `--web`.

## issue clone
`jira issue clone ISSUE-KEY`. Copies the issue; optionally tweak fields.

| Flag | Meaning |
|---|---|
| `-P, --parent <KEY>` | Parent for the clone. |
| `-s, --summary <S>` | New summary. |
| `-y, --priority <P>` | New priority. |
| `-a, --assignee <user>` | New assignee. |
| `-l, --label <L>` / `-C, --component <C>` | Labels/components (repeatable). |
| `-H, --replace <search>:<replace>` | Replace text (case-sensitive) in summary + body; repeatable. |
| `--web` | Open clone in browser. |

## issue delete
`jira issue delete ISSUE-KEY`. Aliases: `remove`, `rm`, `del`. **Irreversible.**

| Flag | Meaning |
|---|---|
| `--cascade` | Also delete all sub-tasks of the issue. |

## issue watch
`jira issue watch ISSUE-KEY WATCHER` (alias `wat`). WATCHER = exact email/display name or `$(jira me)`.

## epic
`jira epic` (alias `epics`). Explorer view by default; `--table` for table.

- **`epic list [EPIC-KEY]`** — no KEY lists epics; with KEY lists issues *in* that epic. Accepts every `issue list` filter flag **except** `-t/--type`, plus `--table`.
- **`epic create -n"Name" -s"Summary" [...] --no-input`** — same flags as `issue create` **plus required `-n/--name`** (the epic name, distinct from summary). No `-t` (type is fixed to Epic). **Notes:** `-n/--name` is **required even on next-gen** (value ignored there, but the non-interactive mandatory check still demands it); works non-interactively on both project types and the `-b` body lands. **No `--raw` flag** — to capture the new key as JSON use `jira issue create -tEpic … --no-input --raw` instead. The `? Epic Key` prompt is from `epic add` (missing `EPIC-KEY` arg), not create.
- **`epic add EPIC-KEY ISSUE-1 [...ISSUE-N]`** (alias `assign`) — add up to 50 issues to an epic.
- **`epic remove ISSUE-1 [...ISSUE-N]`** — remove up to 50 issues from their epic.

## sprint
`jira sprint` (alias `sprints`). Explorer view by default; `--table` for table. Shows up to ~25–50 recent sprints.

- **`sprint list [SPRINT_ID]`** (aliases `lists`, `ls`) — no ID lists sprints; with ID lists issues in that sprint (accepts all `issue list` filter flags). Sprint-specific flags:
  - `--current` / `--prev` / `--next` — issues in the active / previous / next sprint.
  - `--state future,active,closed` — filter sprints by state (default `active,closed`).
  - `--show-all-issues` — include issues from all projects.
  - `--table` — table view.
  - `--columns` for sprint list: `ID, NAME, START, END, COMPLETE, STATE`. For sprint *issues*: same set as `issue list`.
  - Plus the standard output flags (`--plain`, `--raw`, `--csv`, …) and `--order-by`/`--paginate`.
- **`sprint add SPRINT_ID ISSUE-1 [...ISSUE-N]`** (alias `assign`) — add up to 50 issues to a sprint. Get the ID from `sprint list --table`.
- **`sprint close SPRINT_ID`** — close a sprint.

## release
`jira release list` (alias `ls`) — list project versions. Requires the **Releases/Versions** feature enabled on the instance. Use the global `-p/--project <KEY|id>` to target a specific project: `jira release list -p PROJ`. **No output flags** (`--plain`/`--raw`/etc. error with `unknown flag`) — prints a table directly.

## project / board / open
`project list`, `board list`, and `release list` are the simple list commands: they take **no output flags** (`--plain`, `--raw`, `--csv`, `--columns`, `--no-headers` all error with `unknown flag`) and print a tab-separated table to stdout directly, header row always included. Pipe with `awk`/`cut` to post-process.

- **`jira project list`** (alias `ls`) — projects you can access. Columns: `KEY NAME TYPE LEAD`. Keys only: `jira project list | awk 'NR>1{print $1}'`.
- **`jira board list`** (alias `ls`) — boards in the (configured or `-p`) project. Columns: `ID NAME TYPE`.
- **`jira open [ISSUE-KEY]`** — open the project (no arg) or an issue in the browser. `--no-browser` prints the URL instead of opening.

## init / me / serverinfo / completion / man / version
- **`jira init`** — interactive config bootstrap. Prompts installation type (`Cloud` / `Local`), server URL, login, and (for Local) auth type (`basic` / `bearer`-PAT-via-env / `mtls`). Writes `~/.config/.jira/.config.yml`.
- **`jira me`** — prints the configured user (the self-reference for `-a$(jira me)`).
- **`jira serverinfo`** — instance metadata; quick connectivity check.
- **`jira completion bash|zsh`** — shell completion script (`jira completion --help`).
- **`jira man --generate --output <dir>`** — write full man(7) pages; then `man <dir>/jira-issue-list.7`.
- **`jira version`** — version, git commit, build date, Go version, platform.
