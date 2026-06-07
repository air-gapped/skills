# Workflows, automation, and reporting — killing the busywork

Two named dreads live here: "our workflow is a maze" and "status updates are busywork". The fixes are workflow simplicity, *disciplined* automation, and making the board (not a document) the single source of truth.

> **Who does what.** Workflow editing, Simplified-Workflow toggles, board config (WIP/swimlanes/quick filters), and Automation-rule authoring are **admin/UI operations** — *not* exposed by `jira-cli` or `mcp-atlassian`. So the agent **advises the human admin** with the exact steps below (and may drive the Automation REST API directly via Bash/curl where the org allows). What the agent does **directly** through the tools: run JQL off **shared filters** for live reporting, **transition issues by id**, read boards/sprints (`jira_get_board_issues`, `jira_get_sprints_from_board`), and keep the board current via issue updates. The reporting principle ("update the board, not a doc") is something an agent can *operationalise* by querying Jira instead of hand-rolling status — and by reminding the user not to maintain a parallel doc.

## Workflow design — simple, shared, governed

- **Start minimal, add only what earns its place.** Baseline = the three categories (To Do / In Progress / Done). Add a status only when the team can name what it *adds to the value-creation process*. Aim for **6–9 core statuses**; every status multiplies transition paths.
- **Status vs Resolution** (full mechanics in `lean-config.md`): don't encode "done-ness" as many terminal statuses — use one/two terminal statuses + the Resolution field, set on closing transitions, cleared on reopen.
- **Govern against per-project drift.** *"If you let project admins customise on their own without coordination, different teams move in different directions."* Use **shared/standard workflow schemes** so workflows are reusable and simple; route new customisation through an approval that keeps the big picture in mind; limit who has admin (sprawl correlates with admin count).

### DC "Simplified Workflow" — a lean default with sharp edges

Enable via **Board → Configure → Columns tab → "Simplify workflow"**. It lets you add/remove statuses and columns straight from board config (no separate workflow editor); transitions need no screen; **resolution auto-sets to Done** when an issue reaches a "done" column.

