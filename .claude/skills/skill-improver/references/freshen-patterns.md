# Freshen Patterns — Reference Extraction & Staleness Probes

Heuristics for Freshen Mode in `SKILL.md`: reference extraction, probe templates, classification, commit format, rate limits.

## Table of Contents
- [Freshen Mode Workflow](#freshen-mode-workflow)
- [1. Reference Extraction](#1-reference-extraction)
- [2. Probe Templates](#2-probe-templates)
- [3. Classification Rules](#3-classification-rules)
- [4. Commit Message Format](#4-commit-message-format)
- [5. Rate-Limit Handling](#5-rate-limit-handling)
- [6. Worked Examples](#6-worked-examples)

## Freshen Mode Workflow

Probe a skill's external references for staleness; apply verified updates in place. Same keep/discard loop as improvement mode, but hypotheses come from online evidence, not rubric scores.

### Invocation

- `freshen <skill-path>` — single skill
- `freshen --all` — every skill returned by `scripts/scan-skills.sh`
- `freshen --group <glob>` — subset, e.g., `vllm-*`

Freshen defaults to **apply**. For a read-only readout use `ages` (fleet) or `score` (one skill; Dim 9 reflects `references/sources.md` freshness).

### Phase F0: Setup

1. Read the target skill directory (SKILL.md + `references/`).
2. Review §1 and §2 below.
3. Snapshot: `SNAP=$(mktemp -d -t <skill-name>-freshen-baseline.XXXX) && cp -a <skill-dir>/. "$SNAP"`.
4. Open a findings log: `id | ref | skill-says | current | classification | action`.

### Phase F1: Extract References

Precedence:

1. `references/sources.md` rows — authoritative refs with prior `Last verified` / `Pinned` markers.
2. SKILL.md + other reference-file scan — URLs, `owner/repo` patterns, CLI names with versions, semver strings, API paths, dated claims.
3. **The frontmatter `description` and `when_to_use`** — scan explicitly, not as part of the step-2 sweep; they carry bare factual claims.
4. Deduplicate (normalize URLs, collapse owner/repo variants).

**Bare counts in a description have nothing to age against** ("31 flag values", "98 tools"): no probe touches them. Sweep: `\b[0-9]{2,3}\+?(?:-| )(flag|parser|tool|scaler|endpoint|model|metric|value|path|feature|famil(y|ie))s?\b` plus `\b[0-9]{2,3} (are|were) \w+` over every description. Then attach a version ("30 on current vLLM, 31 through v0.27.x") or make it an explicit lower bound ("40+").

If the target has no `sources.md`, create one in Phase F6 from the extracted set.

If `description` + `when_to_use` already exceed 1,536 chars (`scripts/frontmatter-lengths.py`), add nothing to them; correct in place and name `trigger` as the next step in the F6 summary.

If the target's `sources.md` carries its own freshen protocol, follow its extra steps; where it conflicts with this file, this file wins. A row that covers a group (an issue list, a flag table) is verified member by member, batched — one query per repo.

### Phase F2: Probe — everything, batched

A pass verifies **every ref**, so the F6 stamp is true. **Delegate the sweep to cheap subagents — never run probes in the main context.** Spawn one background wave; spend main-context turns only on judgment and mutations:

- **`web-searcher`** (`model: sonnet` — Haiku row probes report false drifts; has Bash/gh/WebFetch and full browser control, so it retries bot-blocked rows per §2.4) — one per skill:
  "Verify every row of `<skill>/references/sources.md`: bulk-curl the URLs,
  batch issue/PR states via one GraphQL query per repo, check latest
  releases against the versions the rows claim. Return ONLY a findings
  table: `ref | ok|drifted|gone|blocked | evidence`, nothing else."
- **`Explore`** (read-only, has Bash) — local-clone checks: file paths, tags, symbols cited by rows, against `~/projects/github.com/<org>/<repo>`.

Batch the probes:

- URL rows → ONE bulk liveness sweep (`xargs -P 8 curl -sL -w '%{http_code}'`)
- issue/PR state rows → ONE GraphQL query per repo (aliased `issueOrPullRequest` fragments)
- repo file/tag/symbol rows → local clone under `~/projects/github.com/` (`git cat-file -e`, `git grep`)
- version rows → one release-API call per project

Give individual attention only to rows the batch flags (non-200, state changed, path gone, version moved). Per ref, run the cheapest applicable probe first (§2).

Stop early only on rate-limit (§5). A stopped pass does NOT update the stamp; the summary says why.

**Recency filter — last pass under 7 days ago.** Re-probe only row kinds that move within a week: changelogs, release tags and versions, pinned commits, package-registry rows, launch/announcement pages. Leave documentation, specification, paper and standards rows unprobed. A filtered pass must **not stamp**:

- Header-stamp files (`Freshened: <date>`): the old stamp **stands**.
- Legacy per-row files (`Last verified` column): restamp **only rows actually probed**. Never touch a skipped row.

Restamping an unprobed row disarms Dim 9's staleness cap. State in the summary that the pass was filtered and which kinds were skipped.

### Phase F3: Classify

| Class | Action |
|-------|--------|
| `fresh` | No content change (the F6 pass stamp covers it) |
| `version-drift` | Hypothesis: bump pinned version + version-specific guidance |
| `deprecation` | Hypothesis: replace deprecated API / flag with current equivalent |
| `new-feature` | Hypothesis: add a ≤3-line note IFF feature maps to an existing trigger phrase in the skill's `description` / `when_to_use` |
| `broken` | Hypothesis: update or remove the ref |
| `unverifiable` | Leave unchanged; note the ambiguity in the log. **Gated — see below.** |

Only drift, deprecation, new-feature and broken produce mutation hypotheses.

**Re-run every ABSENCE claim ("zero hits for X", "not documented", "no such flag before vN") against the snapshot it names.** An absence that was wrong never contradicts anything checkable; only a re-run catches it. When a row names a snapshot, probe **the snapshot**, not the branch tip: current-`main` evidence cannot separate "wrong then" from "changed since", and those want different fixes.

**Tag ancestry answers "did this COMMIT ship", not "did this FIX ship".** On a project that backports, the fix reaches an older patch release as a *different commit*, so `compare <tag>...<merge-sha>` reports `diverged` while the fix is in the tag. Ancestry is authoritative for a commit; release notes are authoritative for an attribution. When they disagree the project backports and both are true about different things — say which question you asked. Use the notes when the project maintains parallel stable lines.

**Gate on `unverifiable`: name the probe that failed.** The class means probes ran and came back ambiguous, not that two documents look like they disagree. Before logging it, state in the findings log which probe was run and what it returned. If that sentence cannot be written, the finding is **unverified** and the pass is not done. Two cheap probes:
- **Sibling test** — for a claim about one item in a set that shipped together, check the siblings (a change that hit `/verify` but not `/run` localizes mechanically).
- **Re-read the primary for scope** — an official doc vs official blog "conflict" is usually a scope mismatch (human workflow vs agent behaviour). Check both talk about the same actor.

**A release note describing a default change is a summary, not the code.** "Raised X from A to B" flattens conditional logic (e.g. a new device tier added above an unchanged branch). Diff the defining branch across the tags on either side (`git show <tag>:<path>`) before writing the number down.

**A reported "current HEAD" is a different ref, not a fresher reading of the tag.** Delegated probes answer at whatever ref they checked out. Record the ref beside every line number and re-measure at the tag before writing it into a tag-pinned file: `git show <tag>:<path> | grep -n '^def <symbol>'`, or the contents API with `?ref=<tag>`. Put the file's line count next to the anchor.

**An absence claim that licensed an inference is the expensive kind.** When a row says a source does not exist (e.g. "upstream publishes no support matrix"), check the source before trusting anything derived from it. Treat "we infer X because upstream publishes nothing" as a defect report, not a method; 404-pattern inference of version windows does not hold up.

**Read a published lifecycle date; never compute one.** Take support-window dates from the vendor's lifecycle page or endoflife.date, not from release-tag arithmetic (the vendor clock usually starts from a docs release date that trails the tag). When a date falls inside the next 60 days, say so in days.

**Re-test an inherited `unverifiable` flag; never carry it forward.** A row annotated "blocked — read manually" or "verify in browser" stops being probed. Re-run the escalation each pass: curl, then bare curl, then the browser. Delete the flag the moment one works, and say which did. Vendor bot-blocks and `429` to curl are common false positives that load fine in a browser.

### Phase F4: Mutate (One Finding at a Time)

Same atomicity rule as the improvement loop — one finding per iteration, diff minimal, cause attributable. Write the finding into the skill as the current rule and action. The verifying source URL, issue numbers, version history and check date go in that finding's `references/sources.md` row; the reasoning goes in the commit message. See `SKILL.md` §"Rules for every mode" (write for the agent).

### Phase F5: Accept / Revert

Verification-based decision rule:

- **Verified source + ≤ equal complexity** → KEEP (update `Pinned:`/notes if relevant). Commit per §4 below.
- **Unverified** (single unofficial source, probes ambiguous) → DISCARD. Do not guess.
- **>20 added lines for one finding** → DISCARD and flag for human review in the summary.
- **Breaks self-consistency** (orphans a section, contradicts another part) → REVERT.

### Phase F6: Stamp and Summarize

1. Before stamping, run on the target `check-links.py`, `check-issue-states.py`, `check-advisory-floors.py --verify` and `check-expiring-claims.py` (non-findings: `fleet-checks.md`), plus the §4b scaffolding decay probes. Fix each real hit as one more F4 finding.
2. Write (or update) ONE line at the top of sources.md:
   `Freshened: <today>` — plus, only if something could not be verified,
   `(exceptions: <n> rows, noted inline)`. Unverifiable rows carry a short
   inline note ("403 to curl — bot-blocked", "cookie-gated PDF"). Per-row
   `Last verified` columns are legacy: delete the column or leave it; the
   header stamp is authoritative.
3. If sources.md was absent at Phase F1, create it from the extracted refs (§1.1b) with today's stamp.
4. Print summary: total findings, kept, discarded, exceptions.
5. Stop. Do not re-probe the same skill in the same session.

**The stamp never lies.** It means "every row was verified on this date, except the ones that say otherwise inline." A partial pass keeps the old stamp.

**Restamp the table rows, not the file.** No blanket `s/<old date>/<today>/` over a sources file. Never move historical dates:

- the `<!-- Grounding note: authored <date> ... -->` comment;
- the `## <date> freshen — ...` heading of a previous pass.

Anchor the substitution to the row shape (`| ... | <date> |`), or replace each row explicitly.

### Batch Mode

`freshen --all` iterates skills sequentially:

1. Rank the fleet with `scripts/staleness-report.py` (stalest first; no probes).
2. Spawn ONE verification subagent per skill (§F2 — `web-searcher` for web/version/issue rows, `Explore` for local-clone rows), all in one background wave.
3. As each findings table returns: apply mutations for drifted rows (cap 5 findings per skill), stamp the header, move on.
4. Print ranked summary: skill, findings, kept, new stamp date — every skill from step 1 gets a row.

### Anti-Patterns

- Do NOT replace concrete guidance with "see release notes" — extract the specific change.
- Do NOT bump a pinned version without checking the breaking-change section.
- Do NOT trust a single social-media post — require an authoritative source (official docs, release notes, merged PR, maintainer issue response).
- Do NOT rewrite content unrelated to a finding.

## 1. Reference Extraction

### 1.1 Primary: `references/sources.md` rows

Each row carries the source (URL or repo path), the claim it supports, and optional `Pinned` (version or git ref). The pass verifies all of them (§F2); the header stamp (§1.1b) records when.

### 1.1b The sources.md contract — ONE stamp, full verification

The whole freshness state is a single header line at the top of sources.md:

```
Freshened: 2026-08-18
```

(optionally `Freshened: 2026-08-18 (exceptions: 3 rows, noted inline)`).

- The stamp asserts: *every row below was verified on this date*, except rows carrying an inline exception note ("403 to curl — bot-blocked", "cookie-gated PDF, needs a browser").
- **No per-row date column.** Rows carry source, what it supports, and notes; dates in notes are prose. Existing `Last verified` columns and `[LV:]` markers are legacy: `ages` reads them as a fallback until the next pass, which writes the header stamp and may delete the column.
- No `volatile` tiers, coverage percentages or `ignore-freshen` markers: the only special row state is an inline exception note.
- A partial pass does NOT update the stamp.

### 1.2 Secondary: SKILL.md and other reference files

Run each pattern against the skill directory; collect unique matches.

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

- Strip trailing slashes, URL fragments, tracking parameters.
- Collapse GitHub `owner/repo` shorthand with the full URL.
- Map version-string variants to one canonical form (`v2.1.105` ≡ `2.1.105`).
- Skip refs inside `<!-- ignore-freshen -->` HTML comments.

### 1.4 Output structure

Working set shape:

```
ref_id | kind       | location                | skill_says   | last_verified | pinned
------ | ---------- | ----------------------- | ------------ | ------------- | ------
r01    | github     | sources.md row 3        | anthropics/skills | 2026-01-10 | main
r02    | semver     | SKILL.md L42            | v2.1.105     | —             | —
r03    | cli-flag   | references/patterns.md  | --task embed | —             | —
```

## 2. Probe Templates

Run the cheapest applicable probe first. Stop probing a ref once it produces a finding.

### 2.1 GitHub release tags

```bash
gh release list -R <owner>/<repo> --limit 5 --json tagName,publishedAt,isLatest
gh api /repos/<owner>/<repo>/releases/latest --jq '{tag: .tag_name, published: .published_at}'
```

Compare latest `tagName` against `Pinned` or skill-body version strings.

**Read `isLatest`; never sort by date and never take `[0]`.** Parallel-line projects publish maintenance patches on older lines after a newer minor. Report per-line ceilings, not one number.

**An empty `gh release list` does not mean no tags.** Check `gh api repos/O/R/tags` before writing any "no releases/tags" absence claim.

### 2.2 GitHub doc / code churn

```bash
gh api "/repos/<owner>/<repo>/commits?path=<doc-path>&since=<last-verified>T00:00:00Z" \
  --jq '.[] | {sha: .sha[0:8], msg: .commit.message | split("\n")[0]}'
```

Empty = still fresh. Non-empty = flag semantic commit messages (e.g., "docs: describe new --runner flag") for review.

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

Require at least one merged PR or closed-with-resolution issue from the canonical repo before classifying as `deprecation`.

### 2.4 Live URL check

```
WebFetch <url>
```

`404`, `410`, or an unexpected redirect to an index / marketing page = `broken`. Non-canonical redirects (e.g., trailing slash) are fine.

**A bot-block is not an exception — escalate.** `402`, `403` and login walls mean *this fetcher* was refused (User-Agent block), not that the page is unverifiable. Escalate in cost order:

```bash
curl -sS -L --max-time 30 "<url>"        # 1. bare curl — no UA flag
```

Do not add a `-A` flag. If curl also fails, retry through the operator's logged-in Chrome session (`mcp__claude-in-chrome__*`: open a NEW tab, `get_page_text`, close it) — delegate to a `web-searcher`. Reserve the exception note for what survives the browser too: paywalls, deleted posts, cookie-gated PDFs.

**X/Twitter — read posts with the script, not WebFetch** (WebFetch returns `402` on every `x.com` URL):

```bash
scripts/read-x-post.py "https://x.com/<user>/status/<id>"
```

Text to stdout, `[notes: N | expanded: N | unexpanded: N]` to stderr. The script splices the full text (`__typename:"NoteTweet",text:"..."` in a `<script>` payload) over X's silent 278-char truncation. `twitter.com` needs `-L` (the script passes it). Profile URLs (no `/status/`) work too and return the ~7 most recent posts. Escalate to the browser only when stderr reports non-zero `unexpanded`, or the timeline you need is older than the profile page carries.

### 2.5 Concept / blog post search

```
WebSearch "<tool> changelog <current-year>"
WebSearch "<tool> <version> release notes"
WebSearch "<api-name> migration guide"
WebSearch "site:<official-domain> <topic>"
```

Use only when gh probes don't apply (non-GitHub tools, cross-ecosystem comparisons). Require two independent authoritative sources before producing a hypothesis.

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

**`state: CLOSED` — even `stateReason: COMPLETED` — does not mean fixed.** Inactivity bots close issues as COMPLETED. Trusting the status fields would delete a live limitation from the skill, the highest-damage error this mode can make. Read the closing comment before acting on a state change:

```bash
gh issue view <N> -R <owner>/<repo> \
  --json state,closedAt,stateReason,comments \
  --jq '"\(.state) \(.stateReason)\n\(.comments[-1].body[0:200])"'
```

Classify on the *evidence of a fix*:

| Closing evidence | Class |
|---|---|
| Names a merged PR, a release, or a maintainer confirming the fix | `deprecation` / drift — safe to update the skill |
| "automatically closed due to inactivity" / "marked as stale" | **treat as still open** — re-affirm the claim, note it is stale-closed |
| Closed as `NOT_PLANNED`, duplicate, or by the reporter with no fix | treat as still open unless the linked duplicate resolved it |

When a claim survives this check, say *why* in the skill ("shows closed, but stale-bot closed — no fix landed").

### 3.0b A tag is not a release, and "no release" is not "no version"

**`gh release list` answers "what Release objects exist", never "what versions ship".** A project can tag, publish to a registry and document a major line without a GitHub Release. Never downgrade or delete a version claim on that evidence. Before writing that a version does not exist, check **all** of:

```bash
gh api repos/<o>/<r>/tags --paginate --jq '.[].name' | grep '^v2'   # tags
gh api repos/<o>/<r>/branches --jq '.[].name'                        # release branch
curl -sS https://registry.npmjs.org/<pkg> | jq '."dist-tags"'        # registry truth
```

Registry dist-tags beat everything for "what does an install give me". Check whether the project runs **parallel lines under different package names** (e.g. v1 `opencode-ai`, v2 `@opencode/cli`); querying only the known name finds only the known line.

**If a version is installed on the machine, or the user says it exists, it exists** — find the channel rather than concluding the user is wrong. The probe was too narrow, not the claim too old.

### 3.1 Scope filter for `new-feature`

Produce a hypothesis only when the feature maps to an existing trigger phrase in the skill's `description` or `when_to_use`. Out-of-scope features are logged, NOT applied.

Example: a vLLM release adds a new benchmark mode. For `vllm-benchmarking`, add a ≤3-line note. For `vllm-caching`, log and skip.

### 3.2 Breaking-change discipline for `version-drift`

Before bumping a pinned version:

1. Fetch the release notes / CHANGELOG since the pinned version.
2. Search for "BREAKING", "breaking change", "removed", "renamed".
3. For each hit, check whether the skill body references the affected API / flag / behavior.
4. If overlap exists, classify as `version-drift` (review required), add a reviewer note to the findings log; do NOT auto-apply.

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

For multi-ref findings, list each location in a bullet list under `Before:` / `After:`.

Stamp commit (F6), last in the pass:

```
freshen(<skill-name>): stamp sources.md Freshened <date>

Rows probed: <n>. Findings applied: <n> (one commit each). Exceptions: <n>, noted inline.
```

## 4b. Scaffolding Decay Probes (Boris alignment)

Standard probes test external refs. These test whether the skill's *internal* prose compensates for old-model behaviour that current models no longer show.

### Detection patterns

Run from the skill directory:

```bash
# 1. Model-version compensation language
rg -in 'claude (tends to|sometimes|often)|always remind|model (frequently|tends)|compensate for|claude (3\.5|3\.7|opus 4\.0|sonnet 3)' SKILL.md references/ 2>/dev/null

# 2. Procedural prescription where plan mode would suffice.
# Counts scaffold items only — numbered items that carry a prohibition, named
# failure, threshold, or branch condition are encoded judgment, not scaffolding.
# See quality-rubric.md §"Procedural steps" — advisory only, no cap.
python3 "${CLAUDE_SKILL_DIR}/scripts/scaffold-probe.py" SKILL.md --verbose

# 3. Up-front context dumps (sections >30 lines of pure facts, no tool/file pointer)
awk '/^## /{if (sect) print lines, sect; sect=$0; lines=0; next} {lines++} END{if (sect) print lines, sect}' SKILL.md | sort -rn | head
```

### Classification

| Finding | Action |
|---|---|
| Version-specific reference to an old Claude release (e.g. "Claude 3.5 tends to over-eagerly call tools") | Flag for author review. Verify against current model behaviour via a quick probe. If fixed → delete the compensation. |
| Many **scaffold** items in SKILL.md body (probe's scaffold count, not its item count) | Advisory only — NO cap (rubric §"Procedural steps"). Read the list; a long sequence is correct where the operation is fragile or order is load-bearing |
| Section >30 lines of context dump with no tool/file pointer | Flag for refactor — replace bulk with a one-line pointer to where the context lives |
| All three patterns clean | Skill is Boris-aligned. Note in the freshen summary. |

### Apply via mutations

Same accept/revert treatment as URL findings (Phase F4-F5), but *deletion-favoured*: removing prescriptive content beats rewriting it; removing something with equal results is a great outcome.

## 5. Rate-Limit Handling

- `gh` returns `HTTP 403` with `X-RateLimit-Remaining: 0` when throttled.
- On first 403, pause 60 seconds and retry the same probe once.
- On second 403, stop the probe loop. Mark the skill `partial-freshen` in the summary and list the refs not probed.
- Do NOT retry in a tight loop. Do NOT fall through to unauthenticated probes.
- Batch mode: check `gh api /rate_limit --jq .resources.core.remaining` before each new skill; skip to the next skill if < 50.

## 6. Worked Examples

### 6.1 Version drift on a CLI-focused skill

Skill `gh-cli` claims "Use `gh 2.65` for `gh release view --json`." Row: `gh CLI | https://github.com/cli/cli | ... | 2026-01-10 | 2.65`.

```bash
$ gh api /repos/cli/cli/releases/latest --jq .tag_name
v2.74.0
$ gh release view v2.74.0 -R cli/cli --json body --jq .body | rg -iN 'breaking|removed'
```

No hits overlapping skill usage → `version-drift` (low-risk bump). Replace `gh 2.65` → `gh 2.74` in SKILL.md, update the sources.md row's `Pinned: 2.74`; the F6 `Freshened:` stamp carries the date.

### 6.2 Deprecated API surfaced

Skill `vllm-input-modalities` claims "Use `--task embed` to serve embedding models."

```bash
$ gh search issues "--task embed deprecated" --repo vllm-project/vllm --limit 5
#12345 Deprecate --task in favor of --runner pooling (closed, merged)
$ gh pr view 12345 -R vllm-project/vllm --json state,mergedAt,title
{"state":"MERGED","mergedAt":"2026-02-14T...","title":"Deprecate --task, add --runner pooling"}
```

`deprecation`. Replace every `--task embed` with `--runner pooling` in SKILL.md + references. Commit cites the merged PR URL.

### 6.3 Broken reference

Row `https://old-blog.example.com/post-about-skills`; `WebFetch` returns `404 Not Found` → `broken`. Remove the row from sources.md or replace with an archive.org URL if a snapshot exists. Note the removal in the findings log.

### 6.4 New feature in scope

Skill `vllm-benchmarking`, trigger "vllm bench". Latest release adds `vllm bench startup`; skill lists `vllm bench serve|throughput|latency|sweep` only → `new-feature` (in-scope). Add a ≤3-line mention; release notes URL goes in `sources.md`, not the mention.

### 6.5 Out-of-scope new feature

Skill `vllm-caching` (KV cache, prefix caching, LMCache). Release adds chat template kwargs for GPT-OSS harmony channels; no trigger phrase matches → `new-feature` (out-of-scope). Log only, do NOT mutate. Surface it in the batch-mode summary as belonging to `vllm-chat-templates`.
