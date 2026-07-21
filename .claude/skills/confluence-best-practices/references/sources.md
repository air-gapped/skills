# Sources

External claims in this skill, with source, tier, and what they support. **Last verified: 2026-06-07** (research date); volatile rows re-probed **2026-07-21** — see the freshen note at the end. Re-verify before relying on dated facts (DC versions, EOL dates, Cloud-vs-DC feature splits, open-bug status) — these move.

Tiers: **A** = official Atlassian docs / issue tracker (jira.atlassian.com) / primary spec & peer-reviewed · **B** = experienced practitioners / solution partners / surveys · **C** = vendor-advocacy / competitor marketing / community opinion (down-weighted, used for *principles* not facts).

Full research provenance: `autoresearch/results/confluence-best-practices-research-2026-06-07.md` (10 agents, STORM multi-perspective, depth 2, ~90 sources).

## Information architecture

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/doc/spaces-139459.html | A | Space = container ("different folders"); global vs personal; blueprints; Space Directory | 2026-06-07 |
| confluence.atlassian.com/enterprise/confluence-spaces-with-too-many-nesting-levels-1489809653.html | A | Official health check: deep page trees degrade *performance*; remediation moves | 2026-06-07 |
| confluence.atlassian.com/doc/use-labels-to-categorize-spaces-136647.html | A | Space categories = labels on spaces; Space Directory grouping | 2026-06-07 |
| confluence.atlassian.com/doc/undefined-page-links-139580.html; orphaned-pages KB | A | Undefined/wanted + orphaned pages (space-level; no site-wide UI) | 2026-06-07 |
| community.atlassian.com/.../Spaces-vs-Pages-best-practices (1008538); .../space-types (413510) | B | Space-vs-page tie-breaker = restrictions vs space; space types are starter templates | 2026-06-07 |
| k15t.com/rock-the-docs/.../structure-for-long-term-success | B | Consistency-by-type; flat-vs-nested by role; labels-on-templates | 2026-06-07 |
| covectors.io/blog/10-tips-...-page-tree; .../a-practical-guide-to-confluence-labels | B | Depth cap 3–4; tree=containment vs labels=cross-cutting; single-parent | 2026-06-07 |
| support.atlassian.com/confluence-cloud/docs/use-folders-...; k15t folders article | A/B | Folders (Cloud GA late-2024; DC version-gated) — verify before recommending | 2026-06-07 |

## Lean content & lifecycle

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/clean/clean-up-your-confluence-instance-1026047969.html | A | Cleanup levers: space-archive (excluded from search, index unchanged), retention 7.16+, trash purge, view-count sort, macro-usage report | 2026-06-07 |
| confluence.atlassian.com/doc/archive-a-space-284368719.html; .../Delete+and+archive+spaces | A | Space archive vs delete; archive excludes from search but stays indexed; can't move into archived space | 2026-06-07 |
| jira.atlassian.com/browse/CONFSERVER-31010 | A | **No native page-level archiving** on DC — re-probed 2026-07-21: still **Gathering Interest**, unresolved, 100 votes, and the ticket was **updated 2026-07-21** (still live discussion, 13 years on). Claim holds | 2026-07-21 |
| confluence.atlassian.com/enterprise/managing-the-number-of-spaces-in-confluence-data-center-1607598774.html | A | **<8,000 / 8–10k / >10k spaces** guardrail; cause = permission checks | 2026-06-07 |
| confluence.atlassian.com/doc/server-hardware-requirements-guide-30736403.html | A | Pages not a perf axis (80k <512MB); 2 GB attachment max; no documented pages/space cap | 2026-06-07 |
| confluence.atlassian.com/doc/troubleshooting-collaborative-editing-858772087.html | A | 12-concurrent-editor cap (documented product limit — still stands) | 2026-06-07 |
| jira CONFSERVER-60057 / CONFSERVER-59747 | A | **Both now Closed/Fixed** (60057 resolved 2023-11-14, 59747 resolved 2024-10-08) — re-probed 2026-07-21 via the public jira.atlassian.com REST API. They no longer evidence a live "large pages break Synchrony" constraint; `lean-content-and-lifecycle.md` reframed to authoring guidance | 2026-07-21 |
| confluence.atlassian.com/doc/set-retention-rules-...-1108681072.html | A | Retention (versions/revisions/trash), global+exemption, latest-never-deleted (7.16+) | 2026-06-07 |
| confluence.atlassian.com/doc/back-up-a-space-...-1236929929.html | A | XML space export, 72h TTL | 2026-06-07 |
| confluence.atlassian.com/doc/page-properties-report-macro-186089616.html; page-properties-macro-184550024.html | A | Owner/Review-Date dashboard; label-key; 3000-page/60-label caps; AND/OR/NOT | 2026-06-07 |
| confluence.atlassian.com/doc/excerpt-include-macro-148067.html | A | SSOT transclusion (first-excerpt limit; cross-space `SPACEKEY:Page`) | 2026-06-07 |
| confluence.atlassian.com/doc/blueprints-323982376.html; page-templates-296093785.html | A | Templates vs blueprints; promote-template; default labels | 2026-06-07 |

