---
name: jira-best-practices
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  Advise on USING Jira well, not operating it: make the structural call — is this an epic, a story, a task, or a sub-task? — and diagnose why a Jira is a dread, then recommend the lean fix. Adapt to the organisation's OWN hierarchy names, conventions, and working language instead of imposing a methodology. Self-hosted-first: Jira Data Center 10.3/11.x (no Cloud AI; dual Epic Link + Parent Link). Built for an agent that ACTS on Jira through the jira-cli tool or the mcp-atlassian MCP server while advising the user; Jira web-UI and admin-schema guidance is secondary. Covers ALL project types — software AND non-software (operations, engineering, services, business).
when_to_use: |-
  Use whenever the user asks "is this an epic or a story / task / sub-task", "epic vs story", "where should this work go", or wants Jira leaner / less of a chore / less of a dread — even if Jira isn't named. Fires on "our Jira is a mess / bloated / slow", "too many required fields to create a ticket", "filling in a ticket is a chore", "simplify our workflow", "too many statuses", "status vs resolution", "jira best practices", "reduce Jira ceremony", "set up Jira for a non-software / ops / business team", "Jira without sprints or story points", "kill manual status reports", "Jira automation out of control", "how many custom fields", "standardise our hierarchy", "teams use epic/story differently", "non-English / localized issues / statuses". NOT for low-level jira-cli / mcp-atlassian command mechanics, or Cloud-only features (Rovo AI, work items, Spaces).
---

# jira-best-practices — use Jira leanly, structure work sensibly, adapt to the org

Primary reader: an **agent helping a user** — one that *acts on* Jira through tools (the `jira` CLI, or the **`mcp-atlassian`** MCP server) and advises the user on **how to use Jira well**: what an issue *is*, where work *goes*, which fields/statuses/workflows to keep, and how to make Jira stop being a dread. This is the **judgment layer** above those execution tools — it decides *what* should change and *how work should be structured*; the tools do the *how*.

This skill is **instance-agnostic and organisation-adaptive**. It never assumes a team's hierarchy names, workflow, or language — it shows how to *discover* the org's actual conventions and reason within them. It is **self-hosted-first**: the defaults below are for **Jira Data Center** (see the Cloud-vs-DC guard).

## How the work gets done (execution layer)

An agent here almost always acts through one of two **issue-level, Data-Center-capable** tools — and that boundary determines what to *do* versus what to *advise*:

- **`jira-cli`** (sibling skill) — the `jira` CLI, non-interactive automation contract, JQL, ADF. Use it for execution mechanics, flags, and auth.
- **`mcp-atlassian`** ([sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)) — MCP server for Jira+Confluence; supports **Server/Data Center (Jira v8.14+, PAT auth)**; ~72 tools incl. `jira_search` (JQL), `jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_transition_issue`, `jira_get_transitions`, `jira_search_fields`, `jira_get_link_types`, `jira_get_project_components`, `jira_link_to_epic`, `jira_create_issue_link`, `jira_add_comment`, `jira_batch_create_issues`, agile board/sprint reads. Has `READ_ONLY_MODE` and `ENABLED_TOOLS`/`TOOLSETS` gating.

**What an agent DOES directly** (both tools support it): discover the instance's real config; create issues at the *correct* hierarchy level with the *right* type/fields; transition **by transition id**; link to epic / create issue links; run JQL anchored on language-independent keys; add comments; do safe bulk hygiene via update/transition; and, where the org permits, design/trim **Automation for Jira** rules.

