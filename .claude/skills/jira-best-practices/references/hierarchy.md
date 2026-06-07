# Work-item hierarchy — deciding the level and adapting to the org

The single biggest source of confusion in Jira is *what goes where*. This file is the full treatment: the model, the misconceptions, the decision rules, how to adapt to an org's own standard, the Data Center field gotcha, and how to reinterpret all of it for non-software work.

## The three base tiers (and what each is FOR)

```
   Epic              CONTAINER   — a large deliverable that opens, makes progress, and CLOSES
     │
   Story / Task / Bug   DELIVERABLE — independently valuable/shippable units; all PEERS
     │
   Sub-task          BREAKDOWN   — a step of ONE deliverable, often worked in parallel
```

- **Parentage rules (memorise):** Epic → Story/Task/Bug; any standard type → Sub-task; Sub-task → nothing. Every standard type can be both a parent and a child; **only sub-tasks are child-only.**
- Story, Task, and Bug are **peers on one level** — none is "above" another. There is **no native level *between* Epic and Story.**
- Levels **above Epic** (Initiative, Program, Portfolio Epic, or custom names) come **only from Advanced Roadmaps** (bundled in Jira Software Data Center). They extend the ladder *upward* only.

Atlassian's own verbatim definitions: Epic = "A big user story that needs to be broken down… group together bugs, stories and tasks to show the progress of a larger initiative"; Story = "the smallest unit of work that needs to be done" (note: this wording is the *seed* of the "epic = big story" myth — prefer the container framing below); Task = "work that needs to be done"; Bug = "a problem which impairs or prevents the functions of a product"; Sub-task = "a piece of work required to complete a task".

## The five misconceptions to correct on sight

1. **"A Story is bigger than / sits above a Task."** FALSE. *A story cannot be a parent of a Task and a Task cannot be a parent of a Story — they are peers.* This is the #1 error, especially for people migrating from Azure DevOps (where Tasks nest under stories). 
2. **"An Epic is just a big Story."** FALSE. An Epic is a **container** that itself moves To Do → In Progress → **Done**. *If your Epic never closes, you want a Label or a Component, not an Epic.* Permanent categories ("Social Media", "Onboarding", "Maintenance") modelled as epics is the classic abuse.
3. **"Sub-tasks are just small tasks."** FALSE. Size is irrelevant — a Task can be as large as a Story. Sub-tasks carry real constraints (next point).
4. **"Story vs Task is a size decision."** FALSE. The axis is **value vs operational need**: Story = something an end user/customer values; Task = a team/technical/administrative necessity.
5. **"Parent/child and links are interchangeable."** FALSE. **Parent/child rolls up** in reporting and roadmaps; **issue links do not** (and have no native hierarchy view). Use hierarchy for *containment*, links only for *true cross-cutting dependencies* ("blocks", "is duplicated by").

## Sub-task constraints (why "everything is a sub-task" backfires)

Sub-tasks: don't appear on boards by default; don't count independently in sprint burndown/velocity; are **locked to the parent's project**; and **cannot be assigned to a different sprint than the parent** (no native workaround). Use a sub-task **only if** at least one is true:
- multiple people work pieces of the parent **in parallel**, or
- you need **per-step time tracking**, or
- the step must be **visible on the board**.

Otherwise use a checklist (a custom field or a checklist app). And if a story won't fit one sprint, **split it into smaller stories** — never stretch it with cross-sprint sub-tasks.

## The decision heuristic (portable beyond software)

Ask, in order:
1. **Does it deliver value to an end user/customer?** Yes → **Story.** No, it's operational/technical/administrative → **Task.** *(Most non-software items are Tasks.)*
2. **Will it fit in one sprint/cycle?** Yes → deliverable level (Story/Task). **No, it can't be finished in one cycle** → container level (**Epic**). Healthy epic ≈ 1–3 months and ~5–15 children.
3. **Is it a step of one deliverable, done in parallel / time-tracked / board-visible?** → **Sub-task.** Otherwise a checklist item.
4. **Is it a true dependency across items** ("blocks", "duplicates")? → an **issue link**, not a parent/child relationship.