## Findability & search

| Source | Tier | Supports | Verified |
|---|---|---|---|
| developer.atlassian.com/server/confluence/cql-field-reference; advanced-searching-using-cql | A | CQL fields/operators/functions (label, title, space, type, ancestor/parent, lastModified, creator, currentUser()) | 2026-06-07 |
| confluence.atlassian.com/doc/confluence-search-syntax-158720.html | A | Whole-word/stemming; stop-words in quotes; special-chars stripped (`DOC-8510`); no leading wildcard | 2026-06-07 |
| confluence.atlassian.com/doc/configuring-search-175210673.html; configuring-indexing-language-150130.html | A | Exact-search dark feature; CJK exact-off; Indexing Language list; reindex-on-change | 2026-06-07 |
| confluence.atlassian.com/enterprise/opensearch-for-confluence-data-center-1653834676.html | A | OpenSearch DC-only, since 9.0, ~4.5× faster, "same experience" (perf-not-relevance) | 2026-06-07 |
| jira.atlassian.com/browse/CONFSERVER-17138 / -22495 / -5142 | A | Umlaut+wildcard broken (open); accent folding shipped 6.10.0; wildcards don't stem | 2026-06-07 |
| confluence.atlassian.com/confkb/...a-page-with-this-name-already-exists...; CONFSERVER-2524/5926 | A | Unique-title-per-space; restricted/draft collision; won't-fix | 2026-06-07 |
| community.atlassian.com/.../search complaints; news.ycombinator.com 36926680 | B/C | "Can't find anything" = content-not-engine | 2026-06-07 |

## Authoring & readability

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/doc/table-of-contents-macro-182682099.html | A | TOC builds from heading levels; long-page use | 2026-06-07 |
| diataxis.fr (+ /start-here/) | A | Four doc types; "blurring boundaries… vast number of problems"; writer+reader benefit | 2026-06-07 |
| confluence.atlassian.com/doc/info-tip-note-and-warning-macros...; excerpt/expand macro docs | A | Panels, Expand, Excerpt — readability macros + storage format | 2026-06-07 |
| jira.atlassian.com/browse/CONFCLOUD-67594 (+ -69740) | A | New-editor table copy/paste regressions; editor latency on heavy pages | 2026-06-07 |
| WCAG 2.x; siteimprove + university Confluence accessibility KBs | A/B | Alt text, descriptive links, no skipped headings, 4.5:1/3:1 contrast, no colour-only | 2026-06-07 |
| k15t.com/rock-the-docs/...make-beautiful-pages; refined.com; covectors.io headings | B | BLUF, chunking, 60-char lines, title=H1, "less is more", one-page-one-purpose, vague-title warning | 2026-06-07 |
| thoughtworks / RAG practitioner posts | B | Confluence rarely AI-ready; retrieval needs text not screenshots | 2026-06-07 |
| NN/g "How users read on the web" (behind the 79%/74% scan stats) | A | Scanning behaviour grounding (cite original, not blog restatements) | 2026-06-07 |

## Permissions, governance, Jira boundary

| Source | Tier | Supports | Verified |
|---|---|---|---|
| confluence.atlassian.com/doc/page-restrictions-139414.html; permissions-and-restrictions-139557.html | A | View-cascades/edit-doesn't; restriction-narrows-never-grants; admin override; self-restriction; blog-conversion strip | 2026-06-07 |
| confluence.atlassian.com/doc/global-permissions-overview-138709.html; permissions-best-practices-992678945.html | A | Five global perms; Create-Space(s) lever; confluence-administrators; groups>individuals; open-by-default | 2026-06-07 |
| support.atlassian.com/confluence/kb/understanding-permission-in-confluence | A | Evaluation order; additive accumulation; cluster cache note | 2026-06-07 |
| jira.atlassian.com/browse/CONFSERVER-5095 / -25189 / -87720 | A | Edit-restrictions not inherited; CONFANCESTORS/template inheritance desync | 2026-06-07 |
| confluence.atlassian.com/doc/jira-issues-macro-139380.html; use-jira-applications-and-confluence-together-427623543.html | A | Jira Issues macro (3 modes, permission-aware); app-link prereq; create-issue-from-page | 2026-06-07 |
| jira.atlassian.com/browse/CONFSERVER-87786 | A | **Smart Links Cloud-only** (DC request open) | 2026-06-07 |