**What an agent ADVISES the human to do** (secondary — neither tool exposes it): **all schema/admin config** — screens & screen schemes, field configurations, workflows, issue types, custom fields. For these, hand the user the exact, minimal steps (this skill's reference files carry the DC click-paths) rather than attempting them via a tool. Likewise, UI/board guidance is secondary — surfaced mainly to help a user get a cleaner board or view.

So a good response usually = **(a)** the correct action taken via `jira-cli`/`mcp-atlassian`, plus **(b)** a crisp, copy-pasteable recommendation for anything that needs an admin.

## The prime directive

Most Jira dread is a **usage** problem, not a tool problem. The teams that succeed are the ones where *Jira encompasses the minimum process possible*. So, every time:

1. **Lean by default.** The right answer is almost always *fewer* — fewer fields, fewer statuses, fewer issue types, fewer required inputs, fewer rules. Adding is easy and seductive; the value is in restraint. When in doubt, recommend removing.
2. **Adapt to the org, never impose.** Different organisations legitimately define "epic", "story", and the levels above them differently — and that's fine. Discover *their* configured names and conventions and reason in *their* vocabulary. Describe levels by **role** ("container / deliverable / breakdown"), then map to what they actually call them.
3. **Don't software-ify non-software work.** Jira serves ops, systems engineering, services, and business teams too. For those, drop sprints/story-points/velocity entirely and reach for Kanban, due dates, and simple flow.
4. **Non-English is fully normal.** Issue text and configured values are frequently in a local language. **Never translate or rewrite a user's content.** Discover the instance's real strings and anchor logic on language-independent keys.
5. **Diagnose before prescribing.** Name the specific dread, trace it to a cause, then propose the smallest fix that addresses it. Don't redesign the whole instance when one required field is the problem.

## Cloud vs Data Center — speak the right dialect (read this first)

As of June 2026, **every headline "new Jira" change is Cloud-only and is NOT in Data Center.** A self-hosted team lives in a different vocabulary. Get this wrong and the advice is unusable.

| Concept | Jira **Cloud** (2026) | Jira **Data Center** 10.3 / 11.x (this skill's default) |
|---|---|---|
| Product name | one unified **"Jira"** | **"Jira Software"** (+ Jira Core base, JSM add-on) |
| Work nouns | **"work item"**, **"Space"** | **"issue"**, **"project"** |
| Epic↔child field | single unified **`Parent`** field | **`Epic Link`** *and* **`Parent Link`** — two separate, independently-acting fields (JPOSERVER-4430 *not* implemented in DC); Epic Link ignores the Advanced Roadmaps hierarchy |
| AI | **Rovo** agents / Atlassian Intelligence built in | **none native** — AI only via Cloud connectors that sync DC data *into* Cloud. Don't depend on AI. |
| Non-software views | native List / Calendar / Timeline | **Marketplace apps only** (Structure, BigPicture, Calendar for Jira) — not native |
| Forms (intake) | native Forms / Proforma | not native on plain DC — use **field configurations + minimal screens** instead |

DC status as of 2026-06: latest **11.3.7** (2026-06-03); supported LTS lines **11.3** (→Dec 2027) and **10.3** (→Dec 2026). DC is on a sunset path (sale to new customers ended 2026-03-30; read-only EOL 2029-03-28) — note it honestly if asked, but this skill is about using *today's* DC well, not migrating.

If `jira serverinfo` (or the instance) shows **Cloud**, flag that the dialect differs and adapt; otherwise assume DC.

## The hierarchy — by role, not by name (the #1 confusion)

**Default Jira is exactly three base tiers.** Internalise this shape and the parentage rules:

```
   Epic            ← the CONTAINER level (a large deliverable that opens and closes)
     │
   Story / Task / Bug   ← the DELIVERABLE level — all PEERS on one level (NOT nested)
     │
   Sub-task        ← the BREAKDOWN level (a step of one deliverable)
```

- Allowed parentage: **Epic → Story/Task/Bug**; **any standard type → Sub-task**; **Sub-task → nothing**. Any standard type can be both parent and child; only sub-tasks are child-only.
- Levels **above Epic** (Initiative / Program / Portfolio) exist **only via Advanced Roadmaps** (bundled in Jira Software DC). There is **no way to natively insert a level *between* Epic and Story.**

**The misconceptions to correct on sight:**

| Myth | Reality |
|---|---|
| "A Story is bigger than a Task / sits above it." | **They're peers.** A Story cannot parent a Task and vice-versa. (The #1 error, esp. from Azure DevOps migrants.) |
| "An Epic is just a big Story." | An Epic is a **container** that moves To Do→In Progress→**Done**. If it never closes, it's a **Label or Component**, not an Epic. |
| "Sub-tasks are just small tasks." | Size is irrelevant. Sub-tasks are constrained: not on boards by default, don't count independently in velocity, locked to the parent's project, **can't be in a different sprint than the parent**. Use only for parallel work, per-step time tracking, or board visibility — else use a checklist. |
| "Story vs Task is about size." | **Story = user/customer value; Task = team/operational/technical need.** Size doesn't decide it. |

**The decision heuristic (works beyond software):**
- **Does it deliver value to an end user/customer?** → **Story.** Is it operational/technical/administrative? → **Task.** (So *Task* is the natural default for ops, engineering, and business work — most non-software items are Tasks, not Stories.)
- **Will it fit in one sprint/cycle?** → deliverable level (story/task). **Can't be finished in one cycle?** → container level (epic). A healthy epic ≈ 1–3 months / ~5–15 children.
- **Is it a step of one deliverable, done by someone in parallel?** → sub-task. Otherwise a checklist item.
- **Is it a true cross-cutting dependency** ("blocks", "duplicates")? → an **issue link**, *not* a parent/child relationship. (Links don't roll up in reporting; hierarchy does — don't confuse the two.)

**Adapt to the org's own standard (the key move).** Organisations map these levels to different names and frameworks — both are legitimate and must not be "corrected":
- *Atlassian-native SAFe:* Initiative → **Epic** → Story (keep Jira's Epic, add Initiative above).
- *SAFe-purist:* **Epic** → **Feature** → Story (rename Jira's "Epic" to "Feature", add a new "Epic" above).

So **always reason in role terms first** — "the container level", "the deliverable level", "the breakdown level" — then **discover and use the org's configured issue-type names** for those roles. When a team asks "is this an epic or a story?", the honest answer is: *"By role it's a [container/deliverable], which on this instance is called '[their name]'."* Never assume the words "Epic" and "Story" map to the standard roles on a given instance — verify.

For the full hierarchy treatment (non-software reinterpretation, the DC Epic Link/Parent Link workaround, Advanced Roadmaps level setup), read **`references/hierarchy.md`**.

## Discover before advising (and stay language-safe)

A recommendation that hardcodes "Bug", "Done", or "High" is wrong on the next instance — and doubly wrong on a non-English one, where the configured value might be "Fehler", "Erledigt", "Hoch". **Discover the org's real values, and anchor logic on language-independent keys.** (Fetch these via `jira-cli` or the `mcp-atlassian` discovery tools — `jira_get_transitions`, `jira_search_fields`, `jira_get_link_types`, `jira_get_project_components`, `jira_get_all_projects`; the full endpoint↔tool mapping is in `references/multilingual-and-discovery.md`. This skill says *what* to look at and *which key to anchor on*.)

| To learn… | DC REST v2 | Language-safe anchor |
|---|---|---|
| Issue types (+ `subtask` flag, hierarchy) | `GET /rest/api/2/issuetype` | numeric `id` |
| Statuses **and their category** | `GET /rest/api/2/status` | **`statusCategory.key`** — fixed enum `new` / `indeterminate` / `done` / `undefined` (→ To Do / In Progress / Done) |
| Priorities / resolutions | `GET /rest/api/2/priority`, `/resolution` | `id` |
| Link types | `GET /rest/api/2/issueLinkType` | `id` |
| Components (per project) | `GET /rest/api/2/project/{key}/components` | `id` |
| Fields (system + custom) | `GET /rest/api/2/field` | **`untranslatedName`**, **`clauseNames`** incl. **`cf[NNNNN]`** |
| Valid transitions from current status | `GET /rest/api/2/issue/{key}/transitions` | transition **`id`** (act by id, not localized name) |
| What a project actually *allows* | `GET /issue/createmeta`, `/issue/{key}/editmeta` | reflects real config, not English defaults |

**The two rules that prevent localized-value bugs:**
1. **Anchor on keys, not names.** Prefer JQL `statusCategory = Done` over `status = "Done"`; reference custom fields by `cf[NNNNN]`; transition by `id`. These survive any UI language and any per-user translation.
2. **Canonical strings on DC need a service account.** REST/webhooks return values in the **authenticating (or triggering) user's** profile language — there is **no per-request override on DC** (`X-Force-Accept-Language` is Cloud-only). To get stable canonical strings, use a **service account whose profile language is set to the canonical language**, and one with **admin rights** (permissions decide which statuses are even visible — a separate axis from language).

Full discovery recipes, the non-English search/indexing caveats (CJK, umlaut+wildcard, Indexing Language = "Other"), and the JQL canonical-vs-translated asymmetries are in **`references/multilingual-and-discovery.md`**.

## Lean levers — de-bloat the configuration

The "filling a ticket is a chore" dread is almost always **too many fields on the Create screen**. The fixes, highest-leverage first:

1. **Minimum-viable Create screen.** Make the **Create** screen shorter than **Edit/View** (a Screen Scheme maps the three operations to *different* screens). Ask "what's the minimum needed *right now*?" — not "what could we capture?" Too many create fields make users enter garbage or avoid Jira, destroying data quality. **Load-bearing constraint:** a *Required* field must appear on every Create screen, so to drop one, first make it Optional (Field Configuration) or set it via default/post-function.
2. **Challenge every required field and every custom field.** Apply the 4-question test — a field earns its place only if it (a) drives cross-team reporting, (b) is needed by automation, (c) must be JQL-searchable, or (d) must survive an item moving projects. New global field also needs **a named owner** (this gate kills most requests). DC guardrail: **<800 custom fields optimal, >1,200 degraded** — global-context fields and fields-with-defaults are the costly ones; use the **Instance Optimizer** to find prune/scope candidates.
3. **6–9 core statuses, no "status zoo".** Start from To Do / In Progress / Done; add only statuses the team actually uses. Transition paths grow combinatorially.
4. **Status vs Resolution — the biggest single fix.** Don't model "done-ness" as many terminal statuses. Use **one or two terminal statuses + a small Resolution set** (Done, Won't Fix, Duplicate, Canceled). Set Resolution **only on closing transitions** (a transition screen), never on the Create/Edit screen. **Reopen trap:** clear the Resolution on any reopen transition or reports will keep counting the item as resolved.
5. **Fewer issue types.** Prefer built-ins; substitute a **label / component / "Phase" select field** for a new issue type when the need is just categorisation.

Concrete DC admin click-paths (Screen Schemes, Field Configuration schemes, the clear-Resolution-on-reopen post-function) are in **`references/lean-config.md`**.

## Kill the busywork — workflows, automation, reporting

- **Simplify workflows; govern against drift.** Few statuses, clear transitions, shared/standard workflow schemes so teams don't each invent their own. DC's **Simplified Workflow** (manage statuses from board config, auto-sets Done resolution) is a fine lean default for a small/non-software team — but it trades away per-issue-type workflows, transition screens, and app extensions, so it's too constrained for governed multi-team setups.
- **Automate the toil — Automation for Jira is free/native in DC.** High-value rules: auto-transition, auto-assign (round-robin/balanced), field hygiene on transition, parent/child roll-up (a *branching recipe* — there's no one-click "update parent from children"), SLA nudges. **But automation sprawl is its own dread** — "300+ rules, someone pinged 11 times". Maturity is *fewer, owned, boring* rules: scope each to the projects it touches, filter early, **never chain-fire on generic triggers** like "Issue updated", and name them `[Project] - [Trigger] - [Action]`.
- **"Update the board, not a doc."** Kill hand-written status reports — they go stale and get bypassed. Make Jira the single source of truth: live dashboards off **shared filters**, not Excel exports ("if someone is exporting to Excel, your SSOT is already broken"). **WIP limits + flow metrics** (cycle time, throughput, CFD) keep the board honest with minimal effort. Healthy signal: the team updates the board daily without being told, and it matches reality.

Automation recipes, service limits, the anti-chain-fire rules, and board WIP/swimlane/quick-filter mechanics are in **`references/workflows-automation.md`**.

## Non-software & non-agile teams

Jira is not just for developers — but its software defaults (sprints, story points, velocity, "Bug") are exactly what makes non-software teams dread it. De-software-ify:

- **Kanban, not Scrum.** Flow + WIP limits + clear ownership, not sprint ceremonies. **Drop story points and velocity entirely**; estimate with time or due dates if at all.
- **Reinterpret the hierarchy:** the container/"epic" is the large deliverable (a campaign, a facility change, an audit cycle, an infrastructure or transport project); Tasks are the actionable items; Sub-tasks the steps. Most items are **Tasks** (operational), not Stories.
- **Vocabulary and fields fit the domain.** Use issue types and field names the team recognises; remove dev-only fields from their screens. On DC, business projects build on the always-present **Jira Core** base.
- **Standardise recurring work** (onboarding, monthly close, inspections) with a scheduler app instead of recreating tickets by hand.
- **Roll out lean: one team → a few → org-wide** (Minimum Viable Process Change), never a big-bang enterprise config — and never force one team's process on another (*"the team should serve its goals, not serve Jira"*).

More non-software patterns and the workflow-design workshop method: **`references/non-software.md`**.

## Diagnose-the-dread playbook

Match the symptom, name the cause, apply the smallest fix:

| Symptom the team reports | Likely root cause | Lean fix |
|---|---|---|
| "Filling in a ticket takes forever" | Too many required/optional fields on Create | Minimum-viable Create screen; make fields optional; 4-question field test |
| "Jira is slow" | Custom-field sprawl (esp. global-context) | Audit with Instance Optimizer; scope/delete fields; aim <800 |
| "We never know if something's actually done" | "Done-ness" modeled as statuses; Resolution unset/misused | One/two terminal statuses + Resolution set on close; clear on reopen |
| "Our workflow is a maze" | Status zoo / per-project workflow drift | Cut to 6–9 statuses; shared workflow scheme; consider Simplified Workflow |
| "Standups are status theater / reports are stale" | Hand-maintained status outside Jira | "Update the board, not a doc"; live dashboards off shared filters |
| "Is this an epic or a story?" (recurring) | Hierarchy defined by name, not role; no shared standard | Teach role-based levels; map to the org's configured names; write it down once |
| "Different teams use epic/story differently" | No deliberate standard, or a legitimately different framework | Don't force uniformity; document each unit's role-mapping; align only where cross-team reporting needs it |
| "We're drowning in tickets / stale backlog" | No WIP discipline; tickets that generate no value | WIP limits; delete value-less tickets; backlog hygiene; fewer/larger tickets |
| "Automation keeps doing weird things / spamming" | Rule sprawl, chain-firing, broad triggers | Inventory & prune rules; scope + filter early; kill generic-trigger chains |
| "Non-English issues/statuses break our JQL/automation" | Matching localized names instead of keys | Anchor on `statusCategory`/IDs/`cf[NNNNN]`; service-account locale for canonical strings |
| "A team hates being forced into Jira" | Software process imposed on non-software work | De-software-ify (Kanban, no points); fit vocabulary; let the team own its process |

## Anti-patterns (call these out)

1. **Hierarchy by name, not role** — assuming "Epic"/"Story" mean the same on every instance. Always verify the org's mapping.
2. **Epic that never closes** — should be a Label/Component.
3. **Sub-tasks as a to-do checklist**, or spanning sprints — use a checklist or split into stories.
4. **Required field with no named owner / no reporting use** — make it optional or delete it.
5. **Many "done-like" statuses** instead of the Resolution field.
6. **Velocity/story points as a cross-team or per-person KPI** — vanity metric; it corrupts estimation. Velocity is a *team planning aid* only.
7. **Status theater** — maintaining a status doc/Excel alongside Jira.
8. **Automation sprawl** — more rules ≠ more mature; boring, owned, scoped rules win.
9. **Forcing one process org-wide** — makes the team serve Jira. Let teams own their process; standardise only where cross-team reporting demands it.
10. **Auto-translating or "correcting" non-English content** — never. It's normal; preserve it; discover real values.

## What to read next

| File | Read when… |
|---|---|
| `references/hierarchy.md` | Deciding epic/story/task/sub-task; setting/adapting an org standard; Initiative levels; the DC Epic Link/Parent Link gotcha; non-software hierarchy |
| `references/lean-config.md` | De-bloating — custom-field guardrail & audit, minimum-viable Create screen (screen schemes + field configs), status-vs-resolution mechanics, issue-type minimalism |
| `references/workflows-automation.md` | Simplifying workflows, Automation-for-Jira recipes + sprawl governance, board WIP/swimlanes/quick filters, "update the board not a doc" |
| `references/non-software.md` | Setting up Jira for ops / engineering / business teams — Kanban over Scrum, no story points, recurring work, lean rollout |
| `references/multilingual-and-discovery.md` | Non-English instances — discovery recipe, language-independent anchors, JQL canonical-vs-translated, search/indexing (CJK, umlaut), service-account locale |
| `references/sources.md` | Verifying or freshening a claim — per-row source + tier + what it supports |

**Execution:** to *carry out* any of this (creating issues at the right level, transitioning by id, JQL, links, bulk edits, ADF), act through **`jira-cli`** (sibling skill) or the **`mcp-atlassian`** MCP server — both Data-Center-capable, both issue-level. This skill decides *what* and *how to structure work*; those tools do the *how*. Anything needing schema/admin (screens, fields, workflows, types) → hand the user the exact steps; neither tool can do it.
