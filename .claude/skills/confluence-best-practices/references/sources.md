# Sources

Freshened: 2026-10-20

External claims in this skill, with source, tier, and what they support. Dated facts (DC versions, EOL dates, Cloud-vs-DC feature splits, open-bug status) move — re-verify them before relying on them.

Tiers: **A** = official Atlassian docs / issue tracker (jira.atlassian.com) / primary spec & peer-reviewed · **B** = experienced practitioners / solution partners / surveys · **C** = vendor-advocacy / competitor marketing / community opinion (down-weighted, used for *principles* not facts).

Full research provenance: `autoresearch/results/confluence-best-practices-research-2026-06-07.md` (10 agents, STORM multi-perspective, depth 2, ~90 sources).

## Information architecture

| Source | Tier | Supports |
|---|---|---|
| confluence.atlassian.com/doc/spaces-139459.html | A | Space = container ("different folders"); global vs personal; blueprints; Space Directory |
| confluence.atlassian.com/enterprise/confluence-spaces-with-too-many-nesting-levels-1489809653.html | A | Official health check: deep page trees degrade *performance*; remediation moves |
| confluence.atlassian.com/doc/use-labels-to-categorize-spaces-136647.html | A | Space categories = labels on spaces; Space Directory grouping |
| confluence.atlassian.com/doc/undefined-page-links-139580.html; confluence.atlassian.com/conf59/orphaned-pages-792498978.html | A | Undefined/wanted + orphaned pages (space-level, Space tools > Content Tools; orphan = no incoming links; no site-wide UI) |
| community.atlassian.com/forums/discussion/1008538; community.atlassian.com/forums/discussion/413510 | B | 413510: space types "more as templates… once created, they don't really have much effect". 1008538 does NOT state the restrictions-over-space tie-breaker (its answer favours a space per client); that rule rests on the page-restrictions doc mechanics (restrictions narrow per page; space permissions are space-wide) |
| k15t.com/rock-the-docs/.../structure-for-long-term-success | B | Consistency-by-type; flat-vs-nested by role; labels-on-templates |
| covectors.io/blog/10-tips-...-page-tree; .../a-practical-guide-to-confluence-labels | B | Depth cap 3–4; tree=containment vs labels=cross-cutting; single-parent |
| support.atlassian.com/confluence-cloud/docs/use-folders-to-organize-your-work/; k15t.com/rock-the-docs/news/2024/11/48-why-folders-in-confluence-are-a-big-deal | A/B | Folders are Cloud-only: the 'container with a Read Me' wording is Atlassian's Cloud doc, not k15t's. Absence on DC checked 2026-10-20: DC 10.0/10.1/10.2/11.0 release notes have no content-folder feature, the DOC-space search finds no folders page, and the DC-vs-Cloud differences page names folders only as Cloud content |

## Lean content & lifecycle

