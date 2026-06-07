# Agent execution & discovery — acting on Confluence safely and language-safely

This is the operational heart of the skill for an **agent acting on Confluence** automatically. Three jobs: (1) **discover** the org's real configuration so you never guess; (2) know the **act-on-content vs advise-the-human** boundary; (3) **write** content idempotently and safely. It is **tool-agnostic** — REST/CQL primitives — and applies whether the agent calls REST directly, goes through an MCP server, or hands steps to the user. Cloud and DC differences are flagged throughout.

## Discover before you act

Map each thing you need to learn to the primitive that fetches it. **Anchor logic on the language-independent column**, never on a display name or title.

| To learn… | DC (REST v1) | Cloud (REST v2) | Language-safe anchor |
|---|---|---|---|
| Spaces + keys + categories | `GET /rest/api/space?expand=metadata.labels` | `GET /wiki/api/v2/spaces` (**categories still need a v1 call**) | space **`key`** |
| Page tree / ancestors | `/content/{id}/child\|descendant/page`, `?expand=ancestors`; `/content/scan` (7.18+) | `/pages/{id}/children`, `/ancestors`, `/spaces/{id}/pages` | content **`id`** |
| Labels in use | per page `/content/{id}/label`; instance-wide → CQL-facet | `/pages/{id}/labels` | **label text** |
| Templates | `/rest/api/template/page\|blueprint` | v1 `/template/...` | template id |
| Space permission scheme | `GET /space/{key}?expand=permissions` | **apps blocked from the resource on Cloud** → advise human | — |
| Indexing language | **not REST-exposed** → advise human | not REST-exposed | — |
| What content really says | `?expand=body.storage` → `body.storage.value` | `?body-format=storage` | — |

> Read a handful of existing pages with `?expand=body.storage,metadata.labels` to *see* the instance's real titles, labels, and structure before proposing changes — "discover before advising."

## Language-independent anchors (what survives a localized UI)

- **Durable:** space **KEY** (immutable, a-z/0-9 ≤255, forms the URL), numeric **content ID** (stable across rename/move), **label text** (lowercase, no spaces, only `_`/`-`), **CQL field names**, **content-type tokens** (`page`/`blogpost`/`comment`/`attachment`).
- **NOT durable — never use as a lookup key:** space **display name**, page **title** (gets renamed; blueprint titles differ per instance language), any UI string.
- **CQL field name nuance:** prefer documented camelCase **`lastModified`**; the lowercase `lastmodified` has worked historically but practitioners report it intermittently failing — emit camelCase and verify on the instance. Date results are index- and timezone-dependent.

## The act-on-content vs advise-the-human boundary

**Agent-actionable at content level** (needs only content/page permissions):
- Create / update / delete pages & blog posts; **move** (re-parent via `ancestors`/`parentId`); add/remove **labels** (dedicated endpoint — *adds without replacing*; a full content update **replaces** labels); add **comments**; set/read **page restrictions** (`/content/{id}/restriction`); **CQL search**; read the page tree; read/write **content properties** (JSON side-store).

