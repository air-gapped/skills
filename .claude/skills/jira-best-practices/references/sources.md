# Sources

Freshened: 2026-08-19 (exceptions: 3 bot-blocked rows, noted below)

**Contents:** Execution layer · Hierarchy · Work modeling / decomposition · Lean configuration · Workflows, automation, reporting · Non-software · Platform state (2026-08 pass) · Multilingual & discovery · Dread / critique

External claims in this skill, with source, tier, and what they support. Every
Tier-A hard fact was re-verified on 2026-08-19 with **no drift**: DC 11.3.10
(2026-08-07) latest, LTS 11.3→Dec 2027 and 10.3→Dec 2026, the DC sunset trio
(2026-03-30 / 2028-03-30 / 2029-03-28), the 800/1,200 custom-field guardrail,
and Automation-for-Jira free-and-native since JSW DC 9.0.

**Every source cell is a full, resolvable URL** as of this pass — 126 unique
URLs, 120 returning 200 on a single bulk sweep. This replaced the previous
shorthand style (elided paths like `community.atlassian.com/.../Designing Jira
Fields in 2026`, brace sets like `JRASERVER-{39215,39009}`, and Atlassian slugs
missing their trailing numeric ID and `.html`), which could not be probed and so
left most rows pinned to the 2026-06-07 research date across three passes. To
re-verify the whole file now:

```bash
grep -oE 'https://[^ )|+]+' references/sources.md | sed -E 's/[.,]+$//' | sort -u \
  | xargs -P 8 -I{} curl -s -o /dev/null -L -m 25 \
      -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36' \
      -w '%{http_code} {}\n'
```

**Standing exceptions — 3 rows that bot-block automated fetches** (live in a
browser, not gone): `medium.com/@ss-tech/...`, `www.pmi.org/learning/library/...`,
`www.smartinsights.com/guides/...`. A 403 on these is expected.
`bigpicture.one` also rate-limits (429) under a parallel sweep.

**Two references died and were replaced this pass:** `success.atlassian.com` no
longer resolves at all — the whole domain is gone, not just the page — so the
custom-field-governance citation now points at the equivalent `atlassian.com/blog`
article; and a paused Vercel deployment was dropped from the Linear-vs-Jira row,
which retains two live siblings.

Re-verify before relying on dated facts (DC versions, EOL dates, Cloud-vs-DC
feature splits) — these move.

Tiers: **A** = official Atlassian docs / issue tracker / primary spec · **B** = experienced practitioners / solution partners / surveys · **C** = vendor-advocacy / community opinion (down-weighted, used for *principles* not facts).

Full research provenance: `autoresearch/results/lean-jira-best-practices-research-2026-06-07.md` (9 agents, STORM multi-perspective, depth 2).

## Execution layer (agent tooling)

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://github.com/sooperset/mcp-atlassian + /releases | A/B | mcp-atlassian: Jira+Confluence MCP, **DC supported (Jira v8.14+, PAT auth)**, key tools, ~98 tools (63 jira + 35 confluence `@tool` registrations at v0.23.0, 2026-07-18; repo active), READ_ONLY_MODE; v0.23.0 adds `jira_get_project_epic_hierarchy` + `jira_get_cross_project_dependencies` (#1286) | 2026-08-18 |
| https://mcp-atlassian.soomiles.com/docs/tools-reference | A/B | Full jira_ tool list (read/write), `jira_get_transitions`/`jira_search_fields`/`jira_link_to_epic`/…; **no admin/schema tools** (URL 200 OK) | 2026-08-18 |
| (sibling skill) `jira-cli` | — | `jira` CLI execution surface, automation contract, ADF, auth — the other execution path | 2026-06-07 |