| Source | Tier | Supports |
|---|---|---|
| confluence.atlassian.com/clean/clean-up-your-confluence-instance-1026047969.html | A | Cleanup levers: space-archive (excluded from search, index unchanged), retention 7.16+, trash purge, view-count sort, macro-usage report |
| confluence.atlassian.com/doc/archive-a-space-284368719.html; .../Delete+and+archive+spaces | A | Space archive vs delete; archive excludes from search but stays indexed; can't move into archived space |
| jira.atlassian.com/browse/CONFSERVER-31010 | A | **No native page-level archiving** on DC — re-probed 2026-07-21: still **Gathering Interest**, unresolved, 100 votes, and the ticket was **updated 2026-07-21** (still live discussion, 13 years on). Claim holds |
| confluence.atlassian.com/enterprise/managing-the-number-of-spaces-in-confluence-data-center-1607598774.html | A | **<8,000 / 8–10k / >10k spaces** guardrail; cause = permission checks |
| confluence.atlassian.com/doc/server-hardware-requirements-guide-30736403.html | A | Pages not a perf axis (80k <512MB); no documented pages/space cap. The page states no attachment maximum (re-read 2026-10-20) |
| confluence.atlassian.com/doc/configuring-attachment-size-150040.html | A | Attachment Maximum Size default **100 MB**; text extraction caps 1 MB xlsx/pptx, 8 MB PDF, 16 MB docx, 100 MB text/XML (`atlassian.indexing.attachment.maxsize`) |
| confluence.atlassian.com/doc/troubleshooting-collaborative-editing-858772087.html | A | 12-concurrent-editor cap (documented product limit — still stands) |
| jira CONFSERVER-60057 / CONFSERVER-59747 | A | **Both Closed/Fixed** — 60057 resolved **2022-06-22**, fixVersions 7.13.11/7.18.2/7.19.2; 59747 resolved **2024-10-03**, fixVersion 9.1.0 (re-read 2026-10-20 via the public REST API; the 2026-07-21 log below recorded the tickets' last-*updated* dates, not resolution dates). They no longer evidence a live "large pages break Synchrony" constraint; `lean-content-and-lifecycle.md` reframed to authoring guidance |
| confluence.atlassian.com/doc/set-retention-rules-...-1108681072.html | A | Retention (versions/revisions/trash), global+exemption, latest-never-deleted (7.16+) |
| confluence.atlassian.com/doc/back-up-a-space-...-1236929929.html | A | XML space export, 72h TTL |
| confluence.atlassian.com/doc/page-properties-report-macro-186089616.html; page-properties-macro-184550024.html | A | Owner/Review-Date dashboard; label-key; 3000-page/60-label caps; AND/OR/NOT |
| confluence.atlassian.com/doc/excerpt-include-macro-148067.html | A | SSOT transclusion (first-excerpt limit; cross-space `SPACEKEY:Page`) |
| confluence.atlassian.com/doc/blueprints-323982376.html; page-templates-296093785.html | A | Templates vs blueprints; promote-template; default labels |

## Findability & search

| Source | Tier | Supports |
|---|---|---|
| developer.atlassian.com/server/confluence/cql-field-reference; advanced-searching-using-cql | A | CQL fields/operators/functions (label, title, space, type, ancestor/parent, `lastmodified` — documented lowercase in both the DC and Cloud field references, re-read 2026-10-20 — creator, currentUser(); date formats `yyyy/MM/dd HH:mm` and `yyyy-MM-dd HH:mm`) |
| confluence.atlassian.com/doc/confluence-search-syntax-158720.html | A | Whole-word/stemming; stop-words in quotes; special-chars stripped (`DOC-8510`); no leading wildcard |
| confluence.atlassian.com/doc/configuring-search-175210673.html; configuring-indexing-language-150130.html | A | Exact-search dark feature; CJK exact-off; Indexing Language list; reindex-on-change |
| confluence.atlassian.com/enterprise/opensearch-for-confluence-data-center-1653834676.html | A | OpenSearch DC-only, since 9.0, ~4.5× faster, "same experience" (perf-not-relevance) |
| jira.atlassian.com/browse/CONFSERVER-17138 / -22495 / -5142 | A | Umlaut+wildcard broken (open); accent folding shipped 6.10.0; wildcards don't stem |
| support.atlassian.com/confluence/kb/the-error-a-page-with-this-name-already-exists-in-this-space-displays-when-renaming-a-page-title/ (old confkb URL 301s here); CONFSERVER-2524 (Won't Fix) / -5926 (Duplicate) | A | Unique title per space; restricted pages the user can't see still block the title. The KB does not mention drafts — that claim was dropped |
| news.ycombinator.com/item?id=36926680 (comment: "Confluence search isn't that bad. What is bad is the data that is fed into it"); community.atlassian.com search threads (e.g. qaq-p/1422876 — index/wildcard/permission causes) | B/C | "Can't find anything" = content-not-engine |

## Authoring & readability

| Source | Tier | Supports |
|---|---|---|
| confluence.atlassian.com/doc/table-of-contents-macro-182682099.html | A | TOC builds from heading levels; long-page use |
| diataxis.fr (+ /start-here/) | A | Four doc types; "blurring boundaries… vast number of problems"; writer+reader benefit |
| confluence.atlassian.com/doc/info-tip-note-and-warning-macros...; excerpt/expand macro docs | A | Panels, Expand, Excerpt — readability macros + storage format |
| jira.atlassian.com/browse/CONFCLOUD-67594 (+ -69740) | A | New-editor table copy/paste regressions; editor latency on heavy pages. **Both closed** — 67594 Won't Do 2025-10-28 (behaviour stands, won't be changed), 69740 Fixed 2026-02-13. Cite as documented behaviour, not as live bugs |
| w3.org/WAI/WCAG22/Understanding/contrast-minimum.html; help.siteimprove.com accessibility (images, headings, links) | A/B | 4.5:1 normal / 3:1 large text (WCAG SC 1.4.3, re-read 2026-10-20); alt text, descriptive links, heading order. Siteimprove is generic web guidance, not Confluence-specific; no Confluence-specific university KB located |
| k15t.com/rock-the-docs/misc/how-to-make-beautiful-pages-in-confluence (has "less is more"; does not contain "walls of text are your worst enemy" — quote dropped); refined.com/blog/ultimate-guide-creating-confluence-wiki (one idea per page, clear titles; no BLUF wording); covectors.io/blog/confluence-headings-best-practices (calls H1 vs page title confusing; does not prescribe title=H1) | B | Chunking, "less is more", one-page-one-purpose, clear titles. BLUF and title=H1/body-from-H2 are this skill's synthesis, not stated by these sources |
| thoughtworks.com/insights/blog/generative-ai/how-to-build-an-AI-ready-knowledge-base (2025-11-06) | B | Confluence rarely AI-ready; retrieval needs text not screenshots |
| nngroup.com/articles/how-users-read-on-the-web/ | A | 79% of test users scanned; 16% read word-by-word (re-read 2026-10-20) |

## Permissions, governance, Jira boundary

| Source | Tier | Supports |
|---|---|---|
| confluence.atlassian.com/doc/page-restrictions-139414.html; permissions-and-restrictions-139557.html | A | View-cascades/edit-doesn't; restriction-narrows-never-grants; admin override; self-restriction; blog-conversion strip |
| confluence.atlassian.com/doc/global-permissions-overview-138709.html; permissions-best-practices-992678945.html | A | Five global perms; Create-Space(s) lever; confluence-administrators; groups>individuals; open-by-default |
| support.atlassian.com/confluence/kb/understanding-permission-in-confluence | A | Evaluation order; additive accumulation; cluster cache note |
| jira.atlassian.com/browse/CONFSERVER-5095 / -25189 / -87720 | A | 5095 Closed **Won't Do** 2020-06-29 (edit restrictions not inherited, by design). 25189 Closed **Fixed 6.5.0**; 87720 Closed **Fixed 8.5.0 / 7.19.11 / 7.13.19** — the CONFANCESTORS desync causes are fixed on current LTS (REST re-read 2026-10-20) |
| confluence.atlassian.com/doc/jira-issues-macro-139380.html; use-jira-applications-and-confluence-together-427623543.html | A | Jira Issues macro (3 modes, permission-aware); app-link prereq; create-issue-from-page |
| jira.atlassian.com/browse/CONFSERVER-87786 | A | **Smart Links Cloud-only** (DC request open) |

## Agent execution & discovery

| Source | Tier | Supports |
|---|---|---|
| developer.atlassian.com/server/confluence (REST overview, examples, content-descendant, restrictions) | A | DC REST v1 `/content`, `body.storage`, PAT (7.9+), version-increment, `/scan` |
| developer.atlassian.com/cloud/confluence/rest/v2/api-group-page | A | Cloud v2 `/pages`, `body-format=storage`, cursor pagination |
| confluence.atlassian.com/doc/confluence-storage-format-790796544.html; confluence-wiki-markup-251003035.html | A | Storage format XML (ac:/ri:, CDATA); markdown is editor-input-only; wiki deprecated-as-storage |
| developer.atlassian.com/cloud/confluence/deprecation-notice-user-privacy-api-migration-guide | A | `accountId` replaces username/userKey on Cloud |
| developer.atlassian.com/cloud/confluence/rest/v1/api-group-space-permissions | A | Space-perms need space-admin; apps blocked from resource on Cloud |
| community.developer.atlassian.com/t/update-to-confluence-v1-api-deprecation-timeline/79687; developer.atlassian.com/cloud/confluence/changelog; Cloud v1 content-body API; Cloud v2 OpenAPI (dac-static.atlassian.com/cloud/confluence/openapi-v2.v3.json) | A* | v1 still operational, no announced removal date (changelog read 2026-10-20; Oct 2026 entries move content restrictions to new v2 permissions endpoints, no date). Async convert covers storage/editor/atlas_doc_format only — no wiki→storage. v2 has read-only `GET /spaces/{id}/labels` (`prefix=team` = space categories per the v1 spec); no v2 write. 409 on a stale `version.number` is practitioner-reported (thread 68821), not in an official doc |
| community.atlassian.com/forums/discussion/1430592 (CQL `lastmodified` thread) | B | One 2020 report of `lastmodified` returning out-of-window pages, suspected timezone; Atlassian could not reproduce. Supports "verify on the instance" only — it does not show camelCase is safer, and the field reference documents lowercase |

## Cloud-vs-DC / June-2026 state

| Source | Tier | Supports |
|---|---|---|
| endoflife.date/confluence (+ `/api/confluence.json`) | A | 2026-10-20: **11.0.0 released 2026-10-08, `lts: false`**; 10.2 LTS latest **10.2.19 (2026-10-05)** →2027-12-02; 9.2 LTS latest **9.2.26** →2026-12-10 (51 days from 2026-10-20); 8.5 EOL; Server EOL Feb 2024; 8.6+ DC-only |
| confluence.atlassian.com/doc/confluence-11-0-release-notes-1875247238.html | A | 11.0 (8 Oct 2026): Java 25 minimum; upgrade only from latest 10.2.x (10.2.13+); rate limiting on by default, per-endpoint REST limits answer **429 + `Retry-After`** |
| atlassian.com/trust/security/bug-fix-policy | A | Critical security fixes: latest feature release, all supported LTS, and feature versions released within 6 months of the fix |
| atlassian.com/licensing/data-center-end-of-life | A | DC sunset (announced 8 Sep 2025): sale-stop 30 Mar 2026, renewal 30 Mar 2028, read-only 28 Mar 2029; Bitbucket exception |
| confluence.atlassian.com/doc/confluence-10-2-release-notes-1652924013.html | A | 10.2 LTS, Java 21, TinyMCE 7.9.1 editor, Storage Format Source Editor in 10.2.3 |
| atlassian.com/migration/assess/compare-cloud-data-center/confluence; support.atlassian.com/migration/docs/differences-using-confluence-data-center-and-cloud/; atlassian.com/software/confluence/whiteboards + /automation FAQs | A | Cloud-only list (Whiteboards and Automation: FAQ says "no plans" for DC; Databases, Rovo/AI, page-archive, guests, smart links); page analytics on DC = "Limited functionality" (compare page; the bundled-app page says nothing about development status); Not-in-Cloud: RTL, Companion editing, attachments from other pages, copy-without-attachments; nested body macros and custom table widths are 'works differently in Cloud', not DC-only (differences page re-read 2026-10-20). Compare page lists 'Bulk archive pages' as Premium/Enterprise |
| confluence.atlassian.com/doc/the-editor-251006017.html; migration-from-wiki-markup-...-255363895.html | A | DC TinyMCE editor; wiki-markup deprecated-as-storage; unmigrated-wiki-markup macro |
| support.atlassian.com/organization-administration/docs/connect-confluence-data-center-to-**teamwork-graph** | A | Rovo AI Cloud-only; DC via connectors. **Atlassian renamed this connector doc from "Rovo" to "Teamwork Graph"** — the old URL 301s to the new one. The mechanism is unchanged; the branding in prose may not be. |
| support.atlassian.com/confluence/kb/how-to-get-team-calendars-bundled-with-an-existing-data-center-instance/ | A | Team Calendars "bundled with Confluence Data Center since February 1, 2021"; integrated from 7.11 |

## Dread / critique (use for principles, read skeptically)

| Source | Tier | Supports |
|---|---|---|
| dev.to/niklasbegley/confluence-is-where-documentation-goes-to-die-3ank (old slug 404s); dev.to/pabloportugues/confluence-is-where-information-goes-to-die-25n | B | "Goes to die"; staleness→trust; "the tool is not the problem… we use it wrong" |
| news.ycombinator.com/item?id=39375258; austinkucera.com/blog/Why-I-Hate-Jira-and-Confluence.html | B | Sharpest search/duplication complaints; the genuine tool-limit side (proprietary storage, no VCS) |
| newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-2025-survey-part-2; atlassian.com/blog/developer/developer-experience-report-2025 | B/C | Jira most-disliked (Confluence third); "finding information (services, docs, APIs)" first-listed time-waster (vendor self-report) |
| researchgate.net/publication/221367717 (Cunningham, WikiSym 2006); pmc.ncbi.nlm.nih.gov/articles/PMC8896816 | A | Cunningham: wiki design principles (abstract only; the "organic" framing is secondary-source). PMC8896816: cited references 27% unavailable at 3 years, 45–78% at 5. It gives no "half-life 1.6–15 yrs" figure — dropped |
| midori-global.com/blog/2023/01/18/confluence-content-lifecycle-management; gocapable.com/blog/how-to-build-a-knowledge-centered-confluence; technicalwriterhq.com; slite.com/learn/confluence-vs-notion | C | Review-cadence and lifecycle principles (expiry, owner reminders, quarterly review). The competitor-comparison phrases ("templates by default", "what happens after content is created") were not found on any located page — principle only, no quote |


## 2026-07-21 freshen

Re-probed the rows the header flags as volatile (open-bug status, DC versions/EOL).

**Bug-status re-probe via the public `jira.atlassian.com` REST API** — this is
the class the header warns about, and two of three had moved:

| Issue | Was cited as | State 2026-07-21 |
|---|---|---|
| CONFSERVER-31010 | No native page-level archiving on DC (Gathering Interest since 2013) | **Unchanged** — still `Gathering Interest`, unresolved, 100 votes, and *updated 2026-07-21*. Claim holds. |
| CONFSERVER-60057 | Large pages break Synchrony / ~30s timeout | **Closed / Fixed 2023-11-14** |
| CONFSERVER-59747 | Large-table publish slowness | **Closed / Fixed 2024-10-08** |

The last two were cited as evidence for a live constraint. Both were already
fixed *before* the 2026-06-07 research pass — the research picked up the
symptom description without checking resolution. `lean-content-and-lifecycle.md`
now keeps the split-large-pages advice as **authoring guidance** (readability,
review effort, reuse) and the 12-editor cap as the one documented product
limit, while explicitly noting that a Synchrony timeout on a current version is
a *new* bug rather than these. Handing someone a years-closed known-issue link
is worse than saying "unknown".

**DC version / EOL:**

- LTS lines and sunset dates re-checked and **unchanged**: 10.2 → 2027-12-02
  (Java 21 only), 9.2 → 2026-12-10, 8.5 already EOL, Server EOL 2024-02-15,
  sunset 2026-03-30 / 2028-03-30 / 2029-03-28.
- Added the consequence: **9.2 has under five months of support left**, and the
  10.2 hop carries a **Java 17 → 21** requirement with it.
- **Latest patch not resolved.** The skill recorded 10.2.13 (2026-06-02);
  Atlassian's docs indicate a further 10.2.x around 2026-07-09, but
  `confluence-release-summary` enumerates only minor lines and the exact patch
  did not surface. Marked "re-derive from the instance or the 10.2 release-notes
  page" in both `SKILL.md` and `cloud-vs-dc.md` rather than substituting a
  guess.

**Not re-probed this pass:** the Atlassian doc-page URLs (IA, findability,
permissions, authoring sections) and the tier-B/C practitioner sources. They
support durable *principles* rather than dated facts, which is what the header's
re-verify instruction targets.
