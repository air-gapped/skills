# Authoring & readability — pages people (and agents) can actually read

The second pillar of this skill. The governing insight: **readability and machine-retrievability converge** — the structure that lets a human scan a page is the structure that lets a RAG/agent retrieve it. So every move here pays off twice.

## Page structure for readability

- **The page title is the H1.** So body content starts at **H2 for main sections, H3 for sub-sections.** Don't skip levels, and **don't go past ~H3/H4** — deeper headings clutter the Table of Contents and signal the page should be split. For tiny subsections use lists, not H5/H6.
- **Answer first (BLUF / inverted pyramid).** Most readers *scan* (≈79% scan rather than read word-for-word; many stop above the fold), so **front-load the conclusion**: open with a one-line summary (an Info panel works well), then detail. Write **topic-sentence-first** paragraphs so someone reading only first sentences still gets the gist.
- **Chunk.** Short paragraphs, whitespace between sections, ~60-char line widths. *"Walls of text are your worst enemy"* — they give the reader no direction.
- **Table of Contents macro on LONG pages only.** It auto-builds from heading levels (H2 nested under H1…), so disciplined headings *are* the TOC. On short pages it's needless clutter. Keep heading text short (long headings render badly in the TOC).
- **Too long → split by purpose** into child pages (also a performance win), then stitch with Children Display / Excerpt-Include so the set stays coherent rather than scattered. Keep the tree shallow.

## One page = one purpose (Diátaxis)

The canonical "one page, one type" model. Four types on two axes (study↔work × action↔cognition):

| Type | Serves | Example |
|---|---|---|
| **Tutorial** | learning (study + action) | "Get started with our API" |
| **How-to guide** | a task (work + action) | "Rotate the signing certificate" |
| **Reference** | information (work + cognition) | "Config option catalogue" |
| **Explanation** | understanding (study + cognition) | "Why we chose OpenSearch" |

*"Crossing or blurring the boundaries… is at the heart of a vast number of problems in documentation."* Typing a page fixes readability (the reader knows the mode) **and** findability (the page has one retrievable purpose). It is *"light-weight, easy to grasp"* and layerable onto Confluence today. Plus Confluence-native types: **ADRs/decision records** (short, status-stamped: Proposed/Accepted/Superseded), **runbooks** (steps + escalation, updated post-incident), **meeting notes** (dated, `@mention` actions, decisions).

**Descriptive, consistent titles** (see `findability-and-search.md`) — never "Notes"/"Meeting".

## Macros that AID vs HURT

**AID** — use deliberately:
- **Info / Note / Warning / Tip panels** — highlight the one critical point.
- **Table of Contents** — long pages only.
- **Expand** — collapse optional/supplementary detail to keep the page scannable.
- **Excerpt** — define a reusable summary once (one per page); surface elsewhere with Excerpt Include.
- **Children Display / Page Tree** — navigation/index.
- **Page Properties** — structured metadata (Owner/Review-Date/Status) feeding the governance dashboard.
- **Status lozenge**, **code block** — at-a-glance state, syntax-highlighted code.

**HURT** — *"less is more; overdoing formatting makes pages harder to read."* **Macro and table overload both clutter the page and degrade the editor** — heavy tables + many status macros can make typing lag tens of seconds, and Confluence auto-disables editor features on very large pages. **Every macro must earn its place.**

## Tables vs lists vs child pages

- **Tables** for genuine 2-D structured data (and to feed Page Properties Reports). **Keep them small** — Atlassian flags "10+ tables" or large row counts as the slow case.
- **Lists** for sequential or short items.
- **Child pages** when content is long enough to be its own purpose.
- **New-editor table regressions** to be aware of (and warn about): oversized cells, fixed line height, no compact layout, copy/paste loss of formatting/links (CONFCLOUD-67594). Practical rule: prefer fewer/smaller tables, build them fresh rather than copy-pasting, and move to lists/child pages as a table grows.

## Templates enforce readability

Templates kill the blank-page problem and standardize structure so every page of a type looks the same; **default labels on a template auto-tag every page** created from it — wiring findability and the governance dashboard in for free. *"Templates are the easiest way to prevent chaos without policing every page."* (Authoring templates is admin; the agent can still emit the same structured storage body — see `agent-execution-and-discovery.md`.)

## Authoring for an agent / RAG audience (since this skill is agent-first)

Confluence is "rarely maintained with AI in mind," yet machine-retrievability needs the **same** things as human readability:
- **Semantic headings** (so content chunks sensibly) and **descriptive titles**.
- **Labels + Page Properties** for structure an agent can filter on.
- **Put the answer IN TEXT — not locked in a screenshot, image, or attachment** (an image has nothing to embed/retrieve).
- **Descriptive link text** — no "click here" (gives neither a human nor an agent a semantic anchor).
- Avoid giant unstructured pages that chunk badly; one-page-one-purpose chunks cleanly.

## Accessibility (and it helps agents too)

- **Alt text**: succinct, no "image of…"; decorative images → blank alt; complex charts → describe in nearby text.
- **Descriptive link text** (same rule as RAG).
- **Logical heading outline** H1→H6, no skipped levels.
- **Don't rely on colour alone**; maintain contrast (**4.5:1** normal text, **3:1** large) — relevant to status lozenges and coloured table cells.
- Non-English content stays in its language — **never auto-translate or rewrite** (preserves meaning, keeps search analyzer aligned, keeps titles unique).

## Common authoring mistakes → lean fix

| Mistake | Symptom | Lean fix |
|---|---|---|
| Wall of text | No direction, low engagement | Headings + chunking + whitespace + BLUF summary |
| Vague title ("Notes") | Unfindable, collides | Descriptive, consistent, unique-per-space title |
| Giant / many-table page | Slow editor, can't scan | Split into child pages by purpose; small tables |
| Copy-paste duplication | Drift, multiple sources | Excerpt / Include from one canonical page |
| Deep burial | Critical info unreachable | Shallow curated tree; Children Display nav |
| Screenshot-only docs | Unsearchable, inaccessible, un-retrievable | Put the answer in text; alt text on images |
| Stale, no review date | Wrong answers trusted | Page Properties (Owner/Review-Date) + Report dashboard |
| Macro / formatting overload | Cluttered + laggy editor | "Less is more"; remove decorative macros |

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian Table-of-Contents / Page-Properties(-Report) / Excerpt-Include / Page-Templates macro docs; diataxis.fr; CONFCLOUD-67594 (table regressions); WCAG/accessibility KBs. Tier B: K15t make-beautiful-pages; Refined/Vectors authoring guides; Thoughtworks AI-ready KB.