## Hierarchy

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://support.atlassian.com/jira-cloud-administration/docs/what-are-issue-types/ | A | Verbatim work-type defs; 3-tier hierarchy; parentage rules | 2026-06-07 |
| https://atlassian.com/agile/project-management/epics-stories-themes | A | Initiative/Epic/Story/Theme; Theme = goal/label, not a level; sizing | 2026-06-07 |
| https://confluence.atlassian.com/jiraportfolioserver/configuring-hierarchy-levels-802170489.html | A | DC custom hierarchy levels; issue-type mapping; system-wide effect | 2026-06-07 |
| https://jira.atlassian.com/browse/JPOSERVER-4430 | A | DC Epic Link/Parent Link **not** unified (closed Not-a-bug); workaround. Re-probed via public REST: still Closed/Not-a-bug, untouched since 2023-09 | 2026-08-18 |
| https://support.atlassian.com/jira-software-cloud/docs/upcoming-changes-epic-link-replaced-with-parent/ | A | Cloud Parent unification; DC "not affected" | 2026-06-07 |
| https://products.seibert.group/blog/jira-story-vs-task-vs-epic | B | Misconceptions; Story=value/Task=operational; sub-task constraints; non-software examples | 2026-06-07 |
| https://tempo.io/blog/which-safe-hierarchy-should-you-choose | B | Two valid SAFe mappings; "depends on your situation" | 2026-06-07 |

## Work modeling / decomposition

