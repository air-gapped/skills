# Lean content & lifecycle — fighting the "graveyard"

The "Confluence is where documentation goes to die" dread is a **content-lifecycle** problem: creation is frictionless, retirement is a deliberate act, so content only grows and rots unless someone prunes. This file has the numbers and the concrete Data Center mechanics to fix it.

> **Who does what.** The agent acts at **content level** (create/move/label pages, build a Page Properties Report, run CQL sweeps, transclude with Excerpt/Include). **Retention rules, space archiving, default permissions, and template authoring are admin** — diagnose the bloat and hand the user the exact steps. Cloud differences are flagged inline.

## The graveyard mechanism (name it precisely)

Docs decay from the moment of publishing, and Confluence has **no native staleness signal** — nothing goes red when a runbook references a dead service. Over time a wiki accumulates orphaned pages nobody owns, contradictory duplicates, and spaces untouched for years. This is the Confluence analogue of Jira's field/workflow bloat: in Jira the tax is on every issue; in Confluence the tax is on every search and every reader's *trust* — and once trust collapses, people stop maintaining the wiki, which accelerates the rot. The lean thesis transfers directly: **value is in restraint and removal, not accumulation.**

(Treat vivid "X% of pages are stale" figures as motivation, not fact — they're practitioner colour. The sound grounding is information-rot research: web-reference half-lives of 1.6–15 years; scheduled review dates are the only real defence against silent drift.)

## Lever 1 (highest leverage) — make ownership + staleness VISIBLE

The single best *no-admin, agent-buildable* governance pattern:

1. On each content page, add a **Page Properties** macro (`ac:name="details"`) — a two-column table whose **left column uses heading-cell style** (`<th>`): `Owner`, `Review Date`, `Status`.
2. Add a **shared label** to every such page (e.g. `team-handbook`).
3. On one index page, add a **Page Properties Report** macro keyed on that label — it aggregates the metadata into a sortable table.

Now ownership and review dates are *visible and sortable* with zero add-ons. The agent can build the entire dashboard via REST (`PUT` the `details` table into each page's storage, `POST` the label, create the report page). Pair it with **template default-labels** (template authoring is admin) so the dashboard self-populates as humans create pages.

**Report caps:** max **60 labels** in the macro, displays max **3,000 pages** (a sysadmin can raise `pagePropertiesReportContentRetrieverMaxResult`). Label logic: multiple values in one Label field = **OR**, separate Label fields = **AND**, `-label` = **NOT**. Storage-format snippet for the `details` macro is in `agent-execution-and-discovery.md`.

Review cadences to recommend: policies/HR/security every 6–12 months; project docs on change only.

## Lever 2 — find rot with CQL (agent-actionable)

- **Stale:** `type=page AND lastModified < startOfYear()` (or `< now("-12M")`); add `AND space=KEY` to scope. Prefer the documented camelCase `lastModified`; results depend on the index and the server timezone — verify on the instance.
- **No labels:** CQL has **no `label IS EMPTY`** — enumerate `type=page AND space=KEY` with `?expand=metadata.labels` and filter client-side for empty labels.
- **By owner / contributor:** `creator = "..."` / `contributor = currentUser()`.
- **Duplicate titles:** fetch all titles in scope and group client-side (`title ~ "X"` finds near-matches but won't dedupe).
- **Never-read pages:** sort by view count ascending in Analytics (DC analytics is page-view-count-level; deeper signals need add-ons or SQL).

## Lever 3 — kill duplication with transclusion, not copy-paste

- **Excerpt** (`ac:name="excerpt"`) marks a reusable block on a canonical page (one excerpt per page; name them to be explicit). **Excerpt Include** surfaces it elsewhere (`SPACEKEY:Page name` across spaces; `nopanel=true` drops the panel). **Include Page** transcludes a whole page.
- Edit the source once, every reference updates. Use for policies, definitions, standard instructions. The anti-pattern is copy-paste-and-drift; the discipline is **one canonical page + transclusion.**

## Lever 4 — prune in the right order

1. **Trash + version retention** (admin) — reclaim version bloat first.
2. **Move obsolete pages to a dedicated archive space** (agent can do the moves).
3. **Archive that space** (admin) — removes it from search/Directory.
4. **Delete** (with an XML export first) **only** when you need to reclaim index/DB.

### The DC lifecycle gotcha — no native page archiving

**Data Center cannot archive an individual page** (CONFSERVER-31010, "Gathering Interest," open since 2013). Only **space-level** archiving exists. So the DC page-archive substitute is the **move-to-archive-space workaround**:

- Create a dedicated archive space → move stale pages into it → set its **Status = Archived** (Space tools → Overview → Edit Space Details).
- **Gotcha:** you **cannot move pages *into* a space whose status is Archived** — flip it back to *Current*, move, then re-archive.
- **What archiving does:** excludes the space from search results, advanced search, Recent Spaces, the Spaces dropdown, and the Space Directory (unless the user ticks "Search archived spaces"). **It does NOT shrink the index or improve search performance** — content stays indexed; users can still view/edit per permissions. Archiving is a *relevance/findability* lever, not a storage one.
- **Cloud difference:** Cloud has native per-page archive (`… > Archive`) — the shortcut that replaces this whole dance.

### Retention rules (admin; DC/Server 7.16+)

**Administration → General Configuration → Retention rules.** Auto-purges three things: **historical page versions, historical file/attachment versions, and Trash.** Model = **global rules + space exemptions** — **set exemptions FIRST**, because a global rule starts deleting almost immediately. The **latest version is never deleted**, only history. Space admins can set space-level rules only if a sysadmin enables the exemption permission first. Trash is swept ~every 10 minutes; deletions are audit-logged at Advanced coverage.

### Export before delete

**Space tools → Overview → Delete Space** offers an XML export first (zipped XML to `<home>/restore/space/`, auto-deleted after 72h unless saved permanently). Always export before a destructive delete.

## The performance guardrails (DC, documented)

- **< 8,000 spaces = optimal · 8,000–10,000 = approaching · > 10,000 = exceeding.** Root cause is **permission checks**; symptoms are slower dashboards and macro rendering. This is the Confluence analogue of Jira's "<800 custom fields" — the one hard numeric guardrail. Consolidate sprawling/duplicate spaces to stay under it.
- **Pages are NOT a primary perf axis** — 80,000 pages can run in <512 MB; Atlassian publishes **no max pages-per-space for DC** (the ~50,000 figure is *Cloud*, don't cite it for DC).
- **Attachments:** 2 GB max per file; they live on the filesystem, so volume drives disk, not heap.
- **The real per-page ceiling is the editor.** There is **no documented hard limit** for page byte-size, macros/page, or attachments/page — the first failure mode is the editor. The **12-concurrent-editor cap** on Synchrony is a documented product limit and still stands. **Split very long or macro-heavy pages.**

  **Caveat added 2026-07-21 — the two bugs formerly cited here are FIXED.** The
  "large pages break Synchrony / ~30s timeout" evidence rested on
  [CONFSERVER-60057](https://jira.atlassian.com/browse/CONFSERVER-60057)
  ("Editing a large page causes Synchrony timeouts") and
  [CONFSERVER-59747](https://jira.atlassian.com/browse/CONFSERVER-59747)
  ("Publishing a page with a large table might be slow"). Both are now
  **Closed / Fixed** — 60057 on 2023-11-14, 59747 on 2024-10-08. Treat the
  split-large-pages advice as **authoring guidance** (readability, review
  effort, transclusion reuse), not as a workaround for live defects. If someone
  reports a Synchrony timeout on a current version, that is a *new* bug, not
  these — don't hand them a known-issue link that was closed years ago.

## Templates & blueprints (anti blank-page chaos)

- **Templates** = pre-populated pages (no code). **Blueprints** = template + creation wizard + auto-indexing (dev effort). Both enforce lean, consistent structure.
- **Promote** one template/blueprint per space to push "Blank page"/"Blog post" under "Show more" — nudging everyone toward structured creation. (Admin.)
- **Cloud difference:** Cloud ships a large template gallery; DC teams build their own library.
- The agent doesn't need the template engine to produce structured pages — it can `POST` a page whose `body.storage` already carries the house structure + the governing label (see `agent-execution-and-discovery.md`).

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian "Clean up your Confluence instance"; "Archive a space"; CONFSERVER-31010 (no native page archive); "Managing the number of spaces in Confluence DC" (<8,000); Server Hardware Requirements; "Troubleshooting Collaborative Editing"; Retention-rules + Back-up-a-space docs; Page Properties (Report) + Excerpt Include macro docs.
