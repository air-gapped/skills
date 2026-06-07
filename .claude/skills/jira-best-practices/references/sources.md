# Sources

External claims in this skill, with source, tier, and what they support. **Last verified: 2026-06-07** (research date). Re-verify before relying on dated facts (DC versions, EOL dates, Cloud-vs-DC feature splits) — these move.

Tiers: **A** = official Atlassian docs / issue tracker / primary spec · **B** = experienced practitioners / solution partners / surveys · **C** = vendor-advocacy / community opinion (down-weighted, used for *principles* not facts).

Full research provenance: `autoresearch/results/lean-jira-best-practices-research-2026-06-07.md` (9 agents, STORM multi-perspective, depth 2).

## Execution layer (agent tooling)

| Source | Tier | Supports | Verified |
|---|---|---|---|
| github.com/sooperset/mcp-atlassian (README) | A/B | mcp-atlassian: Jira+Confluence MCP, **DC supported (Jira v8.14+, PAT auth)**, key tools, 72 tools, READ_ONLY_MODE | 2026-06-07 |
| mcp-atlassian.soomiles.com/docs/tools-reference | A/B | Full jira_ tool list (read/write), `jira_get_transitions`/`jira_search_fields`/`jira_link_to_epic`/…; **no admin/schema tools** | 2026-06-07 |
| (sibling skill) `jira-cli` | — | `jira` CLI execution surface, automation contract, ADF, auth — the other execution path | 2026-06-07 |

## Hierarchy

| Source | Tier | Supports | Verified |
|---|---|---|---|
| support.atlassian.com/.../what-are-issue-types | A | Verbatim work-type defs; 3-tier hierarchy; parentage rules | 2026-06-07 |
| atlassian.com/agile/project-management/epics-stories-themes | A | Initiative/Epic/Story/Theme; Theme = goal/label, not a level; sizing | 2026-06-07 |
| confluence.atlassian.com/.../configuring-hierarchy-levels (Advanced Roadmaps DC) | A | DC custom hierarchy levels; issue-type mapping; system-wide effect | 2026-06-07 |
| jira.atlassian.com/browse/JPOSERVER-4430 | A | DC Epic Link/Parent Link **not** unified (closed Not-a-bug); workaround | 2026-06-07 |
| support.atlassian.com/.../upcoming-changes-epic-link-replaced-with-parent | A | Cloud Parent unification; DC "not affected" | 2026-06-07 |
| seibert.group/.../jira-story-vs-task-vs-epic | B | Misconceptions; Story=value/Task=operational; sub-task constraints; non-software examples | 2026-06-07 |
| tempo.io/blog/which-safe-hierarchy-should-you-choose | B | Two valid SAFe mappings; "depends on your situation" | 2026-06-07 |

## Lean configuration

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/ENTERPRISE/.../Managing number of custom fields in Jira DC | A | **800/1,200** custom-field guardrail; 4 perf-impact areas | 2026-06-07 |
| support.atlassian.com/jira/kb/...too many custom fields | A | Context-per-issue driver; default-value cost; 1,916-field/12–13 s case | 2026-06-07 |
| confluence.atlassian.com/adminjiraserver/optimizing-custom-fields | A | Global-context index cost; Instance Optimizer scan | 2026-06-07 |
| community.atlassian.com/.../Designing Jira Fields in 2026 | B | 4-question field-vs-form test + named-owner gate (Forms = Cloud-centric) | 2026-06-07 |
| thejiraguy.com/.../this-is-why-we-cant-have-nice-screens | B | Minimum-viable Create screen; garbage-data failure mode | 2026-06-07 |
| salto.io/.../reducing-jira-customizations | B | Deletion criteria; admin-count/sprawl correlation; UI slowdown 1000+ | 2026-06-07 |
| confluence.atlassian.com/adminjiraserver/associating-a-screen-with-an-issue-operation | A | Screen scheme Create/Edit/View mapping; Default entry; View-custom-fields quirk | 2026-06-07 |
| confluence.atlassian.com/adminjiraserver/specifying-field-behavior | A | Field Config Required/Optional, Hide/Show; required-must-be-on-create; hidden≠required | 2026-06-07 |
| confluence.atlassian.com/adminjiraserver/associating-field-behavior-with-issue-types | A | Field-config scheme per project×issue-type | 2026-06-07 |
| support.atlassian.com/jira/kb/clear-the-resolution-field-when-reopened | A | Native post-function clear-on-reopen; cloud+DC | 2026-06-07 |
| support.atlassian.com/jira/kb/best-practices-on-using-the-resolution-field | A | Resolution only on transitions; REST ignores transition screens | 2026-06-07 |
| sparxsys.com/.../how-many-issue-types | B | Issue-type minimalism; label/component/Phase substitution | 2026-06-07 |