Full provenance for `references/work-modeling.md`: `autoresearch/results/jira-work-decomposition-research-2026-06-07.md` (8 agents, STORM, depth 2).

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://en.wikipedia.org/wiki/Work_breakdown_structure | A/B | 100% rule; work package = estimable leaf; 8/80 heuristic; deliverable/verb test; WBS-scope-vs-network-sequencing split | 2026-06-07 |
| https://www.pmi.org/learning/library/work-breakdown-structure-basic-principles-4883 + /moving-work-breakdown-structure-critical-path-6978 | A | work-package/critical-path defs; 80h-or-one-reporting-period; noun/verb boundary | 2026-06-07 |
| https://www.pmclounge.com/what-is-rolling-wave-planning/ + https://projstream.com/blog/how-rolling-wave-planning-makes-better-planning-packages-and-proposals/ + https://tensix.com/rolling-wave-planning-and-planning-packages/ | B | rolling-wave / progressive elaboration; **planning package** = "black-box placeholder" → convert to work packages; 3–6mo detail horizon | 2026-06-07 |
| https://www.mountaingoatsoftware.com/blog/five-simple-but-powerful-ways-to-split-user-stories + /two-examples-of-splitting-epics | A | SPIDR 5 split techniques (spike-last); worked vertical-slice seams | 2026-06-07 |
| https://www.humanizingwork.com/the-humanizing-work-guide-to-splitting-user-stories/ | A | 9-pattern split catalog; hamburger meta-pattern; two split-evaluation tests | 2026-06-07 |
| https://blog.crisp.se/2013/07/25/henrikkniberg/elephant-carpaccio-facilitation-guide + https://en.wikipedia.org/wiki/User_story + https://jpattonassociates.com/story-mapping/ | A/B | thinnest end-to-end slice first; breakdown-vs-release-overlay (ordering is separate) | 2026-06-07 |
| https://www.herocoders.com/blog/when-not-to-use-checklist-jira + https://community.atlassian.com/forums/App-Central-articles/Stop-Using-Subtasks-as-a-To-Do-List-And-What-to-Do-Instead/ba-p/3194274 | B/C | grain ladder; earns-its-own-issue tests; sub-task = different owner/timeline | 2026-06-07 |
| https://sre.google/sre-book/eliminating-toil/ + https://sre.google/workbook/eliminating-toil/ | A | toil = "same state after → don't ticket each instance"; track the class in aggregate | 2026-06-07 |
| https://wiki.en.it-processmaps.com/index.php/Change_Management + https://www.manageengine.com/products/service-desk/it-change-management/it-change-types.html + https://www.servicenow.com/community/developer-blog/mastering-dynamic-ci-groups-in-servicenow-best-practices-key/ba-p/3271579 | B/C | **Standard vs Normal vs Emergency** change; Change Model pre-authorises recurring work (not individually ticketed); one change record over a CI fleet | 2026-06-07 |
| https://www.rubick.com/three-anti-patterns-for-project-management/ + https://age-of-product.com/jira-anti-patterns/ + https://techcrunch.com/2018/12/09/jira-is-an-antipattern/ | B | over-decomposition costs; completion bias; "thousand little waterfalls" | 2026-06-07 |
| https://ascendle.com/ideas/splitting-epics-and-user-stories/ + https://agilepainrelief.com/blog/story-slicing-how-small-is-enough/ | B | upper-bound sizing (story < sprint); per-ticket ceremony tax; no numeric floor | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/configuring-issue-linking-938847862.html | A | **4 default link types** (relates/duplicates/blocks/clones); **no default `causes`**; blocks = canonical for order; don't delete Clones | 2026-06-07 |
| https://confluence.atlassian.com/jirasoftwareserver/the-dependencies-report-in-advanced-roadmaps-1077915784.html + /dependencies-in-advanced-roadmaps-1044784190.html + /view-your-advanced-roadmaps-plan-1044784216.html + https://confluence.atlassian.com/jiraportfolioserver/scheduling-dependencies-968677365.html | A | AR dependency viz (red=warning); Blocks=default dependency; sequential/concurrent auto-schedule; **no native critical path**; AR bundled since 8.15 | 2026-06-07 |
| https://support.atlassian.com/jira-software-cloud/docs/enable-and-disable-the-timeline/ | A | **native Timeline/Roadmap is Cloud-only**; DC uses AR | 2026-06-07 |
| https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-links/#api-rest-api-2-issuelink-post + https://support.atlassian.com/jira/kb/how-to-use-rest-api-to-add-issue-links-in-jira-issues/ | A | `POST /rest/api/2/issueLink` shape; **one link per call**; `issueLinkType` enum | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/managing-versions-938847201.html + https://www.atlassian.com/agile/tutorials/versions | A | `fixVersion` = per-project milestone (Releases page, JQL, AR timeline circles) | 2026-06-07 |
| https://help.tempo.io/gantt-dc/latest/gantt-chart-elements + https://bigpicture.one/products/biggantt/ + https://marketplace.atlassian.com/apps/1212259/bigpicture-portfolio-resource-management-for-jira | B | true Gantt + critical-path on DC via Marketplace apps only | 2026-06-07 |
| https://community.atlassian.com/forums/Jira-questions/How-to-update-the-Epic-progress-bar-with-completed-subtasks/qaq-p/2329870 | A/C | epic bar = **direct children only** (sub-tasks excluded); no native deep roll-up | 2026-06-07 |
| https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-portfolio-playbook/implement-wave-planning.html | A | server→move-group→wave; move-group rules = links; order least-risk-first; rolling-wave mandate; shared-by-all dep → one gating task | 2026-06-07 |
| https://aws.amazon.com/blogs/big-data/enterprise-scale-in-place-migration-to-apache-iceberg-implementation-guide/ + https://iceberglakehouse.com/posts/2026-04-29-iceberg-masterclass-15/ | A | per-table control plane (status/error per s3_path) = issue-per-table+status; federate→build/backfill→validate→swap; backfill in date-window waves | 2026-06-07 |
| https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview + https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html#taskgroups | A/B | per-domain pipeline decomposition (staging-by-source / marts-by-domain) | 2026-06-07 |
| https://www.hubspot.com/resources/templates/work-breakdown-structure + https://www.smartinsights.com/guides/campaign-timeline-project-plan-template-and-example/ + https://clickup.com/templates/work-breakdown-structure/event-planning | B/C | business-domain four-phase WBS; parallel streams; measure phase; operational Tasks | 2026-06-07 |
| https://hyperproof.io/resource/audit-findings-remediation-efforts/ + https://tldrsec.com/p/tldr-sec-322 + https://www.atlassian.com/blog/jira/new-security-tab-jira-software + https://www.wiz.io/academy/vulnerability-management/vulnerability-prioritization | A/B | finding→owner+deadline+verification; **triage filter (already-fine→nothing)**; severity decides 1:1-vs-grouped | 2026-06-07 |
| https://github.com/sooperset/mcp-atlassian/blob/main/src/mcp_atlassian/servers/jira.py + src/mcp_atlassian/jira/{issues,epics,links,fields}.py + utils/decorators.py | A | `jira_batch_create_issues` **can't set epic/parent inline (silent drop)**; single-create can; `READ_ONLY_MODE`/`validate_only`; no upsert → search-before-create. Re-read servers/jira.py on main (post-v0.23.0): batch schema still project_key/summary/issue_type/description/assignee/components only — claim holds | 2026-08-18 |
| https://github.com/ankitpokhrel/jira-cli/blob/main/internal/cmdcommon/create.go + pkg/jira/{create,epic,issue}.go + internal/cmd/{epic,issue/link} | A | `--parent`→Epic Link on DC; `epic add` = only batched epic-link (≤50); `issue link A B Blocks`; no bulk-create | 2026-06-07 |
| https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-bulk-post + https://community.developer.atlassian.com/t/change-on-number-of-issues-can-be-created-in-a-single-bulk-create-issues-request/54083 + https://confluence.atlassian.com/adminjiraserver/improving-instance-stability-with-rate-limiting-983794911.html | A/B | bulk 50-cap (Cloud); DC bounded by rate-limiting → chunk ~50 | 2026-06-07 |
| https://github.com/fourplusone/terraform-provider-jira + https://github.com/anubhavmishra/terraform-provider-jira | B | declarative desired-state; `terraform plan` = approve-not-author idempotency (derive every issue from the plan) | 2026-06-07 |

