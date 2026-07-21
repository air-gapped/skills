# Filtering & JQL with jira-cli

Two ways to narrow a `list` (also `epic list` / `sprint list`): **filter flags** (composable, POSIX-style) and **raw JQL** (`-q/--jql`). They combine — flags AND a `-q` clause both apply.

## Filter flags

| Flag | Example | Meaning |
|---|---|---|
| `-t` type | `-tBug` | issue type |
| `-s` status | `-s"In Progress"` | status (repeatable: `-sOpen -s"In Review"`) |
| `-y` priority | `-yHigh` | priority |
| `-a` assignee | `-a$(jira me)` | assignee; `-ax` = unassigned |
| `-r` reporter | `-r"Jane Doe"` | reporter |
| `-l` label | `-lbackend -lurgent` | label (repeatable) |
| `-C` component | `-CBackend` | component |
| `-R` resolution | `-R"Won't Do"` | resolution |
| `-P` parent | `-PPROJ-100` | parent issue |
| `-w` watching | `-w` | issues you watch |
| `--history` | `--history` | recently accessed |

All values are **instance-defined and case-sensitive**, and need quotes when they contain spaces. Discover the real values with `jira issue list -p PROJ --plain --no-truncate --paginate 10` or by reading an existing issue's `--raw` JSON.

### The `~` negation idiom
A tilde **prefix** negates a flag value (it is jira-cli's "NOT", not a JQL operator):

```bash
jira issue list -s~Done            # status is NOT Done
jira issue list -a~x               # assignee is NOT empty (i.e. assigned to someone)
jira issue list -s~Open -ax        # NOT Open AND unassigned
```

`-ax` means unassigned; `-a~x` means assigned-to-anyone.

## Date filtering

`--created` / `--updated` (and `--created-after`/`--created-before`/`--updated-after`/`--updated-before`) accept:

- keywords: `today`, `week`, `month`, `year`
- absolute: `2025-09-15` or `2025/09/15`
- relative period: `-<N><unit>` where unit ∈ `w` (weeks), `d` (days), `h` (hours), `m` (minutes) — e.g. `-7d`, `-3w`, `-2h`, `-30m`

The bare `--created`/`--updated` form takes precedence over the `-after`/`-before` pair if both are given.

```bash
jira issue list --created -7d                    # created in the last 7 days
jira issue list --created month -lbackend        # this month, label backend
jira issue list --created-after 2025-09-15       # since a specific date
jira issue list --created -1h --updated -30m     # very recent activity
```

## Raw JQL (`-q` / `--jql`)

`-q` runs JQL **inside the configured project's context** by default — so a bare query is scoped to that project. To go cross-project, add a project clause.

```bash
jira issue list -q'assignee = currentUser()'
jira issue list -q'updated >= -1w AND status != Done'
jira issue list -q'priority = High AND statusCategory != Done'
jira issue list -q'summary ~ "cli"'              # text contains
jira issue list -q'project IS NOT EMPTY'         # all projects
jira issue list -q'"Epic Link" = PROJ-123'       # issues under an epic (classic projects)
jira issue list -q'parent = PROJ-123'            # children (next-gen / sub-tasks)
```

Notes:
- `currentUser()` is the JQL function for "me" (equivalent to `-a$(jira me)` but server-side).
- `statusCategory` (`To Do` / `In Progress` / `Done`) is workflow-independent and far more portable across instances than hardcoding status *names* — prefer it for "is this open?" questions.
- Field names with spaces or reserved words need quotes: `"Epic Link"`, `"Story Points"`.
- Classic (company-managed) projects use `"Epic Link"`; next-gen (team-managed) use `parent`. If one returns nothing, try the other.

## Ordering & pagination

```bash
jira issue list --order-by rank --reverse        # UI rank order (ascending)
jira issue list --order-by updated               # most-recent first (DESC default)
jira issue list --paginate 100                   # cap at 100 (the max)
```

**Pagination is broken on Jira Cloud in v1.7.0 (#898).**
Atlassian's new JQL search endpoint dropped the `startAt` parameter, so the `<from>:`
offset in `--paginate <from>:<limit>` is **silently ignored** — `--paginate 0:1`,
`1:1`, and `2:1` all return the same first issue. There is **no way to fetch past the
first 100 issues** on Cloud; `--paginate` only sets the limit (maxResults). To get a
specific slice, **narrow with JQL/filters** (status, date, assignee, `--order-by`)
rather than paging. Server/Data Center (older API) still honors `<from>:<limit>`.

**Treat this as permanent, not pending.** Re-checked 2026-07-21: #898 is still
open, v1.7.0 is still the latest release (2025-08-31), and the repo has had **no
commits in 90 days**. Build the JQL-narrowing approach into scripts rather than
waiting for a fix. See `known-issues.md` § Upstream cadence.

## Worked examples

```bash
# My open, high-priority work, parseable
jira issue list -a$(jira me) -yHigh -q'statusCategory != Done' \
  --plain --no-headers --columns key,status,summary

# Unassigned bugs created this week
jira issue list -tBug -ax --created week --plain

# Everything I reported, oldest first
jira issue list -r$(jira me) --order-by created --reverse

# Stale: not updated in 24 weeks, still open, assigned to someone
jira issue list -s~Done --updated-before -24w -a~x --plain
```
