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

Mark rows with `<!-- ignore-freshen -->` to exclude refs the author deliberately keeps as-is (e.g., historical references).

### Phase F2: Probe

For each ref, run the cheapest applicable probe first (templates in §2 below). Stop probing a ref as soon as it produces a finding.

Default probe budget: **20 per skill, 100 per batch run**. On budget exhaustion, stop probing and summarize; flag the skill `partial-freshen` in the log.

### Phase F3: Classify

| Class | Action |
|-------|--------|
| `fresh` | Stamp `Last verified: <today>` on the sources.md row; no content change |
| `version-drift` | Hypothesis: bump pinned version + version-specific guidance |
| `deprecation` | Hypothesis: replace deprecated API / flag with current equivalent |
| `new-feature` | Hypothesis: add a ≤3-line note IFF feature maps to an existing trigger phrase in the skill's `description` / `when_to_use` |
| `broken` | Hypothesis: update or remove the ref |
| `unverifiable` | Leave unchanged; note the ambiguity in the log |

Only drift, deprecation, new-feature, and broken produce mutation hypotheses.

### Phase F4: Mutate (One Finding at a Time)

Same atomicity rule as the improvement loop — one finding per iteration, diff minimal, cause attributable. Always cite the verifying source URL.

### Phase F5: Accept / Revert

Decision rule (different from score-based loop — verification-based):

- **Verified source + ≤ equal complexity** → KEEP. Update sources.md with new `Last verified:` (and `Pinned:` if relevant). Commit per §4 below.
- **Unverified** (single unofficial source, probes ambiguous) → DISCARD. Do not guess.
- **>20 added lines for one finding** → DISCARD and flag for human review in the summary.
- **Breaks self-consistency** (orphans a section, contradicts another part) → REVERT.

### Phase F6: Stamp and Summarize

1. Any ref that probed successfully — fresh or updated — gets `Last verified: <today>` in sources.md.
2. If sources.md was absent at Phase F1, create it now from the successfully-probed refs.
3. Print summary: total findings, kept, discarded, unverifiable, flagged-for-review.
4. Stop. Do not re-probe the same skill in the same session.

### Batch Mode

`freshen --all` iterates skills sequentially:

1. Scan scope via `scripts/scan-skills.sh`.
2. Rank by sources.md staleness (oldest `Last verified:` first; missing dates sort last).
3. Cap findings-per-skill at 5 in batch mode.
4. Share the 100-probe global budget across the batch; stop early on exhaustion.
5. Print ranked summary: skill, findings, kept, new stamp date.

### Anti-Patterns

- Do NOT replace concrete guidance with "see release notes" — extract the specific change.
- Do NOT bump a pinned version without checking the breaking-change section — pins often exist for reasons a diff can't see.
- Do NOT trust a single social-media post — require an authoritative source (official docs, release notes, merged PR, maintainer issue response).
- Do NOT rewrite content unrelated to a finding — each mutation is scoped to its finding.

## 1. Reference Extraction

### 1.1 Primary: `references/sources.md` rows

Each row carries `URL`, `Last verified` (YYYY-MM-DD), and optional `Pinned`
(version or git ref). These are the authoritative refs — probe them first
and stamp their dates on success.

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

# 2. Procedural prescription where plan mode would suffice
# (numbered lists in the SKILL.md *body*, not reference content)
rg -c '^\s*\d+\. ' SKILL.md

# 3. Up-front context dumps (sections >30 lines of pure facts, no tool/file pointer)
awk '/^## /{if (sect) print lines, sect; sect=$0; lines=0; next} {lines++} END{if (sect) print lines, sect}' SKILL.md | sort -rn | head
```

### Classification

| Finding | Action |
|---|---|
| Version-specific reference to an old Claude release (e.g. "Claude 3.5 tends to over-eagerly call tools") | Flag for author review. Verify against current model behaviour via a quick probe. If fixed → delete the compensation. |
| Procedural step list of 8+ items in SKILL.md body | Flag — likely Dim 6 cap candidate. Recommend extracting to `references/runbook.md` or deleting if plan mode would cover. |
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