## Lean configuration

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://confluence.atlassian.com/enterprise/managing-number-of-custom-fields-in-jira-data-center-1488597907.html | A | **800/1,200** custom-field guardrail; 4 perf-impact areas | 2026-06-07 |
| https://support.atlassian.com/jira/kb/how-to-assess-the-impact-of-too-many-custom-fields-in-jira-and-how-to-resolve-it/ | A | Context-per-issue driver; default-value cost; 1,916-field/12–13 s case | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/optimizing-custom-fields-956713279.html | A | Global-context index cost; Instance Optimizer scan | 2026-06-07 |
| https://community.atlassian.com/forums/Jira-Cloud-Admins-articles/Designing-Jira-Fields-in-2026-When-to-Add-a-Field-vs-Use-Forms/ba-p/3202651 | B | 4-question field-vs-form test + named-owner gate (Forms = Cloud-centric) | 2026-06-07 |
| https://thejiraguy.com/2025/07/09/this-is-why-we-cant-have-nice-screens/ | B | Minimum-viable Create screen; garbage-data failure mode | 2026-06-07 |
| https://www.salto.io/blog-posts/best-practices-for-reducing-jira-customizations-and-overcoming-common-challenges | B | Deletion criteria; admin-count/sprawl correlation; UI slowdown 1000+ | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/associating-a-screen-with-an-issue-operation-938847289.html | A | Screen scheme Create/Edit/View mapping; Default entry; View-custom-fields quirk | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/specifying-field-behavior-938847255.html | A | Field Config Required/Optional, Hide/Show; required-must-be-on-create; hidden≠required | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/associating-field-behavior-with-issue-types-938847262.html | A | Field-config scheme per project×issue-type | 2026-06-07 |
| https://support.atlassian.com/jira/kb/clear-the-resolution-field-when-an-issue-is-reopened-in-jira/ | A | Native post-function clear-on-reopen; cloud+DC | 2026-06-07 |
| https://support.atlassian.com/jira/kb/best-practices-on-using-the-resolution-field-in-jira-cloud/ | A | Resolution only on transitions; REST ignores transition screens | 2026-06-07 |
| https://www.sparxsys.com/blog/how-many-issue-types-should-you-create-jira | B | Issue-type minimalism; label/component/Phase substitution | 2026-06-07 |

