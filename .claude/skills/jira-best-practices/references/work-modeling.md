# Decomposing large work — one initiative into an ordered issue set

`hierarchy.md` answers the **vertical** question: what level is *this one* item
(container / deliverable / breakdown). This file answers the **horizontal** one:
given a large, multi-week initiative, **how many** issues, at **what grain**, in
**what order**, and how to **see progress**. The model is domain-neutral — the
same shape fits a software feature, an infra migration, a data-engineering
cutover, and a business campaign. Reason in roles and shapes, then map to the
org's configured names (per `hierarchy.md`).

**Contents:** the WBS + rolling-wave spine · the grain rule (issue / sub-task /
checklist / nothing) · the three decomposition axes · ordering via dependency
links · the assessment→issue-set pattern · one model across every domain ·
progress visibility on Data Center · agent scaffolding from a plan · anti-patterns.

## The spine — WBS + rolling-wave (the shape under every domain)

Project decomposition was solved long before Jira; map the theory onto the tiers:

- **The 100% rule.** A parent's children must sum to **exactly** the parent's
  scope — nothing missing, nothing extra, no overlap. The practical payoff: it
  catches the **prep and verify phases people silently drop** (if "assess" and
  "verify" aren't children, the epic doesn't actually total 100%).
- **Work package = the estimable leaf.** The lowest unit to estimate, assign,
  and track independently → the **deliverable tier** (Story/Task). Rule of thumb:
  it **fits one cycle, has one accountable owner**, and is independently
  trackable (the old "8–80h" heuristic is a guide, subordinate to those three).
- **Rolling-wave planning (the load-bearing idea).** The children **cannot all be
  enumerated up front** — detail emerges as prerequisite work completes. So the
  epic opens with a **planning/assessment issue + the main work**, and the
  remaining children are **created from that issue's output** (PMBOK calls the
  not-yet-detailed remainder a *planning package* — a placeholder to convert into
  real issues once enough is known). Fully detail Phase 0 + gating prereqs + the
  first wave; **stub later waves** as placeholders.
- **Milestone = a marker, not a sized issue.** A milestone is zero-duration — in
  Jira that's a **`fixVersion`/release** (or a label), never a Task with effort.
- **Two orthogonal views of the same issues.** Parent/child = the **scope** view
  (rolls up in reporting/roadmaps). Issue links = the **sequence** view (does
  *not* roll up). Don't conflate them (see Ordering below).

## The grain rule — issue vs sub-task vs checklist vs *nothing*

Default to the **lightest** container; promote upward only when earned. Walk the
ladder top-down and stop at the first that fits:

| Grain | Use when | Notes |
|---|---|---|
| **Own issue** | it will be **estimated / logged against**, has its **own owner**, runs **days**, has **own attachments**, scope is **still debated**, or needs **independent reporting/visibility** | the deliverable tier |
| **Sub-task** | a step of *one* issue that has a **different owner OR a different timeline** *and* needs board-visibility / parallel work / per-step time | constrained — see `hierarchy.md`; collaboration alone ≠ a sub-task |
| **Checklist line** | the routine steps within a single issue's own work | a checklist field/app, not tickets |
| **Nothing** | no decision, no handoff, no audit/reporting need, no lasting state change | don't ticket it at all |

**The "nothing" floor — when work is NOT a ticket** (the most-forgotten lean
move):
- **ITIL Standard Change**: low-risk, repeatable, **pre-authorized** work runs
  against an approved procedure — it is **not individually deliberated or
  ticketed** each time. Recurring routine ops belongs here.
- **SRE toil test**: *"if the system is in the same state after the task, it was
  toil"* — track the **class** in aggregate (and automate it away), don't open a
  ticket per occurrence.
- One-line test: **"Would I track, assign, estimate, hand off, or report this on
  its own?"** No → checklist or nothing.

**Right-size:** a single issue **fits one cycle/sprint**. Too-large → invisible
progress, never closes. Too-small → the **per-ticket ceremony tax** (estimate +
review + transitions + sign-off) swamps the actual work. There's no numeric
floor — go as fine as gives independent visibility/handoff, no finer.

## The three axes — and how they combine

Pick the axis (or mix) that makes **progress legible**:

