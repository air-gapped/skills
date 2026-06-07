# Lean configuration — de-bloating fields, screens, statuses, issue types

The "filling in a ticket is a chore" / "Jira is slow" dread is overwhelmingly a **configuration bloat** problem. This file has the numbers and the concrete Data Center admin mechanics to fix it.

> **Who does what.** Almost everything in this file is **schema/admin configuration** that neither `jira-cli` nor `mcp-atlassian` can perform — so the agent's job here is to **diagnose the bloat and hand the user the exact, minimal steps** (the click-paths below). The agent acts directly only at the issue level: creating issues with a lean field set, setting the Resolution **in the transition payload** (the REST/CLI/MCP path ignores transition screens), and auditing field usage by reading issues. Treat the admin click-paths as the *recommendation you give the human admin*, not something to attempt via a tool.

## Custom fields — the guardrail and the real cost driver

**Atlassian's documented DC guardrail:** **< 800 custom fields = optimal · 800–1,200 = approaching the limit · > 1,200 = exceeding it.** 800 is not a hard cap but "where your site begins to experience degraded performance" (derived from real performance data). Too many custom fields degrade four things: **reindex time, issue create/update, JQL search, and database size.** A documented real case: an issue with **1,916 indexed custom fields took 12–13 s to create**, dropping to ~2 s after optimisation.

**The real driver is context, not raw total.** *"If a field has a global context, it's used in all projects, which has a significant impact on the index."* The two costly patterns:
- **Global-context fields** (apply to every project) — scope them to specific projects/issue types instead.
- **Fields with default values** — "overhead to persist and load at every operation."

So a high total can be fine if fields are tightly scoped; a moderate total can hurt if many are global with defaults.

**Audit & prune (DC):**
- **Admin → Instance Optimizer → Optimize custom fields → Scan** surfaces fields that can be optimised and why.
- DC 8.16+ shows **usage columns** on the Custom Fields page (issues using the field; last value update) — sort to find dead fields.
- Deletion candidates: fields used by < ~5 issues, not updated in a long time, on no screen, or near-duplicates of another field. **Deleting a custom field is permanent and destroys its data** — confirm first.
- The custom-fields admin page itself can take "several minutes to load" at 1000+ fields — a smell in its own right.

**The 4-question field-vs-keep test.** A field earns its place only if **yes to any**:
1. Will it drive **cross-team reporting**?
2. Will **automation** depend on it (routing, SLA, roll-up)?
3. Must it be **searchable/filterable in JQL**?
4. Must the data **survive the item moving between projects**?

If "no" to all four, it's intake-only context — put it in the description, not a field. And a **new global field needs a named owner** for maintenance — *"the owner requirement kills most requests, and rightly so."*

> **DC note:** native **Forms/Proforma** (the Cloud "escape hatch" for intake-only data) are **not** part of plain Data Center. On DC the equivalent levers are description text, **context-scoped field configurations**, and **minimal Create screens** (below) — do not recommend native Forms on DC.

## Minimum-viable Create screen (the highest-leverage fix)

Make the **Create** screen short and the **Edit/View** screens fuller. Design Create around *"what's the minimum needed right now?"* — not *"what could we capture?"* Too many Create fields make users *"fill fields with garbage, avoid creating tickets, or abandon Jira"*, which destroys data quality.

**Screen Scheme — map operations to different screens.** A screen scheme maps three issue operations — **Create**, **Edit**, **View** — to (possibly different) screens.
- Path: **Administration → Issues → Screens → Screen schemes →** *Configure* the scheme → **Associate an issue operation with a screen** (pick the operation + screen).
- The **Default** entry catches any unmapped operation and **cannot be deleted** — if you only map Create + View, Edit falls back to Default.
- Hierarchy: screen → (screen scheme, by operation) → (issue-type screen scheme, by issue type) → project. So one project can show a lean Create screen for Task and a different set for Bug.
- **DC quirk:** the **View** operation only controls layout/order of *custom* fields in the middle section — it does not hide system fields (those are governed by Field Configuration).