**Splitting epics:** break into **vertical slices of value** ("a complete slice of cake — shippable"), not by technical layer (don't split into "backend", "frontend", "DB").

## Adapting to the org's own standard (do not impose)

Organisations legitimately map the levels to different names and frameworks. Two common, both-valid SAFe-in-Jira mappings:

| Approach | Mapping | What it does to Jira |
|---|---|---|
| **Atlassian-native** | Initiative → **Epic** → Story | Keep Jira's Epic; add an Initiative level above via Advanced Roadmaps |
| **SAFe-purist** | **Epic** → **Feature** → Story | Rename Jira's "Epic" to "Feature"; create a new "Epic" issue type above it |

Tempo's honest conclusion: *"We can't tell you which is best — too much depends on your company's situation."*

**Therefore the method is always:**
1. **Reason in role terms first** — "container level / deliverable level / breakdown level / above-container level".
2. **Discover the org's configured issue-type names** (`GET /rest/api/2/issuetype`; note the `subtask` flag and any Advanced Roadmaps hierarchy levels) and learn which name plays which role *on this instance*.
3. **Answer in their vocabulary:** *"By role this is a [container]; on your instance you call that '[their name]'."*
4. **Write the mapping down once** (a short team convention doc) so the question stops recurring. Standardise across teams **only where cross-team reporting actually needs it** — otherwise let teams keep their local convention.

Never assume the literal words "Epic" and "Story" occupy the standard roles on a given instance — verify.

## Data Center field gotcha — Epic Link vs Parent Link

On **Cloud**, Epic Link and Parent Link were merged into a single `Parent` field. **This was NOT implemented in Data Center** (JPOSERVER-4430, closed *Not a bug*). On DC you therefore have **two separate, independently-acting fields**:
- **Epic Link** — links a Story/Task/Bug to its **Epic**.
- **Parent Link** — an **Advanced Roadmaps** field linking an Epic to a higher level (Initiative, etc.).

Crucially, **Epic Link does *not* respect the Advanced Roadmaps custom hierarchy**, which breaks naïve JQL and roll-up reporting that assume one unified parent. **DC workaround** when this bites: create a *new* Epic-style issue type, add it to the Advanced Roadmaps hierarchy, and use **only the Parent Link field** for all parent/child relationships in plans.

When writing JQL across the hierarchy on DC, be explicit about which field you mean; don't assume a single `parent` clause covers both like it does on Cloud.

## Setting up levels above Epic on Data Center

Advanced Roadmaps hierarchy levels are configured in a strict order:
1. A Jira **admin creates the issue type** (e.g. "Initiative").
2. **Add that issue type to the relevant projects.**
3. In **Advanced Roadmaps → hierarchy configuration**, create the hierarchy level and **map the issue type to it.**

Caution: *"Any changes you make to the hierarchy levels apply to all existing plans"* — it's system-wide, so coordinate before changing it. Default DC levels: Epic (maps the Epic type), Story (maps Story **and** Task), Sub-task.

## Reinterpreting the hierarchy for non-software work

The same shape works for any domain — just read the roles, not the software words:

| Role | Software | Operations / Services | Engineering / Infrastructure | Business / Admin |
|---|---|---|---|---|
| Above-container (Advanced Roadmaps) | Initiative | Program / service line | Capital project / programme | Strategic objective |
| **Container (Epic)** | Feature epic | Operational initiative (e.g. a migration, an audit cycle) | A facility change, a system build-out | A campaign, a hiring round |
| **Deliverable (Task ≫ Story)** | Story/Task | A runbook task, a change request | A work package, an inspection | A deliverable, an approval |
| **Breakdown (Sub-task)** | Sub-task | A step of the change | A step of the work package | A step of the deliverable |

For non-software, **Task is the default deliverable type** (work is operational, not user-story-shaped); reserve Story for genuinely user-value-framed items. Don't invent a "Story" habit where it doesn't fit.

## Sources
See `references/sources.md` for the full source + tier table. Key anchors for this file: Atlassian `what-are-issue-types` and `epics-stories-themes` (Tier A); Advanced Roadmaps DC hierarchy docs (Tier A); JPOSERVER-4430 (Tier A); Seibert Group story-vs-task-vs-epic (Tier B); Tempo SAFe-hierarchy (Tier B).
