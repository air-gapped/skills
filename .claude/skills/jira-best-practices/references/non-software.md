# Jira for non-software teams — de-software-ify it

Jira is used far beyond software: operations, IT service management, systems/hardware engineering, manufacturing, infrastructure, services, marketing, HR, finance, legal, program/portfolio management, and physical-deliverable projects. Its **software defaults** (sprints, story points, velocity, "Bug") are precisely what makes these teams dread it. The job is to remove the software machinery and fit the team's real process.

## What you're working with on Data Center

- **"Jira Core" is the always-present business/platform base** on Data Center; Jira Software and JSM are *add-on applications* on top. Non-software ("business") projects build on this base.
- The 2024–25 **"Jira Work Management → single Jira" unification is Cloud-only.** DC never had a product called "Jira Work Management" — and the rich Cloud business views don't exist natively on DC.
- **Native List / Calendar / Timeline views are Cloud-only.** On DC, non-software teams get these only via **Marketplace apps** (Structure, BigPicture, Calendar for Jira, ActivityTimeline). Don't promise native list/calendar/timeline on DC.
- The 23 Cloud business templates have **no shipped DC equivalent** — DC non-software teams build workflows/issue types from the Jira Core base (use the workshop method below).

## Replace the agile machinery

| Software default | Non-software replacement |
|---|---|
| Scrum / sprints | **Kanban** — steady flow, clear ownership, no sprint ceremonies |
| Story points / velocity | **Time-based estimates or due dates** (or no estimate at all). *Never* track velocity for non-software teams. |
| Burndown / sprint reports | **WIP limits + flow metrics** (cycle time, throughput, cumulative flow) |
| "Story" / "Bug" | Domain vocabulary — issue types and field names the team recognises |
| Manual recurring tickets | A **scheduler app** that auto-creates recurring operational work |

**Kanban-over-Scrum** is the default recommendation for business/ops teams: *"the goal is steady flow and clear ownership, not sprint ceremonies."* Kanban *"focuses on status rather than due dates"*; WIP limits (min/max per column) surface bottlenecks.

## Reinterpret the hierarchy (no developer concepts required)

Read the **roles**, not the software words: the **Epic/container** is the large deliverable (a campaign, a facility change, an audit cycle, an infrastructure or transport project); **Tasks** are the actionable items; **Sub-tasks** the steps. **Most non-software items are Tasks** (operational), not Stories — don't force a "Story" habit where work isn't user-story-shaped. The full per-domain role table is in `hierarchy.md`.

## Fit the configuration to the domain

- **Custom issue types per business function** where it helps (onboarding, contract renewal, change request, budget approval) — but apply the issue-type-minimalism rule (`lean-config.md`): prefer a **label / component / "Phase" field** over a new type when it's just categorisation.
- **Strip dev-only fields** (story points, sprint, fix-version-as-release) from these teams' screens entirely.
- **Keep workflows to ~5–7 steps.** *"A workflow your team cannot describe from memory is too complex."* DC's **Simplified Workflow** is often the right lean default for a single non-software team (caveats in `workflows-automation.md`).
- **Standardise recurring work** (onboarding, monthly close, inspections, operational check-ins) with a scheduler app rather than recreating tickets by hand.

## Designing a non-software workflow (the workshop method)

1. **Run a short workshop**: map the real process on a whiteboard (the actual states work passes through).
2. **Translate to statuses + transitions** — keep it to the genuine states. Example (content review): To-Do → Draft → Under Review → (Add Web Tasks) → Live on Site → Done, with a "Submit for review" transition.
3. **Use Conditions / Validators / Post-functions for control**, not extra statuses: Conditions gate who can transition (e.g. only managers approve); Validators verify required input before a status change; Post-functions do follow-up (set a field, notify).
4. **Set the Resolution on close**, not as a status (see `lean-config.md`).

Atlassian itself cites these non-software domains for Jira Core: marketing (launch campaigns), HR (track candidates), finance (approve purchases, close books), legal (document revisions), supply chain (manufacturing process), and more.

## Roll out lean — and don't impose

- **Minimum Viable Process Change:** start with **one team**, prove it, expand to a few, then org-wide — never a big-bang enterprise config.
- **Let the team own its process.** The dominant non-software dread is org-wide standardisation that forces *"the team to serve Jira rather than Jira serving the team."* Standardise across teams **only where cross-team reporting genuinely requires it**; otherwise honour each team's local convention.
- **Be honest about fit.** Sometimes Jira is genuinely the wrong tool for a given non-software team (they "don't think in sprints and story points" and keep a parallel tracker). If so, say so — but if Jira is the mandate, the de-software-ification above makes it tolerable.

## Sources
See `references/sources.md`. Key anchors: Jira Core overview / applications overview (DC, Tier A); eficode JWM-merger-is-Cloud-only (Tier A/B); Atlassian "set up business workflows in Jira Core" + lean-process-improvement (Tier A); titanapps/Atlassian Kanban-with-Jira (Tier A/B); Marketplace "Calendar for Jira" DC version support (Tier A); scrum.org "team serving Jira" anti-pattern (Tier B).
