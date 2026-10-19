# Sources

Freshened: 2026-10-20 (exceptions: 1 row, noted inline)

External claims behind this skill. `freshen` re-verifies every row and rewrites the stamp above. For the installed build, the binary's own `jira <cmd> <subcmd> --help` outranks this file — except where the skill flags a help text as wrong.

| Source | URL | Notes |
|---|---|---|
| jira-cli repo | https://github.com/ankitpokhrel/jira-cli | not archived; last push 2026-10-17 |
| jira-cli README (main) | https://github.com/ankitpokhrel/jira-cli/blob/main/README.md | documents unreleased `main` behaviour — see `known-issues.md` § `main` is ahead |
| jira-cli releases | https://github.com/ankitpokhrel/jira-cli/releases | **v1.7.0 (2025-08-31) is still latest**; no tag newer. 15 commits on `main` since 2026-07-22 (PRs #971, #981, #982, #990, #1003, #1008–#1011, #1013, #1014, #1017, #1034, #1039) |
| jira-cli v1.7.0 tag | https://github.com/ankitpokhrel/jira-cli/releases/tag/v1.7.0 | Pinned: v1.7.0 |
| Upstream agent skill (PR #1039) | https://github.com/ankitpokhrel/jira-cli/pull/1039 | `skills/jira-cli/SKILL.md` on `main`; source for the move-lists-states and `--debug` header warnings |
| Installation guide (wiki) | https://github.com/ankitpokhrel/jira-cli/wiki/Installation | |
| Token storage (.netrc/keychain) discussion #356 | https://github.com/ankitpokhrel/jira-cli/discussions/356 | |
| Custom fields discussion #346 | https://github.com/ankitpokhrel/jira-cli/discussions/346 | `--custom` usage |
| Pager configuration discussion #569 | https://github.com/ankitpokhrel/jira-cli/discussions/569 | |
| FAQs (discussions) | https://github.com/ankitpokhrel/jira-cli/discussions/categories/faqs | |
| Atlassian API tokens (Cloud) | https://id.atlassian.com/manage-profile/security/api-tokens | login-gated SPA; 202 |
| Atlassian Document Format (ADF) | https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/ | nodes that may not round-trip |
| Add comment during a transition | https://support.atlassian.com/jira/kb/how-to-add-a-comment-during-a-workflow-transition-and-make-it-mandatory/ | workflow setup for `move --comment` (old confluence.atlassian.com/jirakb URL 301s here) |
| Enable Releases & Versions | https://support.atlassian.com/jira-software-cloud/docs/enable-releases-and-versions/ | needed for `release list` |
| GitHub-flavored markdown spec | https://github.github.com/gfm/ | |
| Jira wiki markup help | https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa?section=all | **exception:** 401 to curl; the browser redirects to the Atlassian login page — login-gated, content not re-read |

## Local ground truth
- Installed build at time of authoring: `jira version` → `1.7.0` (GitCommit 79067e2, CommitDate 2025-08-30, go1.24.1, linux/amd64). v1.7.0 is the current latest release, so the README on `main` and the binary's `--help` are in sync — no version drift.
- All flag/argument tables in `commands.md` were captured from this binary's `--help`.
- **Upstream issue sweep (2026-06-07)** — searched `ankitpokhrel/jira-cli` issues for known bugs/gotchas and folded in the verified, in-scope ones: **#898** (Cloud v1.7.0 dropped `startAt`, so `--paginate` offset is dead / no paging past 100 — also confirmed live), **#621** (older: `epic create --no-input -b` dropped the description; **fixed on v1.7.0** — body lands, verified live), **#948/#984** (`create`/`edit`/`comment`/`epic create` can block on socket/subprocess stdin even with `--no-input`; use `</dev/null`), **#941** (`___` mis-parsed as emphasis) and **#974** (URL-with-params in code blocks) ADF rendering bugs. Open feature requests / non-reproducible reports were not folded in.
- **Source-confirmed (2026-06-07)** against a local clone (v1.7.0+6, HEAD 396933d): **pagination** — `pkg/jira/search.go`: Cloud `Search(jql, limit)` takes no offset and the v3 `/search/jql` endpoint returns `nextPageToken` (jira-cli doesn't follow it); `SearchV2(jql, from, limit)` keeps `startAt` for Server/DC — so the offset works on DC, not Cloud. **Markdown** — `md.ToJiraMD` (the `blackfriday-confluence` renderer, i.e. Confluence/Jira-Server wiki markup) is applied by `create` (`pkg/jira/create.go:140`) and `comment add` (`pkg/jira/issue.go:314`) but by `edit` only when the existing field is ADF/Cloud (`internal/cmd/issue/edit/edit.go:141-143`; paths re-checked at the v1.7.0 tag 2026-10-20), confirming the #935 edit asymmetry. **Epic** — `epic/create` reads `epic.name` from config and skips `cr.Name` on next-gen (so `-n` is ignored there but still required by `isMandatoryParamsMissing`); `getQuestions` returns before any prompt under `--no-input`; there is **no `--raw`** flag. This corrects an earlier mis-attributed "epic create prompts on next-gen" note — the `? Epic Key` EOF came from a downstream `epic add` with an empty key. **Custom fields** — `--custom` keys are validated against `issue.fields.custom` in the config (`cmdcommon/create.go:244`); the key is the field `name` lowercased with spaces→hyphens, and an unconfigured key is warned and dropped.
- **Behavior live-verified against a real Jira Cloud (team-managed) instance on 2026-06-07** — full read + write round-trip on throwaway issues, all artifacts deleted afterward. Confirmed working as documented: `me`, `serverinfo`, `project list`, `board list`, `release list`, `issue list` (`--plain`/`--raw`/`--columns`/`--paginate`), `issue view --raw` field paths (`.fields.issuetype.name`/`.status.name`/`.priority.name`/`.resolution.name`, `customfield_*`), `issue create --no-input --raw`, `issue edit` `--label` append + `--label -x` removal, `assign` (self / `x` / `default`), `comment add` (+ `--internal`), `worklog add`, `watch`, `link`/`unlink` (`Blocks`), `clone -H`, `move`, `delete`, `open --no-browser`, `man`, `completion`. Two authoring errors the live run **corrected**: (1) `project list`, `board list`, and `release list` take **no output flags** — `--plain`/`--raw`/`--csv`/`--columns` error with `unknown flag`; they print a tab-separated table directly; (2) `epic create` takes **no `--raw`** flag (unlike `issue create`). **[Note: a claim here that `epic create` "prompts `Epic Key` and fails on next-gen" was retracted on 2026-06-07 after source review — `epic create` works non-interactively on next-gen; the `? Epic Key` EOF in the original run came from a downstream `epic add` with an empty key, not from create.]** Not exercised on this instance: `sprint add`/`close` (board has no sprint and the CLI can't create one) and `init` (would overwrite the config).


## 2026-07-21 freshen — a verified non-event, plus one new signal

**Nothing upstream changed.** v1.7.0 (2025-08-31) is still the latest release;
the locally installed binary is still `1.7.0` (GitCommit 79067e2); and **all ten
tracked issue rows in `known-issues.md` are in exactly the state recorded on
2026-06-07** — #898, #948, #984, #935, #477, #342, #941, #974, #621 still OPEN,
#822 still CLOSED. No re-verification of the live command surface was needed,
since the binary and `main` are both unmoved.

**The new signal is cadence, and it changes how the workarounds should be
framed.** Measured via the GitHub API rather than inferred:

- last release **2025-08-31** (~11 months);
- repo last pushed **2026-01-20** (~6 months);
- **0 commits on `main` in the trailing 90 days**;
- 172 open issues; **not archived**; 5.8k stars.

**Superseded by the 2026-08-18 pass** — see below.

Recorded in `known-issues.md` § Upstream cadence with the operational
consequence: **do not write guidance that defers to a future fix.** The
documented workarounds (`</dev/null` for the stdin hang, no paging past 100 on
Cloud, GFM→wiki asymmetry on `edit`) are the answer, not a bridge. Framed as a
cadence measurement, not an abandonment claim — the repo is live and quiet, and
a new release is the signal to revisit.

## 2026-08-18 freshen — the repo woke up

The cadence signal measured on 2026-07-21 has reversed. `main` took 10 commits
between 2026-07-30 and 2026-08-12 (six of PRs #1008–#1014; #1012 never merged) and the repo was last
pushed 2026-08-17; open issues fell 172 → 163. **No new release** — v1.7.0
(2025-08-31) is still `isLatest`, so the installed binary is unchanged.

The operational consequence flips in one specific way: the workarounds are
still correct for v1.7.0, but README-on-`main` no longer describes the binary.
Changes landed in areas this skill documents — `epic add`/`epic remove`
permissions, `--plain` output for `epic list` / `sprint list`,
`--show-all-issues` JQL retention, multibyte UTF-8 in the jirawiki parser.
When the next release cuts, re-verify those four surfaces first.

Also re-verified this pass: the Atlassian "comment during a transition" URL now
redirects from `confluence.atlassian.com` to `support.atlassian.com/jira/kb/…`
(benign, content intact). `jira.atlassian.com` wiki-markup help returns 401
behind an auth wall to any non-browser client — bot-block, not a dead page.

## 2026-10-20 freshen — live-verified on v1.7.0 against a team-managed Cloud project

Throwaway issues and components were created and deleted in the same run; `init` wrote only to a scratch `-c` file.

- **`jira init` non-interactive** — every flag given → config written, exit 0; any flag omitted → prompt → `EOF`, exit 1; existing file without `--force` → `Skipping config generation`, exit 1; `--force` keeps `<file>.bkp`. Flags from `jira init --help` (v1.7.0).
- **`issue edit --component` appends** — `internal/cmd/issue/edit/edit.go` @v1.7.0 builds existing + new components and `pkg/jira/edit.go` sends `add`/`remove` ops, same as labels; `--help` text "Replace components" is wrong. Live: `create -C A` → `[A]`; `edit -C B` → `[A,B]`; `edit -C -A` → `[B]`.
- **`issue move` with an invalid state lists the valid ones** — live: `Error: invalid transition state "NoSuchState"` / `Available states for issue <KEY>: 'To Do', 'In Progress', 'In Review', 'Done'`, exit 1, issue unchanged. Also stated in upstream's `skills/jira-cli/SKILL.md` (PR #1039, merged 2026-10-15).
- **#1020 project-scope regex** — `pkg/jql/jql.go` `hasProjectFilter` matches `(?i)project` loosely. Live `--debug`: `-q'summary ~ "kickoff"'` → `JQL: project="PROJ" AND summary ~ "kickoff"`; `-q'summary ~ "project kickoff"'` → `JQL: summary ~ "project kickoff"` (scope gone).
- **`epic add`/`epic remove` verified live** on next-gen (admin user): add → both children get `parent`; remove → parent cleared; empty `EPIC-KEY` → `? Epic Key` → `Error: EOF`. Non-admin failure from upstream #959 (reported on v1.7.0 Cloud; closed by PR #1013, merged 2026-08-01, not in any release — `epic/add/add.go` @v1.7.0 passes `SkipNotify: true`). `issue edit -P EPIC --no-input` attach verified live.
- **#1029 clone `-H`** — live: `-H"throwaway:see https://example.com/x"` → `Invalid replace string, must be in format <find>:<replace>. Skipping replacement...`, then `Issue cloned`, exit 0. Empty-search corruption: `internal/cmd/issue/clone/clone.go:214-221` @v1.7.0 checks only `len(pieces) != 2`, then `strings.ReplaceAll(summary, "", to)`; not run live.
- **#1033 `issue view` loop** — `pkg/md/jirawiki/parser.go:421-423` @v1.7.0: on the last line `handleFencedCodeBlock` returns `t.endIdx` (a column) where the caller expects a line index. Reported against v1.7.0 on-prem; not reproduced live (the test instance is Cloud).
- **`--debug` prints the auth header** — live: `jira serverinfo --debug` output contains one `Authorization: Basic …` line. Also warned in upstream's `skills/jira-cli/SKILL.md` (PR #1039).