## Workflows, automation, reporting

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/automation/understand-versions-licenses-upgrades | A | **A4J free/native in DC** since JSW 9.0 (8.0+ no separate license) | 2026-06-07 |
| confluence.atlassian.com/automation/automation-service-limits | A | Exact DC automation service limits + REST property keys | 2026-06-07 |
| confluence.atlassian.com/spaces/automation112/.../optimizing automation rules | A | What NOT to do (scoping, condition order, no chain-firing, no batch) | 2026-06-07 |
| confluence.atlassian.com/automation/actions / triggers | A | DC automation action + trigger list; no one-click parent-from-children | 2026-06-07 |
| onpointserv.com/.../jira-automation-in-2026 | B | 7 recipes + guardrails; sprawl numbers; naming convention | 2026-06-07 |
| community.atlassian.com/.../Our Jira Automation Rules Are Out of Control | B | 300+ rule sprawl; "pinged 11 times"; boring rules | 2026-06-07 |
| idalko.com/blog/jira-workflow-best-practices | B | Status minimalism; status-vs-resolution; governance vs drift | 2026-06-07 |
| community.atlassian.com/.../10 Jira Status Anti-Patterns | B | 6–9 statuses; anti-patterns + fixes; time-in-status validation | 2026-06-07 |
| community.atlassian.com/.../single-source-of-truth-in-jira | B | "Update the board, not a doc"; SSOT anti-patterns | 2026-06-07 |
| apwide.com/live-project-status-reports-dashboards-in-jira | C | Manual-report busywork; live dashboards thesis | 2026-06-07 |
| confluence.atlassian.com/jirasoftwareserver/configuring-{a-board,swimlanes,quick-filters} | A | WIP (column-level), swimlanes, quick filters config | 2026-06-07 |
| confluence.atlassian.com/.../using-the-simplified-workflow | A | DC Simplified Workflow + limitations | 2026-06-07 |
| atlassian.com/agile/kanban/wip-limits + .../kanban-metrics | A | WIP limits; flow metrics | 2026-06-07 |

## Non-software

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/jiracoreserver/jira-core-overview + applications overview | A | Jira Core = always-present business base on DC | 2026-06-07 |
| eficode.com/.../jira-software-and-jira-work-management-have-merged | A/B | JWM→Jira merger is **Cloud-only**; DC separate | 2026-06-07 |
| atlassian.com/blog/jira-core/how-to-set-up-business-workflows-in-jira-core | A | Non-software workflow examples; conditions/validators/post-functions | 2026-06-07 |
| atlassian.com/blog/announcements/introducing-jira-work-management | A | 23 Cloud business templates; business vocabulary | 2026-06-07 |
| titanapps.io/blog/jira-kanban-scrum + atlassian.com/agile/tutorials/how-to-do-kanban-with-jira | A/B | Kanban over Scrum; WIP limits; recurring work | 2026-06-07 |
| marketplace.atlassian.com/.../calendar-for-jira | A | Calendar is a DC add-on (DC 10.3–11.3 support) | 2026-06-07 |
| scrum.org/.../jira-anti-patterns | B | "team serving Jira" anti-pattern | 2026-06-07 |
| atlassian.com/agile/project-management/lean-process-improvement | A | Minimum Viable Process Change rollout | 2026-06-07 |

## June-2026 state

