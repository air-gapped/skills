# Known upstream issues — jira-cli

Tracker for upstream `ankitpokhrel/jira-cli` bugs/quirks the skill works around. The **essence** (behavior + workaround) lives inline in the skill body; this table is the **reference** so the bug is trackable and `freshen` can re-check status. Status re-checked **2026-07-21** (still v1.7.0) — **every `open` row below is still open; nothing closed, nothing shipped**. See the upstream-cadence note at the bottom for why that is unlikely to change soon. URLs: `https://github.com/ankitpokhrel/jira-cli/issues/<N>` (discussions under `/discussions/<N>`).

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

How-to references (stable behavior, not bugs — essence inlined, kept here for provenance):

| Ref | Topic | Skill location |
|---|---|---|
| #346 (discussion) | `--custom` field-handle naming + discovery | commands.md |
| #356 (discussion) | `.netrc` / OS-keychain token storage | config-auth.md |
| #569 (discussion) | pager configuration (`PAGER` env var) | troubleshooting.md |

## Upstream cadence — measured 2026-07-21

The workarounds in this skill are still the answer today, but **the repo
resumed development in late July 2026** after six quiet months — so this is no
longer a "nothing will ever change" situation. Measured, not inferred:

| Signal | Value |
|---|---|
| Latest release | **v1.7.0, 2025-08-31** — ~12 months old, still `isLatest` |
| Last push to the repo | **2026-08-17** (was 2026-01-20 at the previous pass) |
| Commits on `main` in the trailing 90 days | **10** (2026-07-30 → 2026-08-12) |
| Open issues | 163 |
| Archived? | **No** — 5.9k stars, live and active again |

**`main` is now ahead of the released binary.** PRs #1008–#1014 changed
`epic add`/`epic remove` (no longer requires admin), `--plain` behaviour for
`epic list` / `sprint list`, `--show-all-issues` JQL retention, and multibyte
UTF-8 in the jirawiki parser — all areas this skill documents. None of it is in
v1.7.0. Read the README on `main` as a description of unreleased behaviour, not
of the binary you have installed.

Every tracked bug row above (#898 pagination, #948/#984 stdin hangs, #935 edit
asymmetry, #941/#974 ADF rendering, #477 SSO, #342 GDPR accountId) is unchanged
since the 2026-06-07 pass. With no commits in a quarter and no release in
eleven months, **do not write guidance that defers to a future fix** — e.g.
"page past 100 once #898 lands". Build the workaround in.

This is a *cadence* observation, not an abandonment claim: the repo is not
archived and maintainers can return at any time. Re-measure rather than assume
in either direction.

**Note on #621 — an open issue is not a live bug.** #621 is still `OPEN`
upstream, but the behaviour it describes (`epic create --no-input -b` dropping
the description) **does not reproduce on v1.7.0** — verified live on
2026-06-07. The table records it as fixed-in-practice for exactly this reason.
Issue state is a poor proxy for behaviour in both directions; the live check is
what settles it.

**Freshen note:** re-check the `open` rows against the tracker on each `freshen`
run — when one closes / ships a fix in a new release, update the inline
workaround and flip the status here. Also re-measure the cadence table: a new
release is the signal that the "permanent workaround" framing needs revisiting.
