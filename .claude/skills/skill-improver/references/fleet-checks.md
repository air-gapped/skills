# Fleet checks — what each one catches, and how to read it

Seven checkers under `scripts/`, each testing something a parser can decide. Run
them over the whole tree, not just the skill being edited. Per section: the
invocation and which hits are *expected* and must not be "fixed".

---

## A Fence Is Code, and Nothing Else Checks It

No gate looks inside a ```bash fence. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/check-shell-fences.py [root]` after editing
any block a reader is meant to run.

Two passes: `bash -n` for syntax errors, plus a regex pass for `cmd \   # note`
(the backslash escapes the space, `#` opens a comment, the next line becomes a
separate command; valid syntax, wrong meaning).

| Output class | Action |
|---|---|
| Broken continuations, unexplained parse failures | Real; fix |
| Placeholder blocks (`<model>`), prompt transcriptions (`$ cmd` / `# cmd`) | Expected to fail; add a note about the convention, never edit the command |

`scripts/check-yaml-fences.py` is the sibling for ```yaml blocks. Real-bug shape:
a `fieldPath` containing `[` `]` unquoted inside a YAML flow mapping (`{...}`).
Expect it to be quiet. Go/Jinja templating is reported separately (not YAML until rendered).

## Content Scheduled to Become False

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check-expiring-claims.py [root] [--relative]`
alongside a freshen pass.

Future dates themselves (lifecycle tables) are fine. What rots is a *relative
descriptor* beside a date ("2.11 goes EOL 2026-10-24 — roughly three months out"); `--relative`
reports exactly those. Fix: delete the relative phrase and tell the reader to compute
from the date. A replacement phrase rots identically.

**Standing false positive:** this file's own quotation of a date beside a relative
phrase is flagged by `--relative` every run. Leave it. A run whose only `[rel]`
hit is this paragraph is clean.

## Two Classes of Link Rot, and the Rest Is Noise

The skillevaluator gate checks links only in skills staged for a commit. Sweep the
whole tree with `python3 ${CLAUDE_SKILL_DIR}/scripts/check-links.py [root] [--workers N]`.

It checks two classes and skips the rest: **documentation hosts** (doc sites
reorganise silently; old path 404s) and **GitHub `blob`/`tree` paths** (GitHub
redirects a renamed repo, never a moved file). GitHub issue/PR/release and arXiv
URLs are stable; skipped. `--all` drops the filter.

**A moved file is searched for, not guessed at.** No path edit finds a relocated file.

| Status | Action |
|---|---|
| 403 | First try the sibling path (a retired docs URL is often answered with a block page; this is the only real defect of the three causes). Otherwise bare `curl`: real page = user-agent block; refused again with interstitial title = bot challenge. Neither is a dead link. |
| 429 | Rate limit tripped: lower `--workers` and re-run; do not record it. |

403 and 429 print outside the dead list and do not affect the exit code.

Add a host to `DOC_HOSTS` when a skill starts citing it; an absent host is never swept.

## A Remediation Floor Is the Number an Operator Acts On

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check-advisory-floors.py [root] --verify`
after any edit that names a CVE and a fixed version.

Failure directions: **too low** sends an operator to a build still in the affected
range; **attributed to the wrong line** credits a version the advisory never
listed (silent, survives review).

**Read every flag before editing; three shapes flag legitimately:**
- A per-minor backport floor sits outside the advisory's range by design.
- An unbounded range with null `first_patched_version` means the feed does not know the fix — derive it from the fix PR's merge commit; never read it as "no fix".
- A negative claim ("does not affect 3.1") is a correction, not a floor.

The tool checks only the lines it can resolve by pattern (7 of 104 ids) and skips
lines naming several advisories; do not guess at those. `--selfcheck` replays the
Argo CD line verbatim and asserts it is still condemned; a clean run means nothing
if that assertion has been tuned away.

## A Cited Issue's State Drifts, and the Skill Keeps Its Old Verdict

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check-issue-states.py [root]`. It resolves
every cited issue and PR in one batched GraphQL call and reports three
disagreement classes: prose says **open** but tracker says closed or merged; prose
says **merged** but PR closed unmerged; prose says **unmerged** but it merged.
Each is wrong whichever side you believe.

