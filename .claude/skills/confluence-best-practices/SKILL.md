---
name: confluence-best-practices
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Advise on USING Confluence well, not operating it: make the structural call — is this a space, a page, or a child page? — diagnose why a wiki is a dread (can't find anything, content rots, duplicates, hidden by permissions, unreadable), and recommend the lean fix. Built FIRST for an agent that ACTS on Confluence (creates/organises/governs content via REST/CQL or an MCP server) and SECOND for helping humans author readable pages. Self-hosted Server/Data Center first (storage format NOT ADF; no native page archive; REST v1), but works for Cloud too. Adapt to the org's own space conventions and working language; never auto-translate content. Covers ALL content types — knowledge base, docs, intranet, meeting notes, runbooks, decision records.
when_to_use: |-
  Use whenever the user asks "should this be a space or a page", "where should this doc go", "how do we structure our Confluence/wiki", or wants Confluence leaner / findable / less of a graveyard — even if Confluence isn't named. Fires on "our wiki is a mess / can't find anything / full of stale pages", "duplicate pages everywhere", "organise our spaces", "a page won't show up / permissions hiding pages", "make this page readable", "structure a runbook / KB / decision record", "confluence best practices", "clean up Confluence", "archive old pages", "agent to create or update Confluence pages". NOT for installing the mcp-atlassian server (→ jira-confluence-mcp), Jira usage (→ jira-best-practices), or Cloud-only features (Whiteboards, Rovo AI, Databases, automation rule-builder).
---

# confluence-best-practices — use Confluence leanly, structure content sensibly, write it readably

Primary reader: an **agent helping a user** — one that *acts on* Confluence (creating, organising, and governing content) and advises the user on **how to use Confluence well**: what a piece of content *is*, where it *goes*, how to keep the wiki lean and findable, and how to make pages people can actually read. This is the **judgment layer** above the execution mechanics — it decides *what* should change and *how content should be structured*; the tools do the *how*.

Two audiences, in priority order: **(1) an agent acting automatically** on Confluence (the main case), and **(2) a human authoring content** who wants it readable. The good news is these converge — the structure that makes a page scannable for a person is the same structure that makes it retrievable for an agent.

This skill is **instance-agnostic and organisation-adaptive**. It never assumes a team's space taxonomy, conventions, or working language — it shows how to *discover* the org's actual conventions and reason within them. It is **self-hosted-first**: defaults are for **Confluence Data Center 10.2 / 9.2 LTS**, but everything has a **Cloud** counterpart noted inline (see the Cloud-vs-DC guard).

## How the work gets done (execution layer)

An agent here acts through **content-level REST/CQL** — directly, or via an MCP server (e.g. `mcp-atlassian`), or by handing the user UI steps. The boundary that determines what to *do* versus what to *advise* is the same on every instance:

- **What an agent DOES directly** (content level, no admin rights): create/update/move/delete pages and blog posts; re-parent a page; add/remove **labels**; add comments; set/read **page restrictions**; run **CQL** searches; read the page tree; build a **Page Properties Report** governance dashboard. All of this is `POST/PUT/GET` against `/rest/api/content` (DC) or `/wiki/api/v2/pages` (Cloud).
- **What an agent ADVISES the human to do** (admin / global config — *not* doable at content level): create a **space** and set its permission scheme; set **default space permissions**; restrict who can **create spaces**; build **templates/blueprints**; set the **indexing language**; configure **retention rules**; install apps. For these, hand the user the exact, minimal steps (the reference files carry the DC click-paths) rather than attempting them via a tool.

So a good response usually = **(a)** the correct content action taken via REST/CQL, plus **(b)** a crisp, copy-pasteable recommendation for anything that needs an admin. This skill decides *what* and *how to structure content*; it is **not** a manual for any one tool — for setting up the `mcp-atlassian` server itself, that's the `jira-confluence-mcp` sibling skill.

## The prime directive

Most Confluence dread is a **usage** problem, not a tool problem. The wikis that work are the ones with the *least unmanaged sprawl*. So, every time:

1. **Lean by default.** The right answer is almost always *fewer and shallower* — fewer spaces, shallower page trees, fewer macros, one home per page, less duplication. Creating content is frictionless; *retiring* it takes a deliberate act, so a wiki only grows unless someone prunes. When in doubt, recommend consolidating, archiving, or removing.
2. **Adapt to the org, never impose.** Organisations legitimately organise spaces by team, by project, by function, or by product — all valid. Discover *their* space roles, label vocabulary, and working language, and reason in *their* terms. Describe structure by **role** ("a space is a *container + permission boundary*; a page is *content*"), then map to what they actually call it.
3. **Readability is a first-class outcome — and it doubles as agent-retrievability.** Answer first, one page = one purpose, the answer in *text* (not buried in a screenshot) — the same moves serve the human reader and the RAG/agent retriever.
4. **Non-English is fully normal.** Content and labels are frequently in a local language. **Never auto-translate or rewrite a user's content.** Discover the instance's real values and anchor logic on language-independent keys (space **key**, content **ID**, label text, CQL fields).
5. **Diagnose before prescribing.** Name the specific dread — *can't find it / it's rotting / it's duplicated / it's hidden / it's unreadable* — trace it to a cause, then propose the smallest fix. Don't redesign the whole space when one inherited restriction is the problem.

## Cloud vs Data Center — speak the right dialect (read this first)

Most "new Confluence" coverage describes **Cloud**, and the DC gap is wide enough that wrong-dialect advice is unusable. This skill is **DC-first, Cloud-compatible** — know both columns. The single biggest trap is the **editor and content format**.

| Concept | Confluence **Cloud** (2026) | Confluence **Data Center** 10.2 / 9.2 (default) |
|---|---|---|
| Editor / content model | Fabric editor; content model **ADF** | own **TinyMCE-based** editor; content model **storage format (XHTML-based)**. **ADF does NOT apply to Confluence DC** — and even on Cloud, *storage format* is the portable write target. |
| Page archiving | native, **per-page** (`… > Archive`) | **space-level only** — no native page archive (CONFSERVER-31010); use the move-to-archive-space workaround |
| AI | **Rovo / Atlassian Intelligence** built in | **none native** — DC reaches Cloud AI only via connectors. Don't depend on AI. |
| Automation | native **Confluence automation** rule-builder | **not native** — use Jira automation, an app, or the agent itself |
| Whiteboards / Databases / Smart Links / Guests / public links / page status | available | **none on DC** |
| REST API | v1 **and v2** (`/wiki/api/v2`, cursor paging) | **v1 only** (`/rest/api/content`, `start/limit`) |
| User identifier | **`accountId`** | **`username` / `userKey`** |
| **Bundled on BOTH** (don't mis-flag): Team Calendars, collaborative editing (≤12 editors), Analytics for Confluence (DC: "limited") | — | — |

DC status (re-checked 2026-07-21): LTS lines **10.2** (→2027-12-02, Java 21 only) and **9.2** (→**2026-12-10 — under 5 months away**, plan the 10.2 hop now); Server EOL'd 2024-02-15. **Exact latest patch: re-derive.** The skill recorded 10.2.13 (2026-06-02); Atlassian's docs show a further 10.2.x around 2026-07-09, but the release-summary page lists only minor lines, so the current patch number was not resolvable this pass — read it off the instance or the 10.2 release-notes page rather than quoting a number from here. DC is on a sunset path (sale-end 2026-03-30, read-only EOL 2029-03-28) — note it honestly if asked, but this skill is about using *today's* Confluence well, not migrating.

To tell which applies, check the REST base path: `/wiki/api/v2/...` works → Cloud; only `/rest/api/content` → DC. Full feature-split matrix in **`references/cloud-vs-dc.md`**.

## Information architecture — space, page, or child? (by role, not by name)

The single most common Confluence question is *"where do I put this?"* — the analogue of Jira's "is this an epic or a story?" Internalise the primitives and the decision:

```
   Space            CONTAINER + permission/ownership boundary — its own homepage, sidebar, admin
     │
   Page             a UNIT OF CONTENT (one purpose)
     │
   Child page       a page with exactly ONE parent (the tree is single-parent)
```

**The decision heuristic:**
- **New SPACE** only when the content has a distinct owning team/project, needs its *own permission scheme*, and should stand alone in the Space Directory. A space is heavyweight (permissions + homepage + admin), so **"a space per tiny project" is the dominant clutter anti-pattern.** Sharpest tie-breaker: **don't create a space just to hide a few pages — use page restrictions instead** (they're more granular than space permissions).
- **PAGE in an existing space** is the lean default for most new content.
- **CHILD page** only when it logically belongs *under* one specific parent. The tree is **single-parent** — if content belongs to several categories, **label it; never duplicate it into two parents.**

**Describe by role, map to the org's names.** DC's space *types* (team / knowledge-base / documentation / personal) are just starter templates that "don't really have much effect once created." So reason in **roles** — *home, project-workspace, reference-KB, personal-scratch, department-intranet, meeting-notes* — detect which role a space plays, and adapt to whatever the org named it. The one near-universal rule is **consistency by type**: spaces of the same role should be named alike and share a top-level structure.

**Tree shape: shallow.** Cap depth at **~3, maybe 4 levels** — Atlassian ships an official "too many nesting levels" health check confirming deep trees have a real *performance* cost (and deep pages get neglected, "out of sight, out of mind"). Every space needs a **homepage** that orients and routes (overview + key links + label indexes). Re-home **orphan pages** (no parent, no inbound links).

**Labels = cross-cutting; tree = containment** (the analogue of "hierarchy rolls up, links don't"): the tree answers *"where does this live"* (one place); labels answer *"what is this about"* (many facets, and they reach across spaces). The same split exists for spaces — **space categories are just labels on spaces.**

Full treatment (the space-vs-page checklist, role table, folders caveat, orphan/depth fixes): **`references/information-architecture.md`**.

## Discover before advising (and stay language-safe)

A recommendation that hardcodes a space *name*, a page *title*, or an English label is wrong on the next instance — and doubly wrong on a non-English one. **Discover the org's real values, and anchor logic on language-independent keys.**

| To learn… | How (tool-agnostic) | Language-safe anchor |
|---|---|---|
| Spaces + keys + categories | `GET /rest/api/space?expand=metadata.labels` (DC); v2 `/spaces` (Cloud, but categories need a v1 call) | space **`key`** (immutable, a-z/0-9, forms the URL) |
| Page tree / ancestors | `/content/{id}/child\|descendant/page`, `?expand=ancestors`; DC `/content/scan` | numeric **content `id`** |
| Labels actually in use | per page `/content/{id}/label`; instance-wide → CQL-facet | **label text** (lowercase, no spaces, only `_`/`-`) |
| Available templates | `/rest/api/template/page\|blueprint` | template id |
| What content really says | request **`body.storage`** | — |
| Indexing language | **not REST-exposed** — admin setting | (advise only) |

**The rules that prevent localized-content bugs:**
1. **Anchor on keys, not display strings.** The space **key**, numeric **content ID**, **label text**, **CQL field names**, and **content-type** survive a localized UI and per-user display language. The space *name* and page *title* do not — never use them as durable lookup keys.
2. **Write in the instance's working language.** Set summaries/titles/labels in that language; never auto-translate. (Labels force lowercase and disallow spaces, so a multi-word non-English tag like "Vertrieb Nord" must become `vertrieb-nord`.)

The full discovery recipe, the act-vs-advise mapping, programmatic-write safety (storage format, the unique-title idempotency key, version-increment/409, not clobbering human formatting), CQL governance recipes, and the Cloud-vs-DC execution branches are the operational heart of this skill: **`references/agent-execution-and-discovery.md`**.

## Lean content & lifecycle — fighting the "graveyard"

The named dread is *"Confluence is where documentation goes to die."* The mechanism is structural: creation is free, retirement is manual, so content rots silently (there's no test that goes red when a runbook references a dead service). De-bloat with these levers, highest-leverage first:

1. **Make ownership + staleness visible — the agent-buildable governance dashboard.** Put a **Page Properties** macro (Owner / Review-Date / Status) on content pages + a shared label, then a **Page Properties Report** index page keyed on that label. This is the single highest-leverage *no-admin* pattern — the agent can build it entirely at content level. (Caps: 3,000 pages / 60 labels, tunable.)
2. **Find rot with CQL.** `type=page AND lastModified < startOfYear()` (scope by space/owner), plus "no labels" and duplicate-title sweeps. Agent-actionable.
3. **Kill duplication with transclusion, not copy-paste.** **Excerpt + Excerpt Include** (a snippet) and **Include Page** (a whole page) keep one canonical source; edit once, every reference updates.
4. **Prune in the right order:** trash + version-retention rules → **move obsolete pages to an archive space** → archive that space → delete (with an XML export) only to reclaim index/DB.
5. **The DC lifecycle gotcha:** **DC has NO native page-level archiving** (Cloud does). Space archiving excludes a space from search/Directory but **keeps it in the index** (a relevance lever, not a perf one). To "archive a page" on DC, move it into a dedicated archive space — and note that **pages cannot be moved into an already-archived space** (flip it to Current first).
6. **The one hard guardrail:** **< 8,000 spaces** is optimal on DC (8–10k approaching, >10k degraded — driven by permission checks). Pages are *not* a primary perf axis; but very large, macro/table-heavy pages break the editor — split them.

Mechanics (retention rules, archive workaround, the dashboard storage format, performance numbers): **`references/lean-content-and-lifecycle.md`**.

## Findability — search, labels, titles, navigation

"I can't find anything" is the #1 complaint — and it's the **content, not the engine** (*"Confluence search isn't that bad; what's bad is the data fed into it"*). Fix the corpus:

- **Titles are the cheapest lever** — and **page titles must be unique within a space**, so make them distinctive and consistently prefixed (`RUNBOOK – Payments – Failover`), never generic ("Notes", "Meeting").
- **Labels as a small controlled vocabulary** (lowercase, no spaces, singular), **pre-loaded into templates** so pages are born tagged.
- **Navigation beats search** for known content: shallow well-named trees + a curated **homepage** (Children Display / label indexes) + the Space Directory.
- **CQL** is the agent's discovery surface (`text`, `title`, `label`, `space`, `type`, `ancestor`/`parent`, `lastModified`, `creator`).
- **Search caveats to set expectations:** whole-word/stemmed by default; stop-words stripped even in quotes; **special chars stripped** (`DOC-8510` → `doc AND 8510`); **no leading wildcard**; **CJK** uses bigram tokenization with exact-search off; umlaut+wildcard is broken (but plain-term accent folding works). OpenSearch (DC, opt-in since 9.0) is *faster, not more relevant*.

Full CQL field reference, label governance, and the indexing/language caveats: **`references/findability-and-search.md`**.

## Authoring & readability — make pages people (and agents) can read

The second pillar. The same structure serves human scanning and machine retrieval:

- **The page title is the H1**, so body content starts at **H2 → H3** (don't skip levels; cap ~H3/H4). A **Table of Contents** macro pays off on *long* pages only.
- **Answer first** (BLUF / inverted pyramid — most readers scan, not read). Open with a one-line summary (an Info panel), write topic-sentence-first paragraphs, **chunk** into short sections.
- **One page = one purpose** (Diátaxis: *tutorial / how-to / reference / explanation* — mixing types is the root of most doc problems). Plus ADRs, runbooks, meeting notes.
- **Macros earn their place.** Info/note/warning panels, Expand, Excerpt, Children Display *help*; **macro/table overload clutters and degrades the editor.** Keep tables small (the new editor has table regressions).
- **Author for retrieval too:** put the answer **in text, not only in a screenshot/attachment**; descriptive link text (no "click here"); labels + Page Properties for structure.
- **Accessibility:** alt text, descriptive links, real heading semantics, don't rely on colour alone.

The mistakes→fix table, Diátaxis mapping, macro guidance, and storage-format snippets: **`references/authoring-and-readability.md`**.

## Permissions & governance, and the Jira boundary

- **Three layers:** global (can-create-spaces, admin) → space (view/add/edit) → page restrictions. Space permissions are **additive**; page restrictions **subtract — they narrow, never grant** (a restriction can deny a user with space-View, but can't give View to someone who lacks it).
- **View restrictions cascade to child pages; edit restrictions do NOT.** This makes **an inherited view-restriction on an *ancestor* the #1 cause of "I can't find/see the page"** — the page silently drops from search and the tree. Diagnose by walking *up* the tree.
- **Open by default.** Atlassian's own stance: "keep Confluence as open as possible." Restriction is the justified exception (HR/legal/security), not the posture; over-restriction creates silos.
- **Governance levers (advise-the-human):** restrict **`Create Space(s)`** to a champions group (whoever creates a space becomes its admin → sprawl); set default new-space permissions; **use groups, not individuals**.
- **The Jira boundary:** **Confluence = durable knowledge** (requirements, decisions, design docs, runbooks, the how-and-why); **Jira = trackable work with status.** Link them with the permission-aware **Jira Issues macro** (live status on the page). Note **Smart Links are Cloud-only**.

Permission mechanics, the "can't see the page" playbook, and integration: **`references/permissions-and-governance.md`**.

## Diagnose-the-dread playbook

Match the symptom, name the cause, apply the smallest fix:

| Symptom the team reports | Likely root cause | Lean fix |
|---|---|---|
| "I can't find anything" | Polluted corpus — stale pages, thin metadata, generic titles | Archive dead spaces; distinctive titles; controlled labels; curated homepages — not a new search engine |
| "A page won't show up / I can't see it" | Inherited **view restriction on an ancestor** | Walk *up* the tree; verify space-View; remove/adjust the ancestor restriction |
| "Our wiki is a graveyard / full of stale pages" | No ownership, no review cadence, no retirement | Page Properties (Owner/Review-Date) + Page Properties Report dashboard; CQL rot sweep; archive workaround |
| "Same info is in five places" | Copy-paste instead of reuse | Excerpt/Include from one canonical page; a "what-belongs-where" note |
| "Where do I put this?" | Space-vs-page decided ad hoc | Teach the role-based decision; page (not space) by default; label don't duplicate |
| "This page is a wall of text" | No structure, no front-loading | H2/H3 headings + BLUF summary + chunking; split by purpose; ToC on long pages |
| "Confluence is slow / the editor lags" | Too many spaces (>8k) or a giant macro/table-heavy page | Audit/consolidate spaces; split heavy pages; fewer macros |
| "We track tasks in Confluence and it's always stale" | Using a wiki as a tracker | Move status to Jira; embed the Jira Issues macro for live status |
| "Non-English search/labels misbehave" | Matching localized strings; wildcard/CJK limits | Anchor on space key / content ID / label / CQL; set expectations on search limits |

## Anti-patterns (call these out)

1. **A space per tiny project** — use a page; reserve spaces for real audience/permission boundaries.
2. **Duplicating a page under two parents** — label it; the tree is single-parent.
3. **Deep page trees (5+ levels)** — cap at 3–4; promote subtrees to siblings or a new space.
4. **Pages with no owner and no review date** — invisible rot; add Page Properties + a Report dashboard.
5. **Copy-pasting shared content** — use Excerpt/Include; one canonical source.
6. **Over-restriction** — silos and "can't find it"; open by default, restrict only what's genuinely confidential.
7. **Generic titles ("Notes", "Meeting")** — collide (unique-per-space) and rank poorly; be descriptive.
8. **Macro/table overload** — clutters and lags the editor; every macro must earn its place.
9. **Answers locked in screenshots/attachments** — unreadable to search and to agents; put the answer in text.
10. **Auto-translating or "correcting" non-English content** — never; it's normal, preserve it, anchor on keys.
11. **Treating ADF as the Confluence write format** — it's Jira-Cloud; Confluence writes are **storage format** on both Cloud and DC.

## What to read next

| File | Read when… |
|---|---|
| `references/information-architecture.md` | Deciding space vs page vs child; setting a space-role standard; tree depth; labels-vs-tree; orphans; folders |
| `references/lean-content-and-lifecycle.md` | De-bloating — wiki rot, the <8,000-spaces guardrail, archive-space workaround + retention, the Page-Properties-Report dashboard, Excerpt/Include, CQL pruning |
| `references/findability-and-search.md` | Findability — CQL field reference, label vocabulary, unique titles, search/indexing caveats (CJK, wildcard), OpenSearch |
| `references/authoring-and-readability.md` | Writing readable pages — headings/ToC/BLUF, Diátaxis page-typing, macros that earn their place, tables, templates, accessibility, agent-retrievability |
| `references/permissions-and-governance.md` | Permissions (3-layer model, cascade, "can't see the page"), governance levers, and the Confluence↔Jira boundary + macros |
| `references/agent-execution-and-discovery.md` | Acting on Confluence as an agent — discovery, act-vs-advise, storage-format writes + idempotency/version safety, CQL recipes, language-safe anchors, Cloud-vs-DC branches |
| `references/cloud-vs-dc.md` | Versions/EOL/sunset; the Cloud-only / DC-only / both feature matrix; the editor & storage-format situation |
| `references/sources.md` | Verifying or freshening a claim — per-row source + tier + what it supports |

**Execution:** to *carry out* any of this (creating pages at the right place, moving/labelling, restrictions, CQL, the dashboard), act through content-level REST/CQL — directly or via an MCP server. This skill decides *what* and *how to structure content*; the tool does the *how*. Anything needing admin (spaces, permissions, templates, indexing, retention) → hand the user the exact steps.
