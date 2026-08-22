# Freshen Patterns — Reference Extraction & Staleness Probes

Heuristics for the Freshen Mode in `SKILL.md`. Covers reference extraction
from skill content, probe templates per reference type, classification
rules, commit format, and rate-limit handling.

## Table of Contents
- [Freshen Mode Workflow](#freshen-mode-workflow)
- [1. Reference Extraction](#1-reference-extraction)
- [2. Probe Templates](#2-probe-templates)
- [3. Classification Rules](#3-classification-rules)
- [4. Commit Message Format](#4-commit-message-format)
- [5. Rate-Limit Handling](#5-rate-limit-handling)
- [6. Worked Examples](#6-worked-examples)

## Freshen Mode Workflow

Probe a skill's external references for staleness and apply verified updates
in place. Shares the keep/discard loop with the improvement mode but sources
hypotheses from online evidence (release notes, doc commits, deprecation
signals) rather than rubric scores.

### Invocation

- `freshen <skill-path>` — single skill
- `freshen --all` — every skill returned by `scripts/scan-skills.sh`
- `freshen --group <glob>` — subset, e.g., `vllm-*`

Freshen defaults to **apply** — the loop commits verified updates. For a
read-only staleness readout, use Standalone Evaluation (Dim 9 reflects
`references/sources.md` freshness automatically).

### Phase F0: Setup

1. Read the target skill directory (SKILL.md + `references/`).
2. Review the ref-extraction heuristics (§1) and probe templates (§2) below.
3. Snapshot: `cp -a <skill-dir> /tmp/<skill-name>-freshen-baseline`.
4. Open a findings log: `id | ref | skill-says | current | classification | action`.

### Phase F1: Extract References

Precedence (extractors in §1 below):

1. `references/sources.md` rows — authoritative refs with prior `Last verified` / `Pinned` markers.
2. SKILL.md + other reference-file scan — URLs, `owner/repo` patterns, CLI names with versions, semver strings, API paths, dated claims.
3. Deduplicate (normalize URLs, collapse owner/repo variants).

If the target skill has no `sources.md`, create one in Phase F6 from the extracted set so future freshens have a baseline.

### Phase F2: Probe — everything, batched

A pass verifies **every ref**, so that the single stamp written in F6 is
true. **Delegate the sweep to cheap subagents — do not run probes in the
main context.** Spawn in one background wave, then spend main-context turns
only on judgment and mutations when findings return:

- **`web-searcher`** (cheap tier; has Bash/gh/WebFetch **and full browser control** — so it, not the main context, is what retries a bot-blocked row per §2.4) — one per skill:
  "Verify every row of `<skill>/references/sources.md`: bulk-curl the URLs,
  batch issue/PR states via one GraphQL query per repo, check latest
  releases against the versions the rows claim. Return ONLY a findings
  table: `ref | ok|drifted|gone|blocked | evidence`, nothing else."
- **`Explore`** (read-only, has Bash) — local-clone checks: file paths,
  tags, symbols cited by rows, against `~/projects/github.com/<org>/<repo>`.

The probes themselves batch, which is what makes full verification cheap:

- URL rows → ONE bulk liveness sweep (`xargs -P 8 curl -sL -w '%{http_code}'`)
- issue/PR state rows → ONE GraphQL query per repo (aliased `issueOrPullRequest` fragments)
- repo file/tag/symbol rows → local clone under `~/projects/github.com/` (`git cat-file -e`, `git grep`), free and unlimited
- version rows → one release-API call per project

Only rows the batch flags (non-200, state changed, path gone, version moved)
get individual attention — that judgment work is the real cost, and it only
scales with *drift*, not with row count. Per-ref, run the cheapest applicable
probe first (templates in §2 below).

Stop early only on rate-limit (§5). A stopped pass does NOT update the stamp
— the previous stamp stands, and the summary says why.

**Recency filter — when the last pass was under 7 days ago.** A full sweep of
a file freshened three days ago mostly re-reads specs that change on a scale
of quarters. Re-probe only the row kinds that can actually move in a week:
changelogs, release tags and versions, pinned commits, package-registry
rows, and launch/announcement pages. Leave documentation, specification,
paper, and standards rows unprobed.

The filter buys cost, and it is paid for by **not stamping**: a filtered pass
verified some rows, so it must not claim it verified all of them.

- Header-stamp files (`Freshened: <date>`): the old stamp **stands**. This is
  the same rule a rate-limited pass follows, for the same reason — the stamp
  means "every row, on this date", and a narrow pass did not do that.
- Legacy per-row files (`Last verified` column): restamp **only rows actually
  probed**. Never touch a row you skipped.

Restamping an unprobed row is the one move that must never happen. Dim 9's
staleness cap reads that date and trusts it, so a restamp on unverified
content does not merely lose information — it silently disarms the cap that
exists to catch exactly this, and the skill then scores as fresh forever.
Say in the summary that the pass was filtered and which kinds were skipped;
a filtered pass that reads as a full one is worse than no pass at all.

### Phase F3: Classify

| Class | Action |
|-------|--------|
| `fresh` | No content change (the F6 pass stamp covers it) |
| `version-drift` | Hypothesis: bump pinned version + version-specific guidance |
| `deprecation` | Hypothesis: replace deprecated API / flag with current equivalent |
| `new-feature` | Hypothesis: add a ≤3-line note IFF feature maps to an existing trigger phrase in the skill's `description` / `when_to_use` |
| `broken` | Hypothesis: update or remove the ref |
| `unverifiable` | Leave unchanged; note the ambiguity in the log. **Gated — see below.** |

Only drift, deprecation, new-feature, and broken produce mutation hypotheses.

**Gate on `unverifiable`: name the probe that failed.** The class means *probes
were run and came back ambiguous* — not *two documents look like they disagree*.
Reading sources and finding tension is the trigger for probing, not a substitute
for it. Before logging `unverifiable`, state in the findings log which probe was
run and what it returned. If that sentence cannot be written, the finding is
**unverified** and the pass is not done.

Two probes are nearly always available and cheap:
- **Sibling test** — if a claim concerns one item in a set that shipped together,
  check the siblings. A behaviour change that hit `/verify` but not `/run`
  localizes the change mechanically. (2026-07-24: settled a `/verify` chaining
  question in one command after it had been logged `unverifiable`.)
- **Re-read the primary for scope** — apparent contradictions between an official
  doc and an official blog are usually a scope mismatch, where one passage
  describes human workflow and another describes agent behaviour. Check whether
  the two are even talking about the same actor before declaring a conflict.

### Phase F4: Mutate (One Finding at a Time)

Same atomicity rule as the improvement loop — one finding per iteration, diff minimal, cause attributable. Always cite the verifying source URL.

### Phase F5: Accept / Revert

Decision rule (different from score-based loop — verification-based):

- **Verified source + ≤ equal complexity** → KEEP (update `Pinned:`/notes if relevant). Commit per §4 below.
- **Unverified** (single unofficial source, probes ambiguous) → DISCARD. Do not guess.
- **>20 added lines for one finding** → DISCARD and flag for human review in the summary.
- **Breaks self-consistency** (orphans a section, contradicts another part) → REVERT.

### Phase F6: Stamp and Summarize

1. Write (or update) ONE line at the top of sources.md:
   `Freshened: <today>` — plus, only if something could not be verified,
   `(exceptions: <n> rows, noted inline)`. Unverifiable rows carry a short
   inline note ("403 to curl — bot-blocked", "cookie-gated PDF"). That is
   the entire bookkeeping. Per-row `Last verified` columns are legacy:
   delete the column when convenient, or leave it — the header stamp is
   authoritative either way.
2. If sources.md was absent at Phase F1, create it now from the extracted
   refs (§1.1b) with today's stamp.
3. Print summary: total findings, kept, discarded, exceptions.
4. Stop. Do not re-probe the same skill in the same session.

**The stamp never lies.** It means "every row was verified on this date,
except the ones that say otherwise inline." A pass that verified only part
of the file keeps the old stamp.

### Batch Mode

`freshen --all` iterates skills sequentially:

1. Rank the fleet with `scripts/staleness-report.py` (stalest first; one
   command, no probes).
2. Spawn ONE verification subagent per skill (§F2 — `web-searcher` for
   web/version/issue rows, `Explore` for local-clone rows), all in one
   background wave. Main context stays free for judgment.
3. As each agent's findings table returns: apply mutations for drifted rows
   (cap 5 findings per skill), stamp the header, move on.
4. Print ranked summary: skill, findings, kept, new stamp date — every
   skill from step 1 gets a row.

### Anti-Patterns

- Do NOT replace concrete guidance with "see release notes" — extract the specific change.
- Do NOT bump a pinned version without checking the breaking-change section — pins often exist for reasons a diff can't see.
- Do NOT trust a single social-media post — require an authoritative source (official docs, release notes, merged PR, maintainer issue response).
- Do NOT rewrite content unrelated to a finding — each mutation is scoped to its finding.

## 1. Reference Extraction

### 1.1 Primary: `references/sources.md` rows

Each row carries the source (URL or repo path), what claim it supports, and
optional `Pinned` (version or git ref). These are the authoritative refs —
the pass verifies all of them (§F2) and the file's header stamp (§1.1b)
records when.

### 1.1b The sources.md contract — ONE stamp, full verification

The whole freshness state of a skill is a single header line at the top of
sources.md:

```
Freshened: 2026-08-18
```

(optionally `Freshened: 2026-08-18 (exceptions: 3 rows, noted inline)`).

- The stamp asserts: *every row below was verified on this date*, except
  rows carrying an inline exception note ("403 to curl — bot-blocked",
  "cookie-gated PDF, needs a browser").
- **There is no per-row date column.** Rows carry source, what it supports,
  and notes — dates in notes are prose, never bookkeeping. Existing
  `Last verified` columns and `[LV:]` markers are legacy: `ages` reads
  them as a fallback until the file's next pass, which writes the header
  stamp and may delete the column outright.
- No `volatile` tiers, no coverage percentages, no `ignore-freshen`
  markers needed: a full pass re-confirms immutable rows for free in the
  batch sweep, and the only special state a row can have is an inline
  exception note.
- A partial pass does NOT update the stamp. The stamp never lies.

### 1.2 Secondary: SKILL.md and other reference files

Extract from markdown body, code fences, and frontmatter using the
ripgrep patterns below. Run each pattern against the skill directory and
collect unique matches.

| Pattern | ripgrep | Example match |
|---------|---------|---------------|
| URL | `rg -oN 'https?://[^\s)\]>]+'` | `https://code.claude.com/docs/en/skills` |
| GitHub repo | `rg -oN 'github\.com/[\w.-]+/[\w.-]+'` | `github.com/anthropics/skills` |
| Short `owner/repo` near "github" | `rg -oN '[\w.-]+/[\w.-]+' -- <file>` (filter manually) | `anthropics/skills` |
| Semver | `rg -oN '\bv?\d+\.\d+(\.\d+)?(-[\w.]+)?\b'` | `v2.1.105`, `1.34.0`, `0.21-rc1` |
| CLI with version | `rg -oN '\b(<tool>)\s+v?\d+\.\d+(\.\d+)?\b'` | `gh 2.65`, `cargo 1.82.0` |
| Deprecation claim | `rg -iN 'deprecat|removed in|superseded by'` | `"deprecated in v0.20"` |
| Dated release claim | `rg -iN 'released?\s+(in|on)\s+\w+\s+\d{4}'` | "released in April 2026" |
| CLI flag | `rg -oN '\s\-\-[a-z][\w-]+'` | `--tool-call-parser` |
| API path | `rg -oN '/v\d+/[\w/-]+'` | `/v1/responses`, `/v1/chat/completions` |
| PyPI / crate / npm package | `rg -oN '(?:pypi\.org/project\|crates\.io/crates\|npmjs\.com/package)/[\w.-]+'` | — |

### 1.3 Normalization and dedup

- Strip trailing slashes, URL fragments, and tracking parameters.
- Collapse GitHub `owner/repo` shorthand with full `https://github.com/owner/repo` URL.
- Map common version-string variants to a single canonical form (`v2.1.105` ≡ `2.1.105`).
- Skip refs inside `<!-- ignore-freshen -->` HTML comments — author opted out.

### 1.4 Output structure

Produce a working set of this shape (in memory or scratch file):

```
ref_id | kind       | location                | skill_says   | last_verified | pinned
------ | ---------- | ----------------------- | ------------ | ------------- | ------
r01    | github     | sources.md row 3        | anthropics/skills | 2026-01-10 | main
r02    | semver     | SKILL.md L42            | v2.1.105     | —             | —
r03    | cli-flag   | references/patterns.md  | --task embed | —             | —
```

## 2. Probe Templates

Run the cheapest applicable probe first. Stop probing a ref as soon as
it produces a finding.

### 2.1 GitHub release tags

```bash
gh release list <owner>/<repo> --limit 5 --json tagName,publishedAt,isLatest
gh api /repos/<owner>/<repo>/releases/latest --jq '{tag: .tag_name, published: .published_at}'
```

Compare latest `tagName` against the `Pinned` field or skill body version
strings.

### 2.2 GitHub doc / code churn

```bash
gh api "/repos/<owner>/<repo>/commits?path=<doc-path>&since=<last-verified>T00:00:00Z" \
  --jq '.[] | {sha: .sha[0:8], msg: .commit.message | split("\n")[0]}'
```

Empty result = still fresh. Non-empty = semantic commit messages (e.g.,
"docs: describe new --runner flag") flag for review.

### 2.3 Deprecation / breaking-change signals

```bash
gh search issues "<api-or-flag-name>" --repo <owner>/<repo> \
  --state all --limit 5 \
  --match title --match body \
  --json title,url,state,labels
gh search prs "<api-or-flag-name>" --repo <owner>/<repo> \
  --state merged --limit 5 \
  --json title,url,mergedAt
gh search issues "deprecate <api-or-flag-name>" --limit 5
```

Require at least one merged PR or closed-with-resolution issue from the
canonical repo before classifying as `deprecation`.

### 2.4 Live URL check

```
WebFetch <url>
```

Treat `404`, `410`, or an unexpected redirect to an index / marketing
page as `broken`. Non-canonical redirects (e.g., `https://` → `https://`
with trailing slash) are fine.

**A bot-block is not an exception — escalate.** `402`, `403`, and login
walls mean *this fetcher* was refused, not that the page is unverifiable.
The block is usually keyed on the **User-Agent**, so escalate in cost order:

```bash
curl -sS -L --max-time 30 "<url>"        # 1. bare curl — no UA flag
```

Bare `curl` sends `curl/<version>` and is served normally by sites that
refuse `Claude-User`. Measured 2026-08-22: `x.com` posts, theatlantic.com
and newyorker.com all return `200` to bare `curl` and `402`/`403` when the
same `curl` sends `-A "Claude-User/1.0"`. Do not add a `-A` flag — the
default UA is the honest one and it is the one that works.

If curl also fails, retry through the operator's logged-in Chrome session
(`mcp__claude-in-chrome__*`: open a NEW tab, `get_page_text`, close it) —
delegate it to a `web-searcher`, which carries those tools. Reserve the
exception note for what survives the browser too: paywalls, deleted posts,
cookie-gated PDFs.

**X/Twitter — read posts with curl, not WebFetch.** WebFetch returns `402`
on every `x.com` URL. Bare curl returns the server-rendered post:

```bash
curl -sS -L --max-time 30 "https://x.com/<user>/status/<id>" \
  | python3 -c 'import html,re,sys; b=re.sub(r"(?is)<(script|style|title)\b.*?</\1>"," ",sys.stdin.read()); print("\n".join(l.strip() for l in html.unescape(re.sub(r"(?s)<[^>]+>","\n",b)).splitlines() if l.strip()))'
```

`twitter.com` URLs work too (needs `-L`). Three limits, all measured:
the `og:description` meta tag is hard-capped at 278 chars — strip the body
instead; long **replies and thread continuations** are cut at a literal
`Show more`; and **profile** URLs (`x.com/<user>` with no `/status/`) return
only a ~2.6 KB shell with no timeline. Escalate those three to the browser.

### 2.5 Concept / blog post search

```
WebSearch "<tool> changelog <current-year>"
WebSearch "<tool> <version> release notes"
WebSearch "<api-name> migration guide"
WebSearch "site:<official-domain> <topic>"
```

Use only when gh probes don't apply (non-GitHub tools, cross-ecosystem
comparisons). Triangulate — require two independent authoritative
sources before producing a hypothesis.

### 2.6 Package registries

```bash
# PyPI
gh api --hostname api.github.com /repos/<owner>/<repo>/releases/latest \
  --jq .tag_name    # if mirrored on GitHub
# OR curl (falls back to PyPI JSON)
curl -sS https://pypi.org/pypi/<package>/json | jq '.info.version'

# crates.io
curl -sS https://crates.io/api/v1/crates/<crate> | jq '.crate.newest_version'

# npm
curl -sS https://registry.npmjs.org/<package>/latest | jq '.version'
```

## 3. Classification Rules

| Evidence | Class |
|----------|-------|
| Latest release tag == pinned / skill-claimed version | `fresh` |
| Latest tag > pinned, changelog has no breaking section matching skill usage | `version-drift` (low-risk bump) |
| Latest tag > pinned, changelog breaking section overlaps skill usage | `version-drift` (review required) |
| Merged PR or closed-with-fix issue in canonical repo says "deprecate X" / "remove X" | `deprecation` |
| Official docs + one independent source confirm rename/removal | `deprecation` |
| Release notes document major feature within skill's stated trigger scope | `new-feature` |
| URL returns `4xx`, project archived, or domain dead | `broken` |
| Probes contradict, single unofficial source, or uncertain signal | `unverifiable` |

### 3.0 A closed issue is not a fixed issue

**`state: CLOSED` — even with `stateReason: COMPLETED` — does not mean the bug
was fixed.** Inactivity bots close issues and GitHub records the result as
COMPLETED. Observed 2026-07-21 in two unrelated repos on the same day:

- `sgl-project/sglang` #20184 and #17623 — both CLOSED/COMPLETED, both closed by
  *"This issue has been automatically closed due to inactivity."*
- `huggingface/transformers` #45205 — CLOSED/COMPLETED 2026-06-10, closed by
  *"automatically marked as stale because it has not had recent activity."*

In all three cases a freshen that trusted the two status fields would have
**deleted a live limitation from the skill** — the highest-damage error this mode
can make, because it removes a true warning and looks like diligent cleanup.

Always read the closing comment before acting on a state change:

```bash
gh issue view <N> -R <owner>/<repo> \
  --json state,closedAt,stateReason,comments \
  --jq '"\(.state) \(.stateReason)\n\(.comments[-1].body[0:200])"'
```

Classify on the *evidence of a fix*, not the state field:

| Closing evidence | Class |
|---|---|
| Names a merged PR, a release, or a maintainer confirming the fix | `deprecation` / drift — safe to update the skill |
| "automatically closed due to inactivity" / "marked as stale" | **treat as still open** — re-affirm the claim, note it is stale-closed |
| Closed as `NOT_PLANNED`, duplicate, or by the reporter with no fix | treat as still open unless the linked duplicate resolved it |

When a claim survives this check, say *why* in the skill ("shows closed, but
stale-bot closed — no fix landed"), so the next pass does not re-litigate it.

### 3.1 Scope filter for `new-feature`

Only produce a hypothesis when the feature maps to an existing trigger
phrase in the skill's `description` or `when_to_use`. Out-of-scope features
are logged but do NOT mutate the skill.

Example: a vLLM release adds a new benchmark mode. If the skill is
`vllm-benchmarking`, add a ≤3-line note. If the skill is `vllm-caching`,
log and skip.

### 3.2 Breaking-change discipline for `version-drift`

Before bumping a pinned version:

1. Fetch the release notes / CHANGELOG since the pinned version.
2. Search for "BREAKING", "breaking change", "removed", "renamed".
3. For each hit, check whether the skill body references the affected
   API / flag / behavior.
4. If overlap exists, classify as `version-drift` (review required) and
   add reviewer note in the findings log; do NOT auto-apply.

## 4. Commit Message Format

```
freshen(<skill-name>): <one-line finding>

Classification: <class>
Source: <url>
Before: <short quote or location>
After:  <short quote or location>
```

Example:

```
freshen(gh-cli): bump gh release-view flag requirement to v2.74

Classification: version-drift
Source: https://github.com/cli/cli/releases/tag/v2.74.0
Before: SKILL.md L87 — "gh release view --json <fields>"
After:  SKILL.md L87 — "gh release view <tag> --json <fields>" (tag now required)
```

For multi-ref findings (e.g., a deprecation that appears in three
places), list each location in a bullet list under `Before:` / `After:`.

## 4b. Scaffolding Decay Probes (Boris alignment)

The standard freshen probes test whether *external* references (URLs,
versions, deprecation claims) have rotted. Scaffolding decay probes
test whether the skill's *internal* prose has rotted relative to the
current model's behaviour.

Boris Cherny (creator of Claude Code) on the bitter lesson: scaffolding
gains "get wiped out by the next model. So it's almost better to just
wait for the next one." Skills that compensate for old-model behaviour
are the in-skill equivalent of stale external refs.

### Detection patterns

Run from the skill directory:

```bash
# 1. Model-version compensation language
rg -in 'claude (tends to|sometimes|often)|always remind|model (frequently|tends)|compensate for|claude (3\.5|3\.7|opus 4\.0|sonnet 3)' SKILL.md references/ 2>/dev/null

# 2. Procedural prescription where plan mode would suffice.
# Counts scaffold items only — numbered items that carry a prohibition, named
# failure, threshold, or branch condition are encoded judgment, not scaffolding.
# See quality-rubric.md §"Procedural steps" — advisory only, no cap.
python3 "$SKILL_IMPROVER/scripts/scaffold-probe.py" SKILL.md --verbose

# 3. Up-front context dumps (sections >30 lines of pure facts, no tool/file pointer)
awk '/^## /{if (sect) print lines, sect; sect=$0; lines=0; next} {lines++} END{if (sect) print lines, sect}' SKILL.md | sort -rn | head
```

### Classification

| Finding | Action |
|---|---|
| Version-specific reference to an old Claude release (e.g. "Claude 3.5 tends to over-eagerly call tools") | Flag for author review. Verify against current model behaviour via a quick probe. If fixed → delete the compensation. |
| Many **scaffold** items in SKILL.md body (probe's scaffold count, not its item count) | Advisory only — NO cap (rubric §"Procedural steps"). Read the list; a long sequence is correct where the operation is fragile or order is load-bearing |
| Section >30 lines of context dump with no tool/file pointer | Flag for refactor — replace bulk with a one-line pointer to where the context lives ("see `tokenizer.json` for the full vocabulary"). |
| All three patterns clean | Skill is Boris-aligned. Note in the freshen summary. |

### Apply via mutations

Scaffolding decay findings get the same accept/revert treatment as URL
findings (Phase F4-F5 of freshen mode), but the mutation is
*deletion-favoured*: removing prescriptive content beats rewriting it.
"Removing something and getting equal results is a great outcome."

## 5. Rate-Limit Handling

- `gh` returns `HTTP 403` with `X-RateLimit-Remaining: 0` when throttled.
- On first 403, pause 60 seconds and retry the same probe once.
- On second 403, stop the probe loop for that run. Mark the skill
  `partial-freshen` in the summary and list the refs that were not probed.
- Do NOT retry in a tight loop. Do NOT fall through to unauthenticated
  probes — the skill should honor the same quota.
- For batch mode, track remaining quota via
  `gh api /rate_limit --jq .resources.core.remaining` before starting a
  new skill; skip to the next skill if < 50.

## 6. Worked Examples

### 6.1 Version drift on a CLI-focused skill

**Skill:** `gh-cli`
**Claim in skill body:** "Use `gh 2.65` for `gh release view --json`."
**sources.md row:** `gh CLI | https://github.com/cli/cli | ... | 2026-01-10 | 2.65`

Probe:

```bash
$ gh api /repos/cli/cli/releases/latest --jq .tag_name
v2.74.0
```

Breaking-change check:

```bash
$ gh release view v2.74.0 -R cli/cli --json body --jq .body | rg -iN 'breaking|removed'
```

(No hits in overlap with skill usage.)

Classification: `version-drift` (low-risk bump).
Mutation: replace `gh 2.65` → `gh 2.74` in SKILL.md, update sources.md
`Pinned: 2.74` and `Last verified: <today>`.

### 6.2 Deprecated API surfaced

**Skill:** `vllm-input-modalities`
**Claim:** "Use `--task embed` to serve embedding models."

Probe:

```bash
$ gh search issues "--task embed deprecated" --repo vllm-project/vllm --limit 5
#12345 Deprecate --task in favor of --runner pooling (closed, merged)
```

Verify:

```bash
$ gh pr view 12345 -R vllm-project/vllm --json state,mergedAt,title
{"state":"MERGED","mergedAt":"2026-02-14T...","title":"Deprecate --task, add --runner pooling"}
```

Classification: `deprecation`.
Mutation: replace every `--task embed` with `--runner pooling` in SKILL.md
+ reference files. Commit cites the merged PR URL.

### 6.3 Broken reference

**sources.md row:** `https://old-blog.example.com/post-about-skills`

Probe:

```
WebFetch https://old-blog.example.com/post-about-skills
```

Returns `404 Not Found`.

Classification: `broken`.
Mutation: remove the row from sources.md, or replace with archive.org URL
if an archive snapshot exists. Note the removal in the findings log so
the author can decide whether to find a replacement source later.

### 6.4 New feature in scope

**Skill:** `vllm-benchmarking`
**Trigger phrase:** "vllm bench".

Probe:

```bash
$ gh release list vllm-project/vllm --limit 3 --json tagName,publishedAt
```

Latest release introduces `vllm bench startup`. The skill currently lists
`vllm bench serve|throughput|latency|sweep` but not `startup`.

Classification: `new-feature` (in-scope — "vllm bench" is a trigger).
Mutation: add a ≤3-line mention of `vllm bench startup` in the
appropriate section. Cite release notes URL.

### 6.5 Out-of-scope new feature

**Skill:** `vllm-caching`
**Trigger phrases:** all about KV cache, prefix caching, LMCache, etc.

Probe surfaces: vLLM release adds new chat template kwargs for GPT-OSS
harmony channels.

Scope check: no trigger phrase in the skill matches chat templates or
harmony channels.

Classification: `new-feature` (out-of-scope).
Action: log only — do NOT mutate. The finding belongs to the
`vllm-chat-templates` skill; surface it in the batch-mode summary so the
author can freshen that skill next.
