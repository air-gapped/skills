# Known upstream issues — jira-cli

Tracker for upstream `ankitpokhrel/jira-cli` bugs/quirks the skill works around. The **essence** (behavior + workaround) lives inline in the skill body; this table is the **reference** so the bug is trackable and `freshen` can re-check status. Every row applies to v1.7.0, the latest release. URLs: `https://github.com/ankitpokhrel/jira-cli/issues/<N>` (discussions under `/discussions/<N>`).

| Ref | Status | Affects / symptom | Skill location |
|---|---|---|---|
| #898 | open | Cloud v1.7.0: new JQL search API dropped `startAt` → `--paginate` `<from>:` offset ignored; can't page past the first 100 issues | SKILL.md (Cloud-vs-Server, automation), jql-and-filters.md, troubleshooting.md |
| #621 | fixed on v1.7.0 | older (≤v1.3.0): `epic create --no-input -b` dropped the description. On v1.7.0 the body lands (verified live). No action; kept for history. | troubleshooting.md |
| #948 | open | `create`/`edit`/`comment add`/`epic create` block on non-TTY stdin even with `--no-input` — `StdinHasData()` == "stdin not a TTY", so `io.ReadAll` waits for EOF. Use `</dev/null`. | SKILL.md pitfall 1, troubleshooting.md |
| #984 | open | same hang via Unix-socket stdin | SKILL.md pitfall 1, troubleshooting.md |
| #935 | open | Server/DC: `issue edit` sends body **verbatim** (only converts when existing field is ADF/Cloud) — `create`/`comment` do convert GFM→wiki | markdown-adf.md, troubleshooting.md |
| #477 | open | on-prem behind SSO: `jira init` 401 — basic/email can't drive SSO; use a PAT | config-auth.md, troubleshooting.md |
| #822 | closed | SSO/proxy init: `invalid character '<'` (HTML login page); `.netrc machine` must be bare host | config-auth.md, troubleshooting.md |
| #342 | open | Cloud GDPR strict mode: assign/reporter resolves by `accountId`, not email | troubleshooting.md |
| #941 | open | ADF: `___triple___` mis-parsed as emphasis | markdown-adf.md |
| #974 | open | ADF: code block containing a URL with query params can be mangled | markdown-adf.md |
| #959 | closed — fix on `main` only (#1013, unreleased) | next-gen: `epic add`/`remove` hardcode `notifyUsers=false` → non-admins fail with "To discard the user notification…". Use `issue edit KEY -P EPIC` | troubleshooting.md, commands.md, SKILL.md command map |
| #1029 | open | `issue clone -H` splits on every `:` — colon in a value → replacement skipped, clone still created (exit 0); empty search string corrupts the text | commands.md |
| #1033 | open | Server/DC: `issue view` loops forever, unbounded memory, when the description's last line has an inline `{code}` span (`pkg/md/jirawiki/parser.go` `handleFencedCodeBlock`). `--raw` unaffected | troubleshooting.md |
| #1020 | open | `-q` JQL containing the word `project` anywhere (even in a text search) drops the automatic `project="X"` scope → searches all projects | SKILL.md pitfall 10, jql-and-filters.md |

How-to references (stable behavior, not bugs — essence inlined, kept here for provenance):

| Ref | Topic | Skill location |
|---|---|---|
| #346 (discussion) | `--custom` field-handle naming + discovery | commands.md |
| #356 (discussion) | `.netrc` / OS-keychain token storage | config-auth.md |
| #569 (discussion) | pager configuration (`PAGER` env var) | troubleshooting.md |

## `main` is ahead of v1.7.0 — unreleased changes

v1.7.0 is still the latest release. These merged changes exist only on `main`; the README on `main` already describes them. Do not apply them to a v1.7.0 binary. When `jira version` reports a newer release, re-verify these surfaces first and drop the matching workarounds above.

| PR | Change on `main` | Skill text it would change |
|---|---|---|
| #1013 | `epic add`/`remove` stop forcing `notifyUsers=false`; new opt-in `--skip-notify` → no admin needed | #959 workaround (troubleshooting.md, commands.md) |
| #971, #1011 | `--plain` implies `--table` for `sprint list`; `epic list` follows the same rule | commands.md sprint/epic list |
| #1014 | `sprint list --show-all-issues` keeps the `-q` JQL filter | jql-and-filters.md |
| #1003 | jirawiki parser keeps multibyte UTF-8 text | markdown-adf.md |
| #1008 | new `cf-access` auth type (Cloudflare Access JWT) | config-auth.md auth table |
| #981 | token pre-check accepts an `api_token` set in the config file | config-auth.md ("token never in config") |

Every workaround in this skill is the answer for v1.7.0. Never write guidance that defers to a future fix ("page past 100 once #898 lands").

Issue state is a poor proxy for behaviour in both directions: #621 is `OPEN` but fixed on v1.7.0; #959 is `CLOSED` but unfixed in any release. On each `freshen`, re-check the `open` rows and this table against the latest release, not against issue state.
