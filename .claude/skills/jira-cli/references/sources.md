# Sources

Per-row `Last verified:` dates for the external claims in this skill. `freshen` mode reads + updates this file. The most authoritative reference for the installed build is always the binary's own `jira <cmd> <subcmd> --help`.

| Source | URL | Last verified | Pinned |
|---|---|---|---|
| jira-cli repo | https://github.com/ankitpokhrel/jira-cli | 2026-06-07 | |
| jira-cli README (main) | https://github.com/ankitpokhrel/jira-cli/blob/main/README.md | 2026-06-07 | matches v1.7.0 binary |
| jira-cli releases | https://github.com/ankitpokhrel/jira-cli/releases | 2026-06-07 | latest v1.7.0 (2025-08-31) |
| jira-cli v1.7.0 tag | https://github.com/ankitpokhrel/jira-cli/releases/tag/v1.7.0 | 2026-06-07 | v1.7.0 |
| Installation guide (wiki) | https://github.com/ankitpokhrel/jira-cli/wiki/Installation | 2026-06-07 | |
| Token storage (.netrc/keychain) discussion #356 | https://github.com/ankitpokhrel/jira-cli/discussions/356 | 2026-06-07 | |
| Custom fields discussion #346 | https://github.com/ankitpokhrel/jira-cli/discussions/346 | 2026-06-07 | `--custom` usage |
| Pager configuration discussion #569 | https://github.com/ankitpokhrel/jira-cli/discussions/569 | 2026-06-07 | |
| FAQs (discussions) | https://github.com/ankitpokhrel/jira-cli/discussions/categories/faqs | 2026-06-07 | |
| Atlassian API tokens (Cloud) | https://id.atlassian.com/manage-profile/security/api-tokens | 2026-06-07 | |
| Atlassian Document Format (ADF) | https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/ | 2026-06-07 | nodes that may not round-trip |
| Add comment during a transition | https://confluence.atlassian.com/jirakb/how-to-add-a-comment-during-a-transition-779160682.html | 2026-06-07 | workflow setup for `move --comment` |
| Enable Releases & Versions | https://support.atlassian.com/jira-software-cloud/docs/enable-releases-and-versions/ | 2026-06-07 | needed for `release list` |
| GitHub-flavored markdown spec | https://github.github.com/gfm/ | 2026-06-07 | |
| Jira wiki markup help | https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa?section=all | 2026-06-07 | |

## Local ground truth
- Installed build at time of authoring: `jira version` → `1.7.0` (GitCommit 79067e2, CommitDate 2025-08-30, go1.24.1, linux/amd64). v1.7.0 is the current latest release, so the README on `main` and the binary's `--help` are in sync — no version drift.
- All flag/argument tables in `commands.md` were captured from this binary's `--help`.
- **Upstream issue sweep (2026-06-07)** — searched `ankitpokhrel/jira-cli` issues for known bugs/gotchas and folded in the verified, in-scope ones: **#898** (Cloud v1.7.0 dropped `startAt`, so `--paginate` offset is dead / no paging past 100 — also confirmed live), **#621** (`epic create --no-input` fragile on Cloud; `issue create` is the reliable path), **#948/#984** (`issue create` can still block on socket/subprocess stdin even with `--no-input`; use `</dev/null`), **#941** (`___` mis-parsed as emphasis) and **#974** (URL-with-params in code blocks) ADF rendering bugs. Open feature requests / non-reproducible reports were not folded in.
- **Behavior live-verified against a real Jira Cloud (team-managed) instance on 2026-06-07** — full read + write round-trip on throwaway issues, all artifacts deleted afterward. Confirmed working as documented: `me`, `serverinfo`, `project list`, `board list`, `release list`, `issue list` (`--plain`/`--raw`/`--columns`/`--paginate`), `issue view --raw` field paths (`.fields.issuetype.name`/`.status.name`/`.priority.name`/`.resolution.name`, `customfield_*`), `issue create --no-input --raw`, `issue edit` `--label` append + `--label -x` removal, `assign` (self / `x` / `default`), `comment add` (+ `--internal`), `worklog add`, `watch`, `link`/`unlink` (`Blocks`), `clone -H`, `move`, `delete`, `open --no-browser`, `man`, `completion`. Two authoring errors the live run **corrected**: (1) `project list`, `board list`, and `release list` take **no output flags** — `--plain`/`--raw`/`--csv`/`--columns` error with `unknown flag`; they print a tab-separated table directly; (2) `epic create --no-input` still **prompts `Epic Key` and fails (`Error: EOF`) non-interactively on team-managed/next-gen projects** — the reliable path there is `issue create -tEpic` + `-P/--parent`. Not exercised on this instance: `sprint add`/`close` (board has no sprint and the CLI can't create one) and `init` (would overwrite the config).
