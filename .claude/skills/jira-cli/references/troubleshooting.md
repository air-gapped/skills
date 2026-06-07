# jira-cli troubleshooting

Add `--debug` to any failing command first — it prints the HTTP request/response and is usually decisive.

## The command hangs / "froze" (no output, never returns)
A write hit an interactive prompt. The process is waiting for keyboard input that won't come (CI, agent, backgrounded shell).
- **Fix:** add `--no-input` and supply every required field as a flag/positional.
- A read without a format flag drops into the pager/TUI — looks like a hang in a non-TTY. Add `--plain`/`--raw`/`--csv`.
- **Known bug — `--no-input` is not always enough.** jira-cli decides to read the body from stdin via `StdinHasData()`, which is really just "stdin is **not a TTY**" — not an actual data check. So when stdin is a Unix socket or subprocess pipe (common when an agent shells out), the body-reading writes (`create`, `edit`, `comment add`, `epic create`) call `io.ReadAll(os.Stdin)` and block until the pipe closes — even with `--no-input` (#948/#984). Redirect stdin to give immediate EOF: append `</dev/null` (`jira issue create … --no-input </dev/null`).

## `401 Unauthorized`
- `JIRA_API_TOKEN` unset, wrong, or expired. `echo ${JIRA_API_TOKEN:+set}` to confirm it's exported in *this* shell.
- **Cloud:** must be an **API token**, not your account password.
- **On-prem PAT:** also set `JIRA_AUTH_TYPE=bearer`.
- **On-prem basic:** `JIRA_API_TOKEN` is your **password**.
- Wrong instance: the token must match the server URL in the active config (`-c`/`JIRA_CONFIG_FILE`).
- **On-prem behind SSO:** basic auth/email won't work — generate a **PAT**, set `JIRA_AUTH_TYPE=bearer`. See the SSO entry below.
- Verify with `jira me`.

## `jira init`: `invalid character '<'` / `401` on on-prem behind SSO
The instance is fronted by SSO (Okta/AD/SAML), so the CLI's API call lands on the SSO HTML login page — the `<` is `<html>` being parsed as JSON. The CLI can't do interactive SSO. Fix (#477, #822): generate a **Personal Access Token**, `export JIRA_AUTH_TYPE=bearer` + `JIRA_API_TOKEN=<PAT>`, then `jira init` → Local → bearer, logging in with your **username** (not email) if they differ. If using `.netrc`, the `machine` line must be the bare host with no `https://`. Details: `references/config-auth.md`.

## `Specify a valid issue type` / type errors
The `-t` value doesn't exist (or differs in case) on that project. Projects define their own types — `Bug` may be `Defect`, `Sub-task` may be `Subtask`.
- Discover real types: `jira issue list -p PROJ --plain --no-truncate --paginate 10` or `jira issue view PROJ-1 --raw | jq '.fields.issuetype.name'`.

## `Field 'priority' cannot be set` (often on epics)
The field isn't on that issue type's create/edit screen for the project. Epics frequently have no priority field. Drop the flag, or add the field to the screen in Jira admin.

## `Given parent work item does not belong to appropriate hierarchy`
`-P/--parent` points at something that can't hold the child — e.g. creating a sub-task under another sub-task, or under an issue type that doesn't allow sub-tasks. Point `-P` at a valid parent (a Story/Task for a Sub-task; an Epic for `-P` epic-attach on next-gen).

## `? Epic Key` prompt / `Error: EOF` on epic commands
The `Epic Key` prompt belongs to **`jira epic add`**, shown when its `EPIC-KEY` positional is missing or empty; in a non-interactive shell it then dies with `Error: EOF`. Provide the key: `jira epic add EPIC-1 ISSUE-1 ISSUE-2`.

`epic create` itself works non-interactively on both classic and next-gen projects. Two real gotchas (not bugs):
- **`-n` and `-s` are both required** even on next-gen (where `-n`'s value is ignored — the mandatory check still demands it). Omitting `-n` fails with "Params `--summary` and `--name` is mandatory".
- **No `--raw` flag** — `jira epic create … --raw` errors `unknown flag: --raw`. To capture the created key as JSON, create the epic as an issue: `jira issue create -tEpic -s"…" --no-input --raw | jq -r '.key'`.

(`jira init` writes `epic.name`/`epic.link` to the config from the project's "Epic Name" field; on non-English or unusual instances those may need hand-fixing for epic features to work — but a standard `-n -s --no-input` create succeeds, body and all.)

## `--custom` field ignored / "custom fields are not configured"
`--custom` only works for fields declared under `issue.fields.custom` in `~/.config/.jira/.config.yml`. A key that isn't configured triggers the warning *"Some custom fields are not configured and will be ignored"* and is **dropped from the request** (currently a warning; slated to become a hard error). Fix: add the field to the config — re-run `jira init`, or add an entry with its `name` (and `key`/`schema`) under `issue.fields.custom` — then reference it as that `name` lowercased with spaces→hyphens. Seeing the `customfield_*` in `issue view KEY --raw` confirms it exists, but it still must be in the config to be settable.

## Transition fails / "state not found"
The STATE string isn't a valid transition from the issue's *current* status in the workflow. Valid targets are status- and workflow-dependent.
- Run `jira issue move PROJ-123` interactively once to see the allowed states, then script the exact string.
- `--comment`/`-R`/`-a` during a move only work if the workflow's transition screen allows those fields.

## Assignment fails for a real user
- Name/email must be an **exact** match. Try the email if the display name fails.
- **Cloud** GDPR strict mode resolves users by **accountId** — fetch it: `jira issue view KEY --raw | jq '.fields.assignee.accountId'`, or use the email (#342).
- **Server/Data Center** resolves by **username** — pass the Jira username (from the profile page), not the email, when they differ.
- `x` unassigns; `default` uses the project default assignee.

## `edit` didn't replace what I expected
Field semantics are asymmetric: `--label` and `--fix-version` **append**, `--component` **replaces**. To remove a value, prefix `-`: `--label -old`. To swap, remove + add in one call.

## Body/template ignored
`-b/--body` (create/edit) and the positional comment body **take precedence** over `--template`. Pass only one source.

## Markdown looks wrong in Jira
- **Cloud:** ADF conversion is lossy. Use GFM ```` ``` ```` fences (not `{code}`), expect `~~x~~`→`-x-`, `@user` needs `[~accountid]`, emoji/HTML dropped.
- **Server/Data Center:** there is **no ADF** — the field stores Jira wiki markup. `create`/`comment add` convert your Markdown to wiki markup, but **`edit` sends the body verbatim** (it only converts when the existing description is ADF/Cloud), so an *edited* description shows raw `## H2` (#935). Write **wiki markup** directly (`h2.`, `*bold*`, `{code}…{code}`), especially when editing. See `markdown-adf.md` → "Jira wiki markup (Server/DC)".

Test on one issue before bulk either way.

## Empty output from `list`
- The filter matched nothing (check case/spelling of `-s`/`-y`/`-t` values).
- `-q` JQL is scoped to the configured project — add `project IS NOT EMPTY` or a project clause for cross-project.
- Wrong project: pass `-p PROJ` or check the config default.
- **Can't fetch more than ~100 issues on Jira Cloud (v1.7.0).** Atlassian's new JQL search API dropped `startAt`, so the `<from>:` offset in `--paginate` is ignored — every page returns the same first batch (#898). Narrow the result set with JQL/filters (date, status, assignee, `--order-by`) instead of paging. Server/Data Center still supports offset paging.

## Pager / control-character junk in piped output
You forgot a format flag, or `--plain` without `--no-headers`/`--columns`. For machine parsing use `--plain --no-headers --columns ...`, or `--raw`/`--csv`. Change the pager via the `PAGER` env var (`PAGER=cat` disables paging); `--plain` skips the pager entirely. (#569)

## Clipboard copy (`c` / `Ctrl+k`) does nothing on Linux
The TUI copy needs `xclip` or `xsel` installed.

## release list errors / empty
The Releases/Versions feature must be enabled on the instance. Target a project explicitly: `jira release list -p PROJ`.

## Server vs Cloud field differences
`--raw` JSON fields and some features differ between Cloud (REST v3) and Server/Data Center (REST v2). Inspect with `jira issue view KEY --raw | jq '.fields | keys'` rather than assuming Cloud shapes on Server. Confirm which backend with `jira serverinfo` (`Deployment Type`). The big divergences — markdown/ADF, auth, user-identity (accountId vs username), and `--paginate` offset — are tabulated in `SKILL.md` ("Cloud vs Server / Data Center").

## When stuck
- `jira <cmd> <subcmd> --help` — authoritative flags/args for the build.
- `jira man --generate --output /tmp/jira-man && man /tmp/jira-man/jira-issue-list.7`.