**Field Configuration — required/optional and hidden/shown, per context.**
- Path: **Administration → Issues → Fields → Field configurations →** *Configure*/*Edit*. The **Operations** column has **Required**/**Optional** and **Hide**/**Show** links per field.
- **Hard constraints:**
  - A **hidden field cannot be required**.
  - **Any Required field must appear on every Create screen** of the associated projects/issue types — or issue creation breaks. *So to drop a field off the Create screen, make it Optional first* (or set it via a default/post-function).
  - **Hiding a field discards its default value** (the default won't carry over).
- **Per project × issue-type** behaviour comes from a **field configuration scheme**: map each field configuration to issue types, then associate the scheme with a project (**project admin → Fields → Actions → Use a different scheme**). A field can thus be required in project A, optional in B, hidden in C. **Reindex after changes.**

## Statuses — keep it to 6–9, no "status zoo"

Start from the three default categories (To Do / In Progress / Done) and add **only statuses the team actually uses**; **6–9 core statuses** is a reasonable soft ceiling. Every added status multiplies possible transition paths (combinatorial growth). There is **no published performance benchmark** for status count — this is a usability/clarity argument, not a perf one. Push edge cases (e.g. "waiting on vendor") to a label or field, not a new global status.

## Status vs Resolution — the single biggest over-modeling fix

- **Status** = where the issue is in the workflow. **Resolution** = *why* it's no longer in flight.
- Mechanic: **once Resolution has any value, Jira treats the issue as resolved even if its Status isn't in a final category.** Reports like "Created vs Resolved" key off **Resolution**, not status. So you need only **one or two terminal statuses** (Done/Closed) plus a small **Resolution set** (Done, Won't Fix, Duplicate, Canceled) — not many "done-like" statuses.
- **Set Resolution only on closing transitions**, via a **transition screen** containing just the Resolution field (the historical default is literally named "Resolve Issue Screen"), or via an **Update Issue Field** post-function for a fixed value. **Never put Resolution on the Create or Edit screen** — that's a common mistake that lets items be "resolved" the moment they're created.
- **Reopen trap:** on every transition that re-opens an issue, add a post-function **Update Issue Field → Resolution → None** — otherwise the reopened item keeps showing as resolved in reports.
  - Path: edit workflow → select the reopen transition → **Post functions → Add post function → Update Issue Field →** Issue Field = Resolution, value = None. **Publish the draft.** Repeat on *every* reopen transition.
  - Native post-function is preferred over an Automation rule here (zero extra moving parts, runs synchronously inside the transition).
- **API caveat (matters with `jira-cli`/REST):** the REST transition API **does not enforce transition screens**, so a screen-only Resolution can be left null when transitioning via API — send the resolution in the transition payload.

## Issue types — fewer is better

No hard limit, but prefer the **built-in types** and make anyone justify a new type over reusing an existing one. **Substitution rule:** for categorisation, use a **label**, a **component**, or a **"Phase" select field** instead of a new issue type. Too many types cause "confusion, overcomplicated workflows, and difficulty reporting."

## Sprawl correlates with admin count

*"More than two or three admins with varying expertise in different locations → more customisations than necessary"* (e.g. several near-duplicate "waiting for vendor" statuses created independently). Preventive measures: limit who has admin, use **project templates**, reuse existing elements, prefer **generic field names**, and put a **governance gate** before any new field/workflow/type.

## Sources
See `references/sources.md`. Key anchors: Atlassian Enterprise DC custom-field guardrail; Atlassian KB on too-many-custom-fields; `optimizing-custom-fields`; `associating-a-screen-with-an-issue-operation`; `specifying-field-behavior`; `associating-field-behavior-with-issue-types`; `clear-the-resolution-field-when-reopened`; `best-practices-on-using-the-resolution-field` (all Tier A). Field-vs-form test and minimum-viable-screen: Atlassian Community 2026 + The Jira Guy (Tier B).