## Workflows, automation, reporting

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://confluence.atlassian.com/automation/understand-versions-licenses-upgrades-1141480571.html | A | **A4J free/native in DC** since JSW 9.0 (8.0+ no separate license) | 2026-06-07 |
| https://confluence.atlassian.com/automation/automation-service-limits-993924705.html | A | Exact DC automation service limits + REST property keys | 2026-06-07 |
| https://confluence.atlassian.com/automation/best-practices-for-optimizing-automation-rules-993924697.html | A | What NOT to do (scoping, condition order, no chain-firing, no batch) | 2026-06-07 |
| https://confluence.atlassian.com/automation/jira-automation-actions-993924834.html + /jira-automation-triggers-993924804.html | A | DC automation action + trigger list; no one-click parent-from-children | 2026-06-07 |
| https://www.onpointserv.com/post/jira-automation-in-2026-what-actually-works-now | B | 7 recipes + guardrails; sprawl numbers; naming convention | 2026-06-07 |
| https://community.atlassian.com/forums/App-Central-articles/Our-Jira-Automation-Rules-Are-Out-of-Control/ba-p/3213878 | B | 300+ rule sprawl; "pinged 11 times"; boring rules | 2026-06-07 |
| https://idalko.com/blog/jira-workflow-best-practices | B | Status minimalism; status-vs-resolution; governance vs drift | 2026-06-07 |
| https://community.atlassian.com/forums/App-Central-articles/10-Jira-Status-Anti-Patterns-and-the-10-Minute-Fix-for-Each/ba-p/3138593 | B | 6–9 statuses; anti-patterns + fixes; time-in-status validation | 2026-06-07 |
| https://community.atlassian.com/forums/App-Central-articles/How-to-Build-a-Single-Source-of-Truth-in-Jira/ba-p/3121337 | B | "Update the board, not a doc"; SSOT anti-patterns | 2026-06-07 |
| https://apwide.com/live-project-status-reports-dashboards-in-jira | C | Manual-report busywork; live dashboards thesis | 2026-06-07 |
| https://confluence.atlassian.com/jirasoftwareserver/configuring-a-board-938845252.html + /configuring-swimlanes-938845294.html + /configuring-quick-filters-938845301.html | A | WIP (column-level), swimlanes, quick filters config | 2026-06-07 |
| https://confluence.atlassian.com/jirasoftwareserver/using-the-simplified-workflow-938845286.html | A | DC Simplified Workflow + limitations | 2026-06-07 |
| https://www.atlassian.com/agile/kanban/wip-limits + https://www.atlassian.com/agile/project-management/kanban-metrics | A | WIP limits; flow metrics | 2026-06-07 |

## Non-software

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://confluence.atlassian.com/jiracoreserver/jira-core-overview-938846149.html + https://confluence.atlassian.com/jirasoftwareserver/jira-applications-overview-939938990.html | A | Jira Core = always-present business base on DC | 2026-06-07 |
| https://www.eficode.com/blog/jira-software-and-jira-work-management-have-merged | A/B | JWM→Jira merger is **Cloud-only**; DC separate | 2026-06-07 |
| https://atlassian.com/blog/jira-core/how-to-set-up-business-workflows-in-jira-core | A | Non-software workflow examples; conditions/validators/post-functions | 2026-06-07 |
| https://atlassian.com/blog/announcements/introducing-jira-work-management | A | 23 Cloud business templates; business vocabulary | 2026-06-07 |
| https://titanapps.io/blog/jira-kanban-scrum + https://www.atlassian.com/agile/tutorials/how-to-do-kanban-with-jira | A/B | Kanban over Scrum; WIP limits; recurring work | 2026-06-07 |
| https://marketplace.atlassian.com/apps/1218390/calendar-for-jira | A | Calendar is a DC add-on (DC 10.3–11.3 support) | 2026-06-07 |
| https://www.scrum.org/resources/blog/jira-anti-patterns-and-how-overcome-them | B | "team serving Jira" anti-pattern | 2026-06-07 |
| https://atlassian.com/agile/project-management/lean-process-improvement | A | Minimum Viable Process Change rollout | 2026-06-07 |

