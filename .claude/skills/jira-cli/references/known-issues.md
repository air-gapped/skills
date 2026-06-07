# Known upstream issues — jira-cli

Tracker for upstream `ankitpokhrel/jira-cli` bugs/quirks the skill works around. The **essence** (behavior + workaround) lives inline in the skill body; this table is the **reference** so the bug is trackable and `freshen` can re-check status. Status as of **2026-06-07** (v1.7.0). URLs: `https://github.com/ankitpokhrel/jira-cli/issues/<N>` (discussions under `/discussions/<N>`).

| Ref | Status | Affects / symptom | Skill location |
|---|---|---|---|
| #898 | open | Cloud v1.7.0: new JQL search API dropped `startAt` → `--paginate` `<from>:` offset ignored; can't page past the first 100 issues | SKILL.md (Cloud-vs-Server, automation), jql-and-filters.md, troubleshooting.md |
| #621 | open | `epic create --no-input` fragile on Cloud / fails non-interactively on next-gen (prompts `Epic Key`) | SKILL.md pitfall 5, commands.md, troubleshooting.md |
| #948 | open | `issue create --no-input` hangs reading stdin in non-TTY (subprocess) — use `</dev/null` | SKILL.md pitfall 1, troubleshooting.md |
| #984 | open | same hang via Unix-socket stdin | SKILL.md pitfall 1, troubleshooting.md |
| #935 | open | Server/DC: GFM **not** converted to Jira wiki markup (passed through literally) | markdown-adf.md, troubleshooting.md |
| #477 | open | on-prem behind SSO: `jira init` 401 — basic/email can't drive SSO; use a PAT | config-auth.md, troubleshooting.md |
| #822 | closed | SSO/proxy init: `invalid character '<'` (HTML login page); `.netrc machine` must be bare host | config-auth.md, troubleshooting.md |
| #342 | open | Cloud GDPR strict mode: assign/reporter resolves by `accountId`, not email | troubleshooting.md |
| #941 | open | ADF: `___triple___` mis-parsed as emphasis | markdown-adf.md |
| #974 | open | ADF: code block containing a URL with query params can be mangled | markdown-adf.md |

How-to references (stable behavior, not bugs — essence inlined, kept here for provenance):

| Ref | Topic | Skill location |
|---|---|---|
| #346 (discussion) | `--custom` field-handle naming + discovery | commands.md |
| #356 (discussion) | `.netrc` / OS-keychain token storage | config-auth.md |
| #569 (discussion) | pager configuration (`PAGER` env var) | troubleshooting.md |

**Freshen note:** re-check the `open` rows against the tracker on each `freshen` run — when one closes / ships a fix in a new release, update the inline workaround and flip the status here.
