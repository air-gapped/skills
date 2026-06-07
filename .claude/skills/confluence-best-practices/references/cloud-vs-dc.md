# Cloud vs Data Center — versions, sunset, and the feature split

This skill is **self-hosted Data Center first, Cloud-compatible.** Get the dialect wrong and advice is unusable — most blog/marketing content describes Cloud. This file is the reference for what's true on each, as of mid-2026 (verified 2026-06-07; re-verify dated facts).

## Version & EOL state (DC)

- **Latest release: 10.2.13 (2026-06-02).** The 10.2 LTS line ships monthly patches.
- **Active LTS lines:** **10.2** (first released 2025-12-02 → EOL **2027-12-02**; **Java 21 only**, drops Java 17) and **9.2** (2024-12-09 → EOL **2026-12-10**). **8.5** LTS is already **EOL (2025-12-15)**.
- **Confluence Server is dead** — support ended **2024-02-15**; **8.5.x was the last Server-capable line; 8.6+ is Data-Center-only.** (Cite 8.5 / Feb-2024 as "last Server," not the older 7.19.)
- Policy: ~one LTS per year, ~2 years of bug+security fixes each; non-LTS feature releases get ~6 months of critical-security fixes only.

## Data Center sunset (YES — same as Jira)

Announced **2025-09-08**, covering **Confluence DC** (and Jira/JSM/Bamboo/Crowd DC):

- **2026-03-30** — end of sale to **new** customers (just passed).
- **2028-03-30** — renewal/expansion cutoff for existing customers.
- **2029-03-28** — final EOL; products become **read-only**.

Through 2029-03-28 Atlassian provides support, critical-vuln fixes, and cloud-to-DC connectors. (**Bitbucket DC is the lone exception** — not EOL'd; Confluence *is* in scope.) Note this honestly if asked, but the skill is about using *today's* DC well, not migrating.

## What is Cloud-ONLY (absent from DC)

| Feature | Notes |
|---|---|
| **Whiteboards** | Cloud-only; Atlassian has stated no DC plans |
| **Databases** | Cloud-only |
| **Smart Links / live embeds** | Cloud-only (CONFSERVER-87786 open); DC uses the Jira Issues macro + plain links |
| **Rovo / Atlassian Intelligence (ALL AI)** | Cloud-only — AI summaries, AI definitions, generate/transform content, related pages, AI translation. DC reaches it only via Rovo *connectors* that sync DC content to Cloud. |
| **Confluence automation (rule builder)** | Cloud-only (Premium/Enterprise); **not native on DC and not on the DC roadmap** |
| **Native per-page archiving** | Cloud-only; DC archives at *space* level only |
| **Page status, page emojis, schedule-publish, inline pre-publish comments** | Cloud-only |
| **Company Hub, Guests, modern anonymous/public links** | Cloud-only |
| **New navigation / Spaces sidebar redesign** | Cloud-only (GA from Mar 2025) |
| **Rich page/space analytics** (views, read-time) | Cloud-richer; DC has bundled "Analytics for Confluence" but it's *limited* and not actively developed |

## Available on BOTH (don't mis-flag as Cloud-only)

- **Team Calendars** — bundled into Confluence DC since **2021-02-01 (7.11+)**, no separate license. Also in Cloud.
- **Analytics for Confluence** — bundled in DC (limited); Cloud has its own richer version.
- **Collaborative/real-time editing** — DC supports up to **12 simultaneous editors** per page; Cloud "live editing" is a richer variant.
- **Templates** — both (Cloud ships a much larger gallery; DC = build your own).
- **DC-only (not in Cloud):** nested macros, custom table widths, right-to-left language support, the Atlassian Companion app.

## The editor & content format (the biggest trap)

- **DC does NOT have Cloud's Fabric/"new" editor — it never shipped to DC.** DC uses its **own TinyMCE-based editor** (TinyMCE 7.9.1 in 10.2): collaborative editing (≤12), drag-and-drop, autocomplete.
- **Terminology trap — "legacy editor" means two different things.** On **Cloud** it's the *old Cloud* editor being deprecated in a phased Jan–Apr 2026 rollout (full deprecation 2026-04-01) — **a Cloud-only concern that does NOT touch DC.** On **DC** there is just "the editor." Never advise a DC user about "legacy editor deprecation."
- **Content model:** DC stores **Confluence storage format** (XHTML-based XML with `ac:`/`ri:` macro elements). **ADF is a Jira-Cloud content model — it does NOT apply to Confluence.** Even on Confluence Cloud, the REST-portable write target is **storage format**. So: for Confluence, write **storage**, never ADF, never raw markdown (markdown is an editor-paste convenience only).
- **Wiki markup** is deprecated as a *storage/input* language (auto-migrated to XHTML since 4.0) but survives as `{macro}` brace notation; unmigratable content is wrapped in an `unmigrated-wiki-markup` macro.
- **Editing raw storage on DC:** the bundled **Storage Format Source Editor** exists since **10.2.3 but is disabled by default** (enable via Admin → Source Editor Configuration); page **… → View Storage Format** shows the XHTML read-only. ("View source" shows editor format, not storage — don't confuse them.)

## Vocabulary to flag (so advice doesn't mislead)

- **Editor:** Cloud = Fabric/ADF; DC = TinyMCE + storage format.
- **"Legacy editor":** Cloud = the deprecating old editor; DC = N/A.
- **"Site" (Cloud, `org.atlassian.net`) vs "instance/installation" (DC, self-hosted).**
- **Automation:** Cloud-native rule builder; DC has none (Jira automation / apps / agent instead).
- **REST:** Cloud v1+v2; DC v1 only.
- **User id:** Cloud `accountId`; DC `username`/`userKey`.

## Sources
See `references/sources.md`. Key anchors (Tier A): endoflife.date/confluence; atlassian.com/licensing/data-center-end-of-life; Confluence 10.2 release notes; Cloud-vs-DC migration compare + differences docs; "Confluence Storage Format", "The Editor", wiki-markup migration docs; Team Calendars / Analytics bundling KBs; CONFSERVER-87786.
