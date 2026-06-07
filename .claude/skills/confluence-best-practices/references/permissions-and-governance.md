# Permissions, governance, and the Jira boundary

Permissions are where Confluence quietly hides content and where sprawl creeps in. This file has the DC mechanics, the "I can't see the page" playbook, the governance levers, and the Confluence↔Jira boundary.

> **Who does what.** Page **restrictions** are agent-actionable (`GET/PUT /content/{id}/restriction`). **Space permissions, default-permission schemes, global permissions, and the Jira application link are admin** — diagnose and hand the user the steps.

## The three layers

1. **Global permissions** (site-wide): **Can Use**, **Personal Space**, **Create Space(s)**, **Confluence Administrator**, **System Administrator**. (`confluence-administrators` is the group that can see *all* restricted pages everywhere — distinct from the limited "Confluence Administrator" permission.)
2. **Space permissions** (per space): view / add / delete pages / blogs / comments / attachments / restrictions-removal / export / admin — assignable to groups, users, and anonymous.
3. **Page restrictions** (per page): view and/or edit.

The day-to-day mental model is "space permissions vs page restrictions," but the agent must know the global layer because **`Create Space(s)`** and `confluence-administrators` live there and drive governance.

## Precedence — additive vs subtractive (the rule that ends arguments)

- **Space permissions are ADDITIVE:** a user's effective access is the *union* of every group they're in plus any individual grant. Revoking one group/individual does nothing if another group still grants it.
- **Page restrictions SUBTRACT — they narrow, never grant.** *"Restrictions don't override a person's space permission":* a restriction can **deny** a user who has space-View, but can **never give** View to someone who lacks space-View. Net: a user sees a page only if they pass **global Can-Use AND space-View AND (no excluding view-restriction on the page or any ancestor).**
- **View restrictions CASCADE to child pages; edit restrictions do NOT.** Edit must be set per page (CONFSERVER-5095, open ~20 years).
- **Admin override:** space admins, `confluence-administrators`, and sysadmins can remove restrictions even from pages they can't see — restrictions are not confidentiality against admins.
- You **cannot restrict yourself out** — Confluence adds you to the restriction automatically.

## The "I can't find / see the page" playbook (the #1 permission dread)

The usual cause is **an inherited view-restriction on an *ancestor*** — the page silently drops from search results and the page tree with **no error message**. Diagnose in order:

1. Confirm the user has **space View** permission (Space tools → Permissions).
2. **Walk *up* the page tree**, checking each ancestor's Restrictions dialog (it flags inherited restrictions). The restriction is usually higher up, not on the page itself.
3. Check the page's own restrictions.

Other traps:
- **Request-access fails** if there's no SMTP server, or the user lacks space permission, or an ancestor is restricted.
- **Converting a page-with-children to a blog post** strips the children's inherited restrictions (blogs have no parent) → silent over-exposure.
- **Cluster cache lag** — permission changes can take time to propagate across DC nodes.
- **`CONFANCESTORS` desync** (after some upgrades, or template-created children — CONFSERVER-25189/87720) makes inheritance *look* applied but unenforced; fix = rebuild ancestors, flush the Inherited-Content-Permissions cache, rebuild the index.

## Governance — keep it open, keep it lean

- **Open by default.** Atlassian's own stance: *"keep Confluence as open as possible — it's designed to be open by default."* Restriction is the justified exception (HR, legal, security), not the posture; over-restriction creates **knowledge silos** and feeds the "can't find anything" dread.
- **Restrict `Create Space(s)`** (Admin → General Config → Global Permissions) to a **champions group** — because *whoever creates a space automatically becomes its admin*, broad space-creation rights are the Confluence analogue of "sprawl correlates with admin count." Champions handle requests and create spaces consistently.
- **Set default new-space permissions** centrally (Admin → General Config → Space Permissions) so every new space starts from a sane, consistent baseline.
- **Use groups, not individuals** — individual grants "rapidly become unwieldy." Delegate space admin to a **group** (e.g. `space-administrators`) so membership churn doesn't touch each space.
- Lifecycle/ownership/naming standards are mostly **org policy** the skill prescribes (Atlassian's primary docs are thin here) — pair them with the Page-Properties ownership dashboard (`lean-content-and-lifecycle.md`).

## The Confluence ↔ Jira boundary (what belongs where)

The clean split — and misusing one as the other is its own dread:

- **Confluence = durable knowledge:** requirements, decisions/ADRs, design docs, runbooks, retros, release-note narrative — the *how and why*, authored and reasoned about, versioned for reading.
- **Jira = trackable work with status:** stories, tasks, bugs, epics, sprints — items with a workflow.
- **Misuse signals:** tracking task status on Confluence pages (goes stale, no workflow); burying long-form rationale in Jira issues (poor to read/version). The fix is a **requirements/decision page in Confluence with an embedded Jira Issues macro** pulling live status — each tool does its job.

**Integration mechanics (DC):**
- Prerequisite: an **Application Link** between Confluence and Jira (admin).
- **Jira Issues macro** — three modes: single issue (paste a URL), **JQL table**, or **count**. It is **permission-aware** ("shows only issues the user is authorized to view"; restricted issues prompt Log-in-&-Approve) — it does *not* leak Jira-restricted issues.
- **Create a Jira issue from a Confluence page** (highlight text → Create issue) is DC-native; auto-linking to an Epic works only in Jira Software Classic projects.
- Also: **Jira Chart** macro, **Jira Report** blueprint, the page **Jira Links** button (issue/epic/sprint count).
- **Cloud-only — flag it:** **Smart Links** (auto-unfurling live issue links), AI summaries, Live Docs, and the `/jira` slash-create flow are **Cloud UX, not DC** (Smart Links = CONFSERVER-87786, open). On DC use the Jira Issues macro + plain links. Don't source DC integration capability from Atlassian's marketing tutorial, which depicts Cloud.

## Sources
See `references/sources.md`. Key anchors (Tier A): Atlassian "Page Restrictions", "Permissions and Restrictions", "Global Permissions Overview", "Permissions best practices", "Jira Issues macro", "Use Jira applications and Confluence together"; CONFSERVER-5095/25189/87720/87786.
