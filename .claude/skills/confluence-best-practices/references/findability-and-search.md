# Findability — search, labels, titles, navigation

"I can't find anything" is the #1 Confluence complaint — and the cleanest diagnosis is that it is the **content, not the engine**: the engine has author/label/space/type filters Notion lacks; the experienced terribleness comes from un-archived stale content polluting results. *"Confluence search isn't that bad. What's bad is the data that's fed into it."* So the fixes are corpus hygiene, not a new search engine.

## Titles — the cheapest findability lever (and a hard constraint)

- **Page titles must be unique within a space.** `(space key + title)` is assumed to uniquely identify a page across macros, APIs, and the UI. A rename/create that collides throws *"A page with this name already exists in this space"* — and the check spans **restricted pages the user can't even see** (and duplicate drafts), so a rename can fail against an invisible conflict.
- Because `title` is a first-class CQL field and must be unique, **distinctive, descriptive, consistently-prefixed titles are the single cheapest findability win** — e.g. `RUNBOOK – Payments – Failover`, `ADR-014 – Adopt OpenSearch`. Avoid generic titles ("Notes", "Meeting", "Untitled") that collide and rank poorly.

## Labels — a small controlled vocabulary

- **Mechanics:** labels are forced **lowercase, no spaces (a typed space splits into separate labels or is hyphenated), only `_` and `-`, ≤255 chars.** So `Q3 Planning` → `q3-planning`; a multi-word non-English tag like `Vertrieb Nord` → `vertrieb-nord`.
- **Best practice:** plan a **small, documented, singular-form** vocabulary that maps to how people search; maintain it on a tracking page; **pre-load labels into templates** so pages are born tagged (the highest-leverage label automation); review drift with the **Labels List** macro.
- **Labels power findability three ways:** CQL `label =` filtering; the **Content by Label / Content Report Table** macros (list/table of matching pages); and **Page Properties Report** aggregation (the governance dashboard in `lean-content-and-lifecycle.md`).
- **Space categories are labels on spaces** — the same controlled-vocabulary discipline applies to organising the Space Directory.

## Navigation beats search for known content

- The **page-tree sidebar**, a **curated homepage** (Children Display / Page Tree / label indexes), and the **Space Directory** reduce reliance on weak search. Good navigation + shallow, well-named trees is complementary to search, not a competitor.
- Lean default: **shallow well-named trees + one curated landing page per space.** (Tree shape is in `information-architecture.md`.)

## CQL — the agent's discovery & governance surface

Confluence Query Language: `field operator value`, boolean `AND/OR/NOT`, `ORDER BY`. Key fields:

| Field | Use |
|---|---|
| `text ~ "term"` | broad net across title + body + labels |
| `title = "exact"` / `title ~ "fuzzy"` | exact vs contains |
| `label = x` / `label IN (a,b)` | label filter (exact, no wildcard) |
| `space = KEY` / `space.category` / `space.type` | scope |
| `type IN (page, blogpost, comment, attachment)` | content type |
| `ancestor = ID` (all descendants) vs `parent = ID` (direct children) | hierarchy |
| `created` / `lastModified` + `startOfDay()`/`now()` | recency (date format `"yyyy/MM/dd HH:mm"`) |
| `creator` / `contributor` / `mention` / `watcher` + `currentUser()` | people |

Governance examples: stale = `type=page AND lastModified < startOfYear()`; by space = `space = "OPS" AND type = page`. Full agent recipes (no-label, duplicates, orphans) are in `agent-execution-and-discovery.md`.

## Search & indexing internals — set expectations, don't over-promise

The engine is **Apache Lucene** by default; **OpenSearch is DC-only, opt-in, since Confluence 9.0** — ~4.5× faster but **"the same search experience," perf-not-relevance** (it does NOT improve recall, stemming, or fix the bugs below). It needs a separate cluster + reindex; recommend it for speed/HA on large instances, never as a "can't find anything" cure.

**The Indexing Language setting** (Admin → General Configuration → Formatting & International Settings) is **instance-wide** (not per-space) and controls **stemming + stop-words**; **changing it requires a full reindex.** Options include English (default), German, French, Russian, Chinese, **CJK**, **Custom Japanese**, etc.

**Search behaviour & traps:**
- **Whole-word / stemmed by default** — exact-substring search is off unless a sysadmin enables the `confluence.search.improvements.exact` dark feature + reindex.
- **Stop-words are stripped even inside quoted phrases** (`"the it crowd"` drops "the"/"it").
- **Special characters aren't indexed** — `"DOC-8510"` searches `doc AND 8510` (the classic "why can't I find my ticket key" trap).
- **Wildcards:** trailing `*`/`?` supported; **no leading wildcard** (`*term` fails — regex `/.../ ` workaround); **wildcards don't stem** (`Managemen*` matches far less than `Management`).
- **Accents:** plain-term **accent folding works** since 6.10.0 (search `majore` finds `majoré`), BUT **umlaut/accent + wildcard is broken** (`Mikrohä*` finds nothing though `Mikrohärtemessung` is indexed — CONFSERVER-17138, still open). Prefer whole indexed terms for accented content.
- **CJK** uses **bigram tokenization** (overlapping 2-char grams) and **exact (quoted) search is disabled by default** for Chinese/Custom Japanese/CJK (no whitespace word boundaries) — single-character CJK queries and phrase matching behave unintuitively.

When a user's search "isn't finding things," suspect these limits before assuming the data is missing — and remember the most common real cause is a **stale, un-archived corpus** or an **inherited view-restriction** hiding the page (see `permissions-and-governance.md`).

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian "Configuring Search", "Configuring Indexing Language", "Confluence Search Syntax", "OpenSearch for Confluence DC"; CQL Field Reference; Page Properties Report macro; unique-title KB + CONFSERVER-2524/5926; CONFSERVER-17138 (umlaut+wildcard), -22495 (accent folding). Tier B: Atlassian Community/HN "content not engine"; K15t labels.