**Closed is not fixed; the checker reports drift, never a rewrite.** Read
`stateReason` and the closing comment before editing: `NOT_PLANNED` plus a bot
comment is abandonment (warning stays); `COMPLETED` with a linked PR is a fix.
`stateReason` is not portable across repos (some inactivity bots close as
`COMPLETED`). When the reason looks like a fix, confirm the closer and labels:

    gh api repos/O/R/issues/N --jq '.state_reason, .closed_by.login, [.labels[].name]'

Decide by evidence, not state alone: findings split evenly between deleting a live
warning and keeping a dead one.

**Get the fix version from ancestry, not dates.**
`git -C <clone> tag --contains <sha> | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | head -1`.
A merge landing after a release branch was cut ships in the release after the next.

**A fix can predate the close by months.** Do not trust a re-probe that reads only
state; read the thread (a third party re-running the reproduction, the author
closing and naming the fix).

**Retire only the justification that died.** A warning with two independent
reasons: delete only the one that was fixed.

**Exempt by design:** deliberate "stale-bot closed it, treat as a live risk"
phrasing. A line citing several refs in *differing* states is reported separately
as AMBIGUOUS.

**AMBIGUOUS is not a defect count and is not meant to reach zero.** Read the line
and move on. **Do not reword correct prose to clear the counter.** Only the
findings count is an error count.

## A Release Note Saying "Bumped X to N" May Be a CI Pin

Before recording a dependency floor from release notes, **read the pull request's
changed-file list**, not its title:

    gh pr view <N> --repo <O>/<R> --json title,files --jq '.files|map(.path)|join(", ")'

Then read the floor from the file the runtime installs, at the tag:

    git -C <clone> show <tag>:requirements/common.txt | grep -i '^<package>'

`requirements/test/*` only = CI pin, runtime floor unchanged. `requirements/common.txt`
= real floor. Summary lines do not distinguish them. A misread floor silently
reclassifies an exposure as patched (a CI pin can clear CVEs the real floor does
not), so run the file-list check every time.

Leave neighbouring claims in the same sentence alone until separately verified.

## A Ragged Table Loses Its Last Column Silently

A table whose rows and header disagree on width **drops every cell past the header
count**, with no warning. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check-tables.py [root]`
after editing any table, and after adding a column.

The dropped cell is the last one, usually the payload (e.g. **Fix**). Too-short
rows render an empty cell, which reads as *absent* rather than *same on both*.

**When the rows agree with each other and only the header disagrees, fix the
header.** Ragged rows cluster around a table whose shape changed without its header.

Content, not borders: a `|` inside backticks, and an escaped `\|`. `--selfcheck` pins both.

## Which Fleet Sweeps Pay, and Four That Do Not

Propose a new checker only if the thing checked has a **decidable** definition
(fence parses, row matches header, URL resolves, version inside range). When it
does not, the false-positive rate becomes the finding.

**Do not rebuild these four semantic sweeps without a sharper idea:**

| Sweep | Why it failed |
|---|---|
| Reference files nothing points at | A pointer can be a bare filename, relative path, `[[wikilink]]`, or live in another reference. |
| Two different versions called "latest" in one file | Version-family grouping lumps unrelated products (a multi-product comparison row). |
| Cross-skill pointers that resolve to no skill | Backtick-quoted lowercase-hyphenated tokens are mostly frontmatter fields, agent types, CLI flags, component names. |
| JSON literals inside shell fences | Single-quoted `{...}` is usually kubectl JSONPath, awk, jq, a Go template or brace expansion. |

A loose sweep may be run once by hand; do not ship it.