Trade-offs (why it's good for small/non-software teams but not governed multi-team setups):
- the board must represent a **single project**;
- the project's workflow scheme must use **one workflow for all issue types**;
- every status needs ≥1 outgoing transition;
- **only Atlassian-provided post-functions, validators, and conditions** — no app-provided ones;
- no transition screens (so no transition-time field capture);
- switching **migrates all existing issues** to the new workflow (can be slow).

## Automation for Jira — free, native, and a double-edged sword

**Licensing:** Automation for Jira is **free and native in Jira Software / JSM Data Center** (built in since JSW 9.0 / JSM 5.0; A4J 8.0+ needs no separate license). It ships inside 10.3 LTS and 11.x. No per-node or extra charge.

**Service limits (DC, configurable via REST `PUT /rest/cb-automation/latest/configuration/property`):** 6 threads/node default (max 8); `max.processing.time.per.day` = 3600 s; `max.rules.per.hour` = 5000; `max.issues.per.search` = 1000; `max.queued.items.per.rule` = 25,000; `max.queued.items` = 100,000; `max.rule.execution.loop.depth` = 10; `rule.rate.per.five.second` = 2. **Breaching limits throttles and silently disables rules** — which is exactly how "automation mysteriously stopped" happens.

**Triggers:** Issue created, Issue transitioned (specific or any), Field-value changed, Work-item event, Scheduled (cron/interval). **Actions that kill clicking:** Transition, Assign (balanced-workload / round-robin / random), Edit, Comment, Create, Clone, Create sub-tasks, Lookup issues (JQL), Re-fetch, Send email, Create version, Delete, Link, Manage watchers, Log work.

**No one-click "update parent from children".** Parent/child roll-up is a **branching recipe**: branch on the related sub-tasks, then Transition/Edit the parent (the Transition action can "copy status from parent to sub-tasks"). Keep sync **one-directional** to avoid loops.

### High-value recipes (each with a guardrail)

1. **Auto-triage / routing** on create — set Team/Queue by Component/Request-type. *Guard:* only if Assignee empty, or set a one-time "Routed" flag.
2. **Field hygiene** on change/transition/daily-schedule — set defaults, clear mutually-exclusive fields.
3. **SLA / staleness nudge** on a scheduled check — comment + notify. *Guard:* an "Escalated Level 1 = yes" flag so it fires once per stage.
4. **Release-readiness gate** on transition to Done — if required fields missing, transition back with a blocking comment.
5. **Parent-child sync** on sub-task change — set parent "Ready" when all children complete. *Guard:* one direction only.
6. **Incident → postmortem** auto-create for SEV1/SEV2.
7. **Webhook integration** — *Guard:* avoid "write everywhere" rules that cause sync loops.

### Automation sprawl is its own dread — govern it

*"A 50-person org can easily accumulate 300+ rules — many redundant, some conflicting, a handful silently broken."* Symptom: *"managers asking why the same person got pinged 11 times."* Maturity = **fewer rules that are owned, measurable, and predictable** — *"the best automations are kind of boring."*

Atlassian's official "optimise rules" guidance (what NOT to do):
- **Scope each rule to the few projects it applies to** (restricts execution at the earliest stage).
- **Order conditions to filter out the most issues as early as possible.**
- **Avoid generic triggers that chain-fire** ("Issue updated" triggering other rules → uncontrollable chains).
- **Don't use automation as a batch processor** with broad triggers (throttling silently drops issues).
- **Use synchronous execution only when necessary**; webhooks can significantly slow rules.
- **Merge similar rules** with branch conditions to lower rule count.
- Name rules **`[Project Key] - [Trigger] - [Action]`** so the inventory stays legible.
- **Don't automate** complex multi-approver workflows with exceptions, large fan-out updates, or "one rule to run everything."

When asked to add automation, first ask whether an *existing* rule can be extended, and whether the toil is better removed by simplifying the workflow than by papering over it with a rule.

## Reporting — "update the board, not a doc"

Manual status reports are the busywork to eliminate. *"You do not fix reporting by improving templates. You fix it by using a system that already holds live project data."* The failure cycle: management asks for templates → teams scatter stale files in email/Confluence/Excel → stakeholders bypass them and ask for real status anyway.

Single-source-of-truth anti-patterns to call out:
- **Data fragmentation** — one team builds 10 dashboards, another exports to Excel, a third pulls half the data into Confluence tables.
- **Dashboard overload** — "15 gadgets that answer none of the real questions."
- **External detours** — *"if someone is exporting to Excel, your SSOT is already broken."*
- **Status docs alongside Jira** — *"when people maintain separate status documents while Jira exists, you've lost the single source of truth before standup even starts."*

Do instead: build dashboards/gadgets on **saved, shared filters** so status stays accurate with no extra admin; **update the board, not a doc**; in standup, walk the board.

## Board hygiene — make the board reflect reality cheaply

- **WIP limits:** Board → **Configure → Columns** → set **Min/Max** per column (header turns red when violated). Set limits to the team's **actual capacity**, not an industry number; when they work, cycle time drops. *Native WIP is column-level only* — per-swimlane WIP needs a Marketplace app.
- **Swimlanes:** Board → **Configure → Swimlanes** → base on **Queries (JQL)** / **Stories** (epic) / **Assignees** / **None**. (ORDER BY in swimlane JQL is ignored — content always orders by rank.)
- **Quick Filters:** Board → **Configure → Quick Filters** → Name + JQL; render as toggle buttons; drag to reorder.
- **Flow metrics:** track lead time, cycle time, WIP, throughput, and cumulative flow for incremental improvement — not as a stick. Healthy signal: *the team updates the board daily without prompting, and the board matches reality.*

## A note on metrics and dread

**Velocity / story points are a team *planning* aid — never a cross-team or per-person KPI.** Used as a target they cause story-point inflation and *"distort estimation, damage collaboration"* ("performance theatre"). If a manager wants per-person velocity, that's a dread-generator to push back on, not a report to build.

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian automation `understand-versions-licenses`, `automation-service-limits`, `optimizing automation rules`; `using-the-simplified-workflow`; `configuring-{a-board,swimlanes,quick-filters}`; WIP-limits + kanban-metrics. Tier B: idalko workflow best practices; onpointserv 2026 automation recipes; community SSOT + status anti-patterns; apwide live-dashboards.