## Agent execution & discovery

| Source | Tier | Supports | Verified |
|---|---|---|---|
| developer.atlassian.com/server/confluence (REST overview, examples, content-descendant, restrictions) | A | DC REST v1 `/content`, `body.storage`, PAT (7.9+), version-increment, `/scan` | 2026-06-07 |
| developer.atlassian.com/cloud/confluence/rest/v2/api-group-page | A | Cloud v2 `/pages`, `body-format=storage`, cursor pagination | 2026-06-07 |
| confluence.atlassian.com/doc/confluence-storage-format-790796544.html; confluence-wiki-markup-251003035.html | A | Storage format XML (ac:/ri:, CDATA); markdown is editor-input-only; wiki deprecated-as-storage | 2026-06-07 |
| developer.atlassian.com/cloud/confluence/deprecation-notice-user-privacy-api-migration-guide | A | `accountId` replaces username/userKey on Cloud | 2026-06-07 |
| developer.atlassian.com/cloud/confluence/rest/v1/api-group-space-permissions | A | Space-perms need space-admin; apps blocked from resource on Cloud | 2026-06-07 |
| community.developer.atlassian.com (v1-deprecation-timeline; async-convert; 409/OptimisticLock; v2 space-labels) | A* | v1 still operational (parity-gated); async convert dropped wiki→storage; 409 mechanics; v2 has no space-categories | 2026-06-07 |
| community.atlassian.com CQL `lastmodified` reliability thread | B | Prefer documented camelCase `lastModified`; verify on instance | 2026-06-07 |

## Cloud-vs-DC / June-2026 state

| Source | Tier | Supports | Verified |
|---|---|---|---|
| endoflife.date/confluence | A | Latest 10.2.13 (2 Jun 2026); LTS 10.2→Dec 2027 / 9.2→Dec 2026; 8.5 EOL; Server EOL Feb 2024; 8.6+ DC-only | 2026-06-07 |
| atlassian.com/licensing/data-center-end-of-life | A | DC sunset (announced 8 Sep 2025): sale-stop 30 Mar 2026, renewal 30 Mar 2028, read-only 28 Mar 2029; Bitbucket exception | 2026-06-07 |
| confluence.atlassian.com/doc/confluence-10-2-release-notes-1652924013.html | A | 10.2 LTS, Java 21, TinyMCE 7.9.1 editor, Storage Format Source Editor in 10.2.3 | 2026-06-07 |
| atlassian.com/migration/assess/compare-cloud-data-center/confluence; support.atlassian.com/migration/docs/differences-... | A | Cloud-only list (Whiteboards, Databases, Rovo/AI, automation, page-archive, guests, smart links); DC-only (nested macros, RTL) | 2026-06-07 |
| confluence.atlassian.com/doc/the-editor-251006017.html; migration-from-wiki-markup-...-255363895.html | A | DC TinyMCE editor; wiki-markup deprecated-as-storage; unmigrated-wiki-markup macro | 2026-06-07 |
| support.atlassian.com/organization-administration/docs/connect-confluence-data-center-to-rovo | A | Rovo AI Cloud-only; DC via connectors | 2026-06-07 |
| Team Calendars / Analytics-for-Confluence bundling KBs | A | Bundled on DC (Team Calendars since 1 Feb 2021 / 7.11+) | 2026-06-07 |

## Dread / critique (use for principles, read skeptically)

| Source | Tier | Supports | Verified |
|---|---|---|---|
| dev.to/niklasbegley/confluence-is-where-documentation-goes-to-die; dev.to/pabloportugues | B | "Goes to die"; staleness→trust; "the tool is not the problem… we use it wrong" | 2026-06-07 |
| news.ycombinator.com 39375258; austinkucera.com | B | Sharpest search/duplication complaints; the genuine tool-limit side (proprietary storage, no VCS) | 2026-06-07 |
| newsletter.pragmaticengineer.com/.../2025-survey; atlassian.com/blog/developer/developer-experience-report-2025 | B/C | Jira most-disliked (Confluence rides along); "finding information" = #1 time-waster (vendor self-report) | 2026-06-07 |
| ResearchGate "Design principles of wiki" (Cunningham); PMC8896816 + link-rot studies | A | Gardening/organic principles ("easier for authors, harder for readers"); reference half-lives 1.6–15 yrs | 2026-06-07 |
| Notion/Slite/GitBook/Coda comparisons; midori-global; gocapable; technicalwriterhq | C | Competitor design principles (templates-by-default, "what happens after content is created"); review-cadence playbooks | 2026-06-07 |


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