| Source | Tier | Supports | Verified |
|---|---|---|---|
| atlassian.com/licensing/data-center-end-of-life | A | DC EOL: sale-end 2026-03-30, renew 2028-03-30, read-only 2029-03-28 | 2026-06-07 |
| endoflife.date/jira-software | A | Server EOL 2024-02-15; latest **11.3.7 (2026-06-03)**; 11.3 & 10.3 LTS | 2026-06-07 |
| confluence.atlassian.com/jirasoftware/jira-software-11-3-x-release-notes | A | DC 11.x leanness guardrails (JQL cap, automation-rule restriction, optimizer, 10k board) | 2026-06-07 |
| atlassian.com/software/jira/ai | A | Rovo/AI is **Cloud-only**; DC via Cloud connectors | 2026-06-07 |
| community.atlassian.com/.../work-is-the-new-collective-term | A/B | issue→work item is **Cloud-only**; APIs keep "issue" | 2026-06-07 |
| uctoday.com / deiser.com (Projects→Spaces) | B | Project→Space rename **Cloud-only** | 2026-06-07 |
| newsletter.pragmaticengineer.com/.../2025-survey | B | Jira most-disliked dev tool 2025 | 2026-06-07 |
| survey.stackoverflow.co/2025 | B | GitHub overtook Jira as most-desired | 2026-06-07 |

## Multilingual & discovery

| Source | Tier | Supports | Verified |
|---|---|---|---|
| developer.atlassian.com/server/.../jira-issue-statuses-as-lozenges | A | `statusCategory` keys/ids/colors — language-independent anchor | 2026-06-07 |
| docs.atlassian.com/.../REST/8.20.0 + DC REST examples | A | Discovery endpoints; transitions by id; createmeta/editmeta; `untranslatedName`/`clauseNames`/`cf[ID]` | 2026-06-07 |
| jira.atlassian.com/browse/JRACLOUD-71793 (+ JRASERVER-74088) | A | Canonical-name fix Cloud-only; **no per-request language override on DC** | 2026-06-07 |
| confluence.atlassian.com/jirakb/get-custom-field-ids | A | Discover custom-field IDs via `/field` | 2026-06-07 |
| confluence.atlassian.com/adminjiraserver/translating-resolutions-priorities-statuses-issue-types | A | Canonical-name + per-language translation model | 2026-06-07 |
| support.atlassian.com/.../configure-jira-application-options | A | Indexing Language; mixed-language → "Other"; whole-word search | 2026-06-07 |
| jira.atlassian.com/browse/JRASERVER-{39215,39009,71096,15006}; AUTO-72; JRASERVER-40049 | A | JQL canonical-vs-translated; system/custom field asymmetry; webhook/transition localization; umlaut-wildcard bug; option-values untranslatable | 2026-06-07 |
| Apache Lucene CJKTokenizer docs + LUCENE-2458 | A | CJK bigram tokenization caveats | 2026-06-07 |

## Dread / critique (use for principles, read skeptically)

| Source | Tier | Supports | Verified |
|---|---|---|---|
| news.ycombinator.com/item?id=25590846 | A* | "It's your process, not Jira"; "minimal process" succeeds (*primary practitioner voices) | 2026-06-07 |
| medium.com/@ss-tech/jira-is-not-agile… | B | Surveillance/velocity-as-target; "team serving the tool" | 2026-06-07 |
| medium.com/@sjoerdnijland/buried-under-jira-tickets | B | Backlog bloat; "Jira is neutral"; validation gates | 2026-06-07 |
| success.atlassian.com/.../jira-custom-fields-governance | A | Atlassian's own "custom fields = administrative debt" admission | 2026-06-07 |
| aliazamkazmi…/Linear-vs-Jira; shortcut.com/blog/9-signs…; dev.to/linearb… | C | Competitor design principles to replicate inside Jira | 2026-06-07 |
| grandiasolutions.com/velocity-per-user-agile; divim.io/velocity-is-a-myth | B/C | Velocity-as-vanity-metric / per-user harm | 2026-06-07 |