**Advise-the-human (admin / global config):**
- Create a **space** / set its permission scheme (on Cloud, apps are blocked from the space-permissions resource); **default space permissions**; restrict **space creation**; build/edit **blueprints** (REST can't create blueprint templates); set the **indexing language**; **retention rules**; install apps; global config.

**Map each fix to its lane:**

| Fix | Lane |
|---|---|
| Tag stale/untagged pages | agent — `POST /content/{id}/label` |
| Re-home an orphan / misfiled page | agent — update `ancestors`/`parentId` |
| Lock a page from edits | agent — `PUT /content/{id}/restriction` |
| Build an ownership/staleness dashboard | agent — Page Properties + Report (below) |
| Standardize new-page structure | agent — write the storage skeleton; a *blueprint* → advise admin |
| Enforce space-creation policy / fix CJK search / create a space | advise admin |

## Writing content idempotently and safely

- **The write payload is storage format** (XHTML-ish XML, `ac:`/`ri:` namespaces, CDATA bodies; *technically XML, not valid XHTML* — emit well-formed, self-closed, entity-escaped tags or the POST fails). **Markdown is an editor-input convenience only — NOT a write representation.** Generate storage directly, or convert first (`POST /contentbody/convert/storage` from wiki on DC; on Cloud the sync convert is deprecated and async dropped wiki→storage, so generate storage). **Never treat ADF as the Confluence write format** — ADF is Jira-Cloud; Confluence writes are storage on both Cloud and DC.
- **Idempotency key = unique title per space.** Look up `GET /content?title=...&spaceKey=KEY` (or CQL `space=KEY and title="..."`); if it exists, **update**, else **create**. Don't blind-POST — you'll get a title conflict.
- **Version safety (bloat + conflicts):** every update **creates a new version** — send `version.number = current + 1`. A stale number → **409 "version must be incremented"**; concurrent edits → `OptimisticLockException`. Recipe: GET the current `version.number` immediately before PUT, increment by 1, **retry-with-refetch on 409**. To curb version bloat, **read-diff-before-write** — skip the PUT if the rendered storage is byte-identical; set a `version.message`.
- **Don't clobber human formatting:** fetch `body.storage`, **mutate surgically** (replace only a marked region — e.g. an HTML-comment-delimited section or the Page-Properties block) and write back; never regenerate the whole body from your own model of it.
- **Restriction-awareness:** check `GET /content/{id}/restriction` before writing — a write to a restricted page may 403.
- **Structure for human + machine:** real `<h1>..<h6>` headings (anchors + TOC), **labels** for CQL discoverability, and a **Page Properties** block so a Report macro / CQL can aggregate — the Confluence analogue of structured Jira fields.

### Minimal storage-format constructs

```xml
<!-- Heading -->            <h2>Section</h2>
<!-- Info panel -->         <ac:structured-macro ac:name="info"><ac:rich-text-body><p>Summary first.</p></ac:rich-text-body></ac:structured-macro>
<!-- Table of contents -->  <ac:structured-macro ac:name="toc"><ac:parameter ac:name="minLevel">2</ac:parameter><ac:parameter ac:name="maxLevel">3</ac:parameter></ac:structured-macro>
<!-- Internal link -->      <ac:link><ri:page ri:content-title="Other Page"/><ac:plain-text-link-body><![CDATA[label]]></ac:plain-text-link-body></ac:link>
<!-- Page Properties (governance dashboard key/value) -->
<ac:structured-macro ac:name="details"><ac:rich-text-body>
  <table><tbody>
    <tr><th>Owner</th><td>Team Payments</td></tr>
    <tr><th>Review Date</th><td>2026-09-01</td></tr>
    <tr><th>Status</th><td>Current</td></tr>
  </tbody></table>
</ac:rich-text-body></ac:structured-macro>
```

Use `<th>` for the left (key) column so the Page Properties Report keys on it. **Labels are NOT in the page body** — add them via `POST /rest/api/content/{id}/label` (body `{"prefix":"global","name":"team-handbook"}`), which adds without clobbering existing labels. `ac:` = Confluence storage elements; `ri:` = resource identifiers (pages, attachments, users, spaces).

## CQL governance recipes (run autonomously)

- **Stale:** `type=page AND lastModified < startOfYear()` (+ `AND space=KEY`).
- **No labels:** enumerate `type=page AND space=KEY` with `?expand=metadata.labels`, filter client-side (no `label IS EMPTY` in CQL).
- **By owner:** `creator = "<accountId-or-username>"` / `contributor = currentUser()`.
- **Duplicate titles:** fetch titles in scope, group client-side.
- **Orphans:** no site-wide UI — iterate per space (built-in "Orphaned Pages" = no inbound links; the tree sense = `ancestors` is just the homepage).

## Cloud vs DC execution — branch on these

| Aspect | DC | Cloud |
|---|---|---|
| Auth | Basic or **PAT** (Bearer, 7.9+) | email + **API token** / OAuth (Forge/Connect for apps) |
| REST | **v1 only** (`/rest/api/content`, `start/limit`) | v1 **and v2** (`/wiki/api/v2`, cursor `Link: rel=next`) |
| Write target | **storage** | **storage** (also `atlas_doc_format`, but storage is portable) |
| User id | **`username` / `userKey`** | **`accountId`** (never hardcode usernames in Cloud CQL) |
| Space categories | v1 expand | **v1 fallback** (no v2 endpoint) |
| Convert wiki→storage | v1 sync convert | sync deprecated; async lacks it → generate storage |
| Page archive | none (space-archive workaround) | native per-page |

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian DC + Cloud REST/CQL docs (content, restrictions, templates, examples; v2 page API); "Confluence Storage Format"; user-privacy (accountId) migration; CQL field reference. Tier A-tracker: v1-deprecation-timeline, async-convert, 409/OptimisticLock threads.