- **By value / vertical slice** (software default). Each child is independently
  demoable; the **horizontal** split — "build the schema / the API / the UI" — is
  **tasks, not deliverables** (nothing ships alone). Splitting catalogs: **SPIDR**
  (Spike, Paths, Interfaces, Data, Rules — spike *last*, extract value first) and
  workflow-step / CRUD / business-rule / data variations. Ship the **walking
  skeleton** (thinnest end-to-end slice) first.
- **By phase** (applies far beyond software). **Prep/assess → execute →
  verify/follow-up.** The **prep and verify phases are mandatory children** (100%
  rule): skip prep and prerequisites get missed; skip verify and "done" is a
  guess.
- **By wave / batch / unit** (the same operation over N targets). Group by a
  **real boundary** — risk tier, failure domain, dependency, geography — **never
  one-issue-per-unit**. Order **lowest-blast-radius first** (dev before prod,
  small before large, canary → pilot → production); leave **buffer between waves**
  so early lessons feed later ones. Grain ladder: **unit → wave/batch (a Task) →
  epic**; per-unit steps are a **checklist inside the wave**, and **promote
  only the unit that fails** to its own issue.
- **Combine them.** The standard multi-week shape is **phase at the top, value-
  slice *or* wave inside the execute phase** — and the prep phase's assessment is
  what **defines the wave boundaries** (which targets are high-risk).

## Ordering — a dependency-link overlay, not nesting

Sequencing is a **separate layer** over the breakdown, expressed with **issue
links**, not parent/child:

- Use **`blocks` / `is blocked by`** to encode "A must finish before B." (`relates
  to` carries no order; on a fresh DC install the defaults are only relates /
  duplicates / blocks / clones — **no default `causes`**.)
- **Load-bearing rule:** a prerequisite whose omission is expensive or
  irreversible **must be a `blocks` link**, not a buried checklist line — the link
  is what stops an agent or a hurried human running steps out of order.
- **Shared-by-ALL dependency → one gating prerequisite task that blocks the
  epic**, *not* N links (e.g. "stand up the shared service before any wave").
- **Don't over-link.** Reserve links for true hard dependencies; a soft
  "nice-to-do-first" is just backlog order.

Viewing order on **DC**: Advanced Roadmaps' **Dependencies report** (arrows; red =
date/ordering warning) — but there's **no native computed critical path**; true
Gantt/critical-path needs **Structure** or **BigPicture**. The native per-project
**Timeline is Cloud-only**. (See the Cloud-vs-DC guard in SKILL.md.)

## The assessment → issue-set pattern (the general engine)

A discovery/audit/compatibility/capacity assessment produces a **verdict**, and
the verdict **mechanically generates the breakdown** — this is rolling-wave made
concrete:

| Verdict element | Jira artifact |
|---|---|
| the initiative / change set | **Epic** (container) |
| the assessment itself | **Phase-0 Task** — its *output defines the other children* |
| "needs work," independently risky | **own Task**, linked |
| "needs work," trivial / repeated | **checklist line**, or a **wave** Task |
| "hard blocker" | **gating Task**, `blocks` the epic |
| "A must precede B" | **`blocks` link** |
| **"already fine"** | **nothing** (no ticket) |

- **Triage is a filter** — "already fine" produces **no work item**. Ticketing
  passed/clean findings is pure ceremony.
- **Severity decides granularity**: independently risky → its **own** issue
  (1:1); a class of low-risk items → **grouped** into one task/wave.
- The children often **can't be listed until the assessment runs** — so the epic
  starts as *Phase-0 assessment + the main work*, and the agent fills in the rest
  from the verdict.

## One model, every domain (generality)

The same four-phase spine, with only the *grain* of "execute" changing:

| Domain | Container (Epic) | Assess (Phase 0) | Execute (sliced / waved) | Verify |
|---|---|---|---|---|
| **Software** | a feature/initiative | spike / design | **vertical slices** (SPIDR) | demo / acceptance |
| **Infra / ops** | a migration or upgrade | readiness/compat survey | **waves of move-groups**, risk-ordered | post-checks / drift re-scan |
| **Data engineering** | a table/format/engine cutover | inventory + parity plan | **per-table** (federate→build/backfill→validate→swap); **backfill in date-window waves** | parity validation / cut consumers |
| **Business / admin** | a campaign / program / audit cycle | brief / plan | **parallel streams** (channels, work packages) | measure / review gate |