## Platform state (2026-08 pass)

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://atlassian.com/licensing/data-center-end-of-life | A | DC EOL: sale-end 2026-03-30, renew 2028-03-30, read-only 2029-03-28 (all three dates re-confirmed on the live page) | 2026-08-18 |
| https://endoflife.date/jira-software | A | Server EOL 2024-02-15; latest **11.3.10 (2026-08-07)**; LTS 11.3 (EOL 2027-12-03) & 10.3 (latest 10.3.24, EOL 2026-12-05) | 2026-08-18 |
| https://confluence.atlassian.com/jirasoftware/jira-software-11-3-x-release-notes-1689288832.html | A | DC 11.x leanness guardrails (JQL cap, automation-rule restriction, optimizer, 10k board); release-notes index confirms **11.3 is still the newest DC line** (no 11.4) | 2026-08-18 |
| https://atlassian.com/software/jira/ai | A | Rovo/AI is **Cloud-only**; DC via Cloud connectors | 2026-06-07 |
| https://community.developer.atlassian.com/t/work-is-the-new-collective-term-for-items-tracked-in-jira/88552 | A/B | issue→work item is **Cloud-only**; APIs keep "issue" | 2026-06-07 |
| https://www.uctoday.com/project-management/jira-projects-are-now-spaces-atlassian-says-its-clarity-users-arent-so-sure/ + https://blog.deiser.com/en/atlassian-changes-jira-project-to-jira-space | B | Project→Space rename **Cloud-only** | 2026-06-07 |
| https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-2025-survey | B | Jira most-disliked dev tool 2025 | 2026-06-07 |
| https://survey.stackoverflow.co/2025 | B | GitHub overtook Jira as most-desired | 2026-06-07 |

## Multilingual & discovery

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://developer.atlassian.com/server/jira/platform/jira-issue-statuses-as-lozenges/ | A | `statusCategory` keys/ids/colors — language-independent anchor | 2026-06-07 |
| https://docs.atlassian.com/software/jira/docs/api/REST/8.20.0/ | A | Discovery endpoints; transitions by id; createmeta/editmeta; `untranslatedName`/`clauseNames`/`cf[ID]` | 2026-06-07 |
| https://jira.atlassian.com/browse/JRACLOUD-71793 + https://jira.atlassian.com/browse/JRASERVER-74088 | A | Canonical-name fix Cloud-only; **no per-request language override on DC** | 2026-06-07 |
| https://confluence.atlassian.com/jirakb/how-to-find-id-for-custom-field-s-744522503.html | A | Discover custom-field IDs via `/field` | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/translating-resolutions-priorities-statuses-and-issue-types-938847111.html | A | Canonical-name + per-language translation model | 2026-06-07 |
| https://confluence.atlassian.com/adminjiraserver/configuring-jira-application-options-938847824.html | A | Indexing Language; mixed-language → "Other"; whole-word search | 2026-06-07 |
| https://jira.atlassian.com/browse/JRASERVER-39215 + /JRASERVER-39009 + /JRASERVER-71096 + /JRASERVER-15006 + /AUTO-72 + /JRASERVER-40049 | A | JQL canonical-vs-translated; system/custom field asymmetry; webhook/transition localization; umlaut-wildcard bug; option-values untranslatable | 2026-06-07 |
| https://lucene.apache.org/core/4_10_4/analyzers-common/org/apache/lucene/analysis/cjk/CJKTokenizer.html + https://issues.apache.org/jira/browse/LUCENE-2458 | A | CJK bigram tokenization caveats | 2026-06-07 |

## Dread / critique (use for principles, read skeptically)

| Source | Tier | Supports | Last verified |
|---|---|---|---|
| https://news.ycombinator.com/item?id=25590846 | A* | "It's your process, not Jira"; "minimal process" succeeds (*primary practitioner voices) | 2026-06-07 |
| https://medium.com/@ss-tech/jira-is-not-agile-why-your-team-should-stop-using-jira-80881befd703 | B | Surveillance/velocity-as-target; "team serving the tool" | 2026-06-07 |
| https://medium.com/@sjoerdnijland/buried-under-jira-tickets | B | Backlog bloat; "Jira is neutral"; validation gates | 2026-06-07 |
| https://www.atlassian.com/blog/development/human-side-scaling-jira-software-governance-custom-fields-admins | A | Atlassian's own "custom fields = administrative debt" admission | 2026-06-07 |
| https://www.shortcut.com/blog/9-signs-its-time-to-break-up-with-jira + https://dev.to/linearb_inc/jira-is-a-microcosm-of-what-s-broken-in-software-development-4lj3 | C | Competitor design principles to replicate inside Jira | 2026-06-07 |
| https://grandiasolutions.com/velocity-per-user-agile/ + https://www.divim.io/velocity-is-a-myth/ | B/C | Velocity-as-vanity-metric / per-user harm | 2026-06-07 |
