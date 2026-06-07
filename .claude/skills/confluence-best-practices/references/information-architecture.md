# Information architecture — space, page, or child page, and how to adapt to the org

The single biggest source of Confluence confusion is *where content goes*. This file is the full treatment: the primitives, the decision, how to adapt to an org's own space taxonomy, tree shape, labels-vs-tree, and the orphan/depth fixes.

## The primitives (and what each is FOR)

```
   Space            CONTAINER + ACCESS BOUNDARY — its own permissions, homepage, sidebar, admin
     │
   Page             a UNIT OF CONTENT — ideally one purpose
     │
   Child page       a page whose parent is another page; the tree is SINGLE-PARENT
```

- A **space** is "like… different folders into which you can put your work" — but a *heavyweight* folder: it carries its own permission scheme, homepage, page tree, blog, and admin. Global (site) spaces appear in the **Space Directory**; **personal spaces** are owned by one user (drafts, scratch, to-dos) and listed in the People Directory.
- A **page** is content. A **child page** has exactly **one** parent — there is no native many-parents relationship; that role is filled by **labels**.

## The decision heuristic (the Confluence "epic or story?")

Ask, in order:

1. **Does this content have a distinct owning team/project, need its *own* permission scheme, and deserve to stand alone in the Space Directory?** → **new SPACE.** Otherwise *don't* create a space.
2. **Otherwise** → a **PAGE** in an existing space. This is the lean default for most new content.
3. **Does it logically belong *under* one specific parent topic?** → a **CHILD page** of that parent. If it belongs under *several* topics, **label it — don't duplicate it into two parents** (the tree is single-parent).

**The sharpest space-vs-page tie-breaker:** *page restrictions are more granular than space permissions.* If the only reason to make a space is to hide a handful of pages from some people, **use page restrictions instead** — spinning up a space per small access need is the dominant clutter anti-pattern. Create a space when the *whole body* of content has a different audience/owner, not when a few pages do.

**Lean default restated:** new content is a **page**, not a space. A space is an object with permissions + homepage + admin to maintain; "a space per tiny project/team" sprawls the Space Directory and (past ~8,000 spaces) measurably slows the instance (see `lean-content-and-lifecycle.md`).

## Adapting to the org's own standard (do not impose)

DC ships four space **blueprints** — *team*, *knowledge base*, *documentation*, *software project* — but these are just starter templates: *"they're more like templates… once created they don't really have much effect."* So never treat the blueprint label as a fixed kind.

**Reason in roles, then map to the org's names:**

| Role | What it's for | Typical shape |
|---|---|---|
| **Home / landing** | An org or department front door | Wide & shallow; homepage-driven; news/links |
| **Project workspace** | One project's working docs | Shallow nesting by phase (plan / build / review) |
| **Reference / knowledge base** | Many standalone how-to / FAQ / troubleshooting articles | **Flat**, search-first, heavy on labels |
| **Product / technical docs** | Versioned product documentation | Deeper parent/child tree; one space per product |
| **Personal / scratch** | Drafts, individual work | Personal space; promote to a team space when shared |
| **Meeting notes** | Recurring dated notes | Chronological, template-driven, `@mentions` + decisions |

Different roles legitimately want different *shapes* — reference content wants **flat + labels**; project content wants **shallow nesting by phase**. Pick the shape from the role; don't force one structure org-wide.

**The one near-universal rule: consistency by type.** *"Spaces of the same type should be named in a similar fashion and ideally follow a similar top-level page structure."* This constrains *consistency within a chosen convention*, not the convention itself — exactly the adapt-don't-impose stance.

**The method, every time:**
1. Reason in role terms first ("this is a *reference-KB* space / a *project workspace*").
2. **Discover** the org's actual spaces and the role each plays (`GET /rest/api/space?expand=metadata.labels` — see `agent-execution-and-discovery.md`).
3. Answer in their vocabulary, and write the convention down once so the question stops recurring.

## Tree shape — keep it shallow

- **Cap depth at ~3, maybe 4 levels.** Too deep means too many clicks, content stranded far from its parent, and neglect (*"out of sight, out of mind"* pages don't get maintained).
- Atlassian ships an **official health check, "Confluence spaces with too many nesting levels,"** confirming deep page trees degrade *performance* (page-tree navigation, viewing the space, viewing/editing pages) — not just UX. Atlassian withholds the exact threshold; treat the built-in health check (and the practitioner 3–4 heuristic) as the per-instance signal. Remediation = distribute into new spaces, restructure to reduce depth, subdivide by main parent pages, archive stale content.
- **Every space needs a homepage** that orients and routes — overview + key links + label-driven indexes (Children Display / Content by Label) — not a dumping ground. The documentation blueprint's homepage deliberately "uses search and page labels to make content easy to find."
- **Orphan pages** (no parent, no inbound links) are "alive but stranded." Detect and re-home or link them. Confluence has a built-in space-level **Orphaned Pages** view (pages with no incoming links); the *tree* sense ("no parent") is found via `ancestors`. Neither has a site-wide UI — iterate per space.

## Labels vs the tree (the "hierarchy rolls up, links don't" analogue)

- **Tree = containment** — *"where does this live?"* — one home per page.
- **Labels = cross-cutting taxonomy** — *"what is this about?"* — many facets, and they reach **across spaces and hierarchies** where the tree cannot.
- The mechanism reason: a child page is tied to **one** parent, so when a page belongs to several categories, **labels associate it with multiple contexts without duplicating or re-organising the hierarchy.** Never copy a page under two parents to "file it twice" — label it.
- The same split exists for **spaces**: **space categories are just labels applied to spaces**, grouping the Space Directory independently of any page tree (Space tools → Overview → Edit → Space Categories; a space can hold many).

Label discipline (controlled vocabulary, singular, lowercase-no-spaces, template-seeded) lives in `findability-and-search.md`.

## Folders (version-gated; verify before recommending)

Newer Confluence has **folders** — a lighter container than a parent page (*"a parent page is a container with a 'Read Me'; a folder is a container without one"*). Rule of thumb: *if you'd have created a blank parent page (or one holding only a Child Pages macro) just to group things, a folder fits better.* Folders are excluded from search results and any page can be converted to one. **Caveat:** folders launched on **Cloud** (GA late 2024) and DC support is more recent — **verify folder availability on the specific DC version before recommending the convert-empty-parent move.** The always-available, portable equivalent is a thin index page (or a Children Display macro), so prefer that when unsure.

## IA anti-patterns → lean fix

| Anti-pattern | Lean fix |
|---|---|
| A space per tiny project/team | A page (or child page); reserve spaces for real audience/permission boundaries |
| Page nested 5+ levels deep | Cap at 3–4; promote subtrees to siblings or a new space |
| Empty placeholder parent pages used only to group | Folder (where available) or a thin index page |
| Same page duplicated under two parents | Single home + labels |
| Orphan pages (no parent, no inbound link) | Re-parent or link from a homepage |
| Folksonomy label sprawl (`API`/`api`/`apis`) | Controlled, singular vocabulary seeded via template labels |
| Inconsistent sibling spaces | Standardize naming + top-level structure per role |

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian DC "Spaces"; "Confluence spaces with too many nesting levels" health check; "Use labels to categorize spaces"; Orphaned/Undefined Pages docs. Tier B: Atlassian Community space-vs-page and space-types threads; K15t "structure for long-term success"; Vectors page-tree/labels guides.