Most non-software items are **Tasks**, not Stories (per `non-software.md`). Pick
no single domain as "the" template — the shape is the constant.

## Seeing progress on Data Center

- **Epic progress bar** = done/total of **direct child issues only** —
  **sub-tasks don't count**, and there's no native deep roll-up (Automation or an
  app where needed).
- **A board filtered to the epic** = the live "where are we" (phase/wave Tasks
  moving across columns).
- **`fixVersion` / Releases** = milestones (per-project, JQL-queryable, render on
  the Advanced Roadmaps timeline).
- **Above-Epic (Initiative)** needs **Advanced Roadmaps**; **plain DC has no level
  above Epic** — if an effort blows past ~15 meaningful children, split into
  several epics (e.g. one per cluster/site/domain) under an Initiative rather than
  one mega-epic (healthy epic ≈ 1–3 months / 5–15 children, per `hierarchy.md`).

## Agent execution — scaffold the tree from a plan

Build the whole structure in a controlled pass, then keep it idempotent:

1. **Create the epic** with `jira_create_issue` (Epic type; on DC the Epic Name
   field is set in the create step).
2. **Batch-create the children** with `jira_batch_create_issues` — **but it
   cannot set epic/parent links inline** (a `parent`/`epicKey` in a batch object
   is **silently dropped**). Pass only summary / type / description / components /
   **labels**.
3. **Link each child to the epic** — `jira_link_to_epic`, or
   `jira_update_issue {"epicKey": …}` (one call per child).
4. **Link dependencies** — one `jira_create_issue_link` per `blocks` edge
   (`jira_get_link_types` first; the exact `"Blocks"` spelling varies per
   instance). jira-cli equivalents: `jira epic add EPIC K1 K2 …` (the only
   *batched* epic-link, max 50) and `jira issue link A B Blocks`.

- **Idempotency is the agent's job** (no upsert; batch isn't atomic →
  re-running duplicates). **Tag every scaffolded issue with a deterministic label**
  (e.g. `agent-scaffold:<plan-id>`, which *does* flow through batch-create), then
  **search-before-create** (JQL `labels = "agent-scaffold:<plan-id>"` or
  `parent = EPIC-1`) before any write. Chunk bulk creates to **~50**.
- **Run read-only by default** — `READ_ONLY_MODE` is enforced server-side;
  `validate_only=true` dry-runs a batch. Elevate only for the owned project.
- **Derive every child from the plan/assessment** so a re-run converges and the
  human **approves rather than authors** (the lean payoff — the modeling judgment
  lives here + in the verdict, not in the user's head).

## Anti-patterns (call these out)

1. **One ticket per repeated unit** (30 servers = 30 tickets) — drowns progress;
   use **waves + checklist**, promote only the failure.
2. **No prep / verify child** — "execution" with no Phase 0 or Phase N; progress
   is unmeasurable and prerequisites get skipped.
3. **Ordering buried in a checklist** instead of a `blocks` link — invites
   out-of-order execution on exactly the steps where order is load-bearing.
4. **Ticketing the "already fine"** — remediation issues for things the
   assessment passed; pure ceremony.
5. **Sub-task sprawl** as a generic checklist — use a checklist unless a
   sub-task's constraints are actually needed (`hierarchy.md`).
6. **Fake hierarchy via links** — generic links don't roll up; only parent/child
   does. A linked "child" never aggregates to its apparent parent.
7. **A never-closing "container"** holding rolling work (a standing "Maintenance"
   epic) — that's a **Label/Component or a recurring-work scheduler**, not an
   Epic (`hierarchy.md` misconception #2).
8. **Over-linking** — `blocks` on soft preferences; reserve links for true hard
   dependencies.

## Sources

See `references/sources.md` (§ Work modeling / decomposition). Key anchors: PMI
WBS / 100% rule / work-package + rolling-wave & planning packages (Tier A/B);
Mountain Goat SPIDR & Humanizing Work story-splitting (Tier A); AWS Large
Migration wave/move-group playbook (Tier A); ITIL Standard Change + Google SRE
toil for the "floor" (Tier A/B); Atlassian DC issue-linking / Advanced Roadmaps
dependencies / versions (Tier A); the connected `mcp-atlassian` + `jira-cli`
source for the agent-scaffolding mechanics (Tier A). Full provenance:
`autoresearch/results/jira-work-decomposition-research-2026-06-07.md`.
