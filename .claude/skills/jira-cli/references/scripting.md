# Scripting & automation with jira-cli

The interactive UI is the default; scripting requires turning it off. This file is the recipe book for unattended, parseable, safe automation — in CI, cron, or an agent loop.

## The non-interactive contract

- **Reads** → one of `--plain` / `--raw` / `--csv`. Bare `list`/`view` open a pager/TUI and emit terminal control codes, not data.
- **Writes** → `--no-input` **and** every required value as a flag/positional. A missing required field with `--no-input` errors fast; *without* `--no-input` it blocks on a prompt forever (the classic "the script hung" bug in CI).
- **Headless** → avoid `--web` (it tries to launch a browser).

```bash
set -euo pipefail
export JIRA_API_TOKEN="${JIRA_API_TOKEN:?set the token}"   # fail loudly if unset
```

## Output shapes

```bash
# Plain, parseable, no header, chosen columns, tab-separated
jira issue list -q'statusCategory = "To Do"' \
  --plain --no-headers --columns key,status,assignee

# Custom delimiter (avoids tab-splitting headaches)
jira issue list --plain --no-headers --delimiter '|' --columns key,summary

# Raw JSON → jq (shape mirrors the Jira REST API)
jira issue list --raw | jq -r '.[].key'
jira issue list --raw | jq -r '.[] | [.key, .fields.status.name, .fields.summary] | @tsv'

# CSV → spreadsheet / awk
jira issue list --csv > issues.csv
```

`--raw` JSON: top level is an array of issues; per-issue fields live under `.fields.*` (`.fields.status.name`, `.fields.assignee.displayName`, `.fields.priority.name`, `.fields.customfield_10016`, …). Server/DC and Cloud differ slightly in field presence — inspect with `jira issue view KEY --raw | jq '.fields | keys'` first.

## Capture a created key and chain

`issue create --raw` prints the new issue JSON; pull `.key`:

```bash
KEY=$(jira issue create -tTask -s"Automated task" --no-input --raw | jq -r '.key')
jira issue assign "$KEY" "$(jira me)"
jira issue move   "$KEY" "In Progress" --comment "Auto-started"
echo "created $KEY"
```

## Bulk operations (loop over keys)

Always derive the key list from a query, never hardcode.

```bash
# Transition every "To Do" issue assigned to me
for k in $(jira issue list -q'assignee = currentUser() AND status = "To Do"' \
             --plain --no-headers --columns key); do
  jira issue move "$k" "In Progress"
done

# Add a watcher to all unassigned issues
ME=$(jira me)
for k in $(jira issue list -ax --plain --no-headers --columns key); do
  jira issue watch "$k" "$ME"
done

# Bulk reassign issues under an epic (JSON path)
jira issue list -q'parent = PROJ-123 AND assignee = currentUser()' --raw \
  | jq -r '.[].key' \
  | while read -r k; do jira issue assign "$k" "teammate@example.com"; done
```

### Bulk-edit safety

`edit` field semantics bite in loops:
- `--label` **appends**, `--component` **replaces**, `--fix-version` **appends**. To set-not-add a label, remove the old one in the same call: `--label -old --label new`.
- Test the edit on **one** issue and `view` the result before looping over hundreds.
- For destructive loops (`delete`), print the keys first and require explicit confirmation — there is no undo, and `--cascade` also deletes sub-tasks.

## Reporting snippets

```bash
# Count issues by status
jira issue list --plain --no-headers --columns status | sort | uniq -c

# Tickets created per day this month
jira issue list --created month --plain --no-headers --columns created \
  | awk '{print $1}' | cut -d- -f3 | sort -n | uniq -c

# Issues per sprint
jira sprint list --table --plain --no-headers --columns id,name \
  | while IFS=$'\t' read -r id name; do
      n=$(jira sprint list "$id" --plain --no-headers 2>/dev/null | wc -l)
      printf '%-20s %3d\n' "$name" "$n"
    done
```

## Multi-instance in one script

```bash
JIRA_CONFIG_FILE=~/.config/.jira/cloud.yml   jira issue list -q'...'   # or -c <file>
JIRA_CONFIG_FILE=~/.config/.jira/onprem.yml  jira issue list -q'...'
```

Each config carries its own server URL + auth; the `JIRA_API_TOKEN` env var must match whichever instance you're hitting (export per-block, or use `.netrc`/keychain — see `config-auth.md`).

## CI checklist
1. `JIRA_API_TOKEN` (and `JIRA_AUTH_TYPE=bearer` for PAT) provided as a secret.
2. A config file committed or generated for the runner (non-interactive — `jira init` prompts, so prefer copying a known-good `.config.yml` and setting `JIRA_CONFIG_FILE`).
3. Every write has `--no-input`; no `--web`.
4. Reads use `--plain`/`--raw`/`--csv`.
5. Add `--debug` temporarily when a step misbehaves.
