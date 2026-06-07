# Improvement backlog — jira-confluence-mcp

Carries findings across skill-improver runs. Read in Phase 0 (improve) / T0 (trigger) / F0 (freshen); update on completion.

## Open

_None._ All three passes (trigger, improve, freshen) ran on 2026-06-07 with **zero mutations required** — the skill was authored with prior skill-improver lessons (split frontmatter under caps, per-row source dates, imperative voice, pointer-shaped body) already applied.

**Deliberate design decisions (do NOT re-propose — intentional, not work-not-done):**
- **TLS/CA guidance appears in three places** (SKILL.md TLS section, `air-gapped.md` in-container CA, `troubleshooting.md` SSL row). This is intentional per-entry-point layering, and the add-CA-vs-`JIRA_SSL_VERIFY=false` both-ways content is a **user-stated requirement** ("info on how to either add ca certs or verify false"). Consolidating it would break the air-gap recipe's self-containment and drop user-requested prominence. The baseline blind scorer rated Dim 6 a 9 ("defensible, different entry points"). Leave as-is.
- **`references/trigger-evals.json` is unreferenced from SKILL.md** — by design; it's the skill-improver trigger-mode artifact (the probe reads `<skill>/references/trigger-evals.json`), not user-facing reference content. Same convention as `jira-cli` and `jira-best-practices`.

## Resolved this pass

### 2026-06-07 — Known upstream bugs section added (from live MCP write test + tracker/codegraph sweep)

- **Trigger:** a live end-to-end write test through the MCP hit *"Operation value must be an Atlassian Document"* on `jira_transition_issue` with an inline comment. Root-caused via codegraph on the local clone (`jira/transitions.py` → `_add_comment_to_transition_data` calls `_markdown_to_jira` = **wiki markup**, but Cloud v3 transitions need **ADF**; standalone `jira_add_comment` converts ADF correctly) and matched to **open** tracker issue #1262. A sweep of the ~200 open issues surfaced three more agent-affecting bugs + the FastMCP CVE scope.
- **Added to `troubleshooting.md`** — new "Known upstream bugs & version notes (verified 2026-06-07)" section: **#1262** (transition+comment ADF, with code root cause + "DC v2 unaffected"), **#1274** (`jira_create_issue_link` inward/outward swapped), **#1279** (DC-behind-WAF 403 despite a valid PAT — `curl`/`urllib` `/myself` succeed where the MCP 403s, so a curl test doesn't prove the MCP works through the proxy), the **lossy markdown→wiki/ADF cluster** (#1340/41/43, #1311), and the **FastMCP `<3.2.0` CVEs reframed as deployment-mode-dependent** — verified against GitHub advisories that all are in OpenAPI-provider / OAuth-proxy+client / Windows-installer paths, **none reached by local stdio + PAT**; relevant only if exposed over HTTP (#1234).
- **sources.md:** +3 rows — the issue tracker (#1262/74/79/1340-cluster), the GitHub `fastmcp` advisories, and the `transitions.py` root cause (local clone @ v0.21.1 via codegraph). All `Verified 2026-06-07`.
- Frontmatter/triggers untouched (body-only edits can't affect triggering); content addition, no re-probe needed.

### 2026-06-07 — Client-setup gotchas added (from a live enablement failure)

- **Trigger:** demoing `confluence-best-practices` against a real Cloud instance surfaced that the connected `mcp-atlassian` had **only `jira_*` tools** — the Confluence client never started because only `JIRA_*` env was set. The skill documented the facts (separate vars in `auth-config.md:14`, `/wiki` in the env catalog) but the **always-loaded body was Jira-first**, the **same-Cloud-token-for-both** fact was absent, and the **exact failure symptom** ("no `confluence_*` tools") wasn't in `troubleshooting.md`. Classic "build the gotchas section from a real failure point."
- **3 additions (Dim 5 Completeness / Dim 9 Accuracy):**
  1. **SKILL.md** — new "**Enable Jira, Confluence, or both (the #1 setup miss)**" section (separate client per product; supplying only `JIRA_*` ⇒ only `jira_*` tools, silently; Cloud/DC URL+auth table with the `/wiki` and same-token facts; reconnect-after-env-change) + a **Cloud dual-product `claude mcp add`** example. Body 110→123 lines (under cap).
  2. **auth-config.md** — strengthened the Confluence-vars line: same Cloud email+token authorise both products (account-scoped), only the URL differs (`CONFLUENCE_URL` ends `/wiki`); DC uses its own host + `CONFLUENCE_PERSONAL_TOKEN`.
  3. **troubleshooting.md** — new "**Tools missing (one product absent)**" row: symptom `confluence_*` absent though server ✓ Connected → cause (Jira vars don't carry over) → fix (add the `CONFLUENCE_*` trio, reconnect, verify with `claude mcp list`).
- Frontmatter/triggers unchanged (1501/1536, 18/18 probe still valid — body edits can't affect triggering).

### 2026-06-07 — Renamed jira-mcp → jira-confluence-mcp (+ Confluence-trigger rebalance)

- **Why:** the skill configures the dual-product `sooperset/mcp-atlassian` server (Jira **and** Confluence — 15+ `CONFLUENCE_*` env vars, 6 Confluence toolsets, `confluence_*` tools), but `jira-mcp` named only one product and read oddly from the new `confluence-best-practices` sibling ("MCP setup → jira-mcp"). User also flagged that an `atlassian-mcp` / `mcp-atlassian` skill name would be confusable with the **MCP server** of (nearly) the same name. Verified there is **no hard namespace collision** (skills are bare-name; MCP entities are always `mcp__<server>__*`-prefixed; runtime name-dedup is skill-vs-skill only), but chose `jira-confluence-mcp` for unambiguous distinctness from the `mcp-atlassian` server.
- **Changes:** dir + `name:` + H1 + this backlog title → `jira-confluence-mcp`; updated 2 pointers in `confluence-best-practices/SKILL.md` + its trigger-eval label; **server name `mcp-atlassian` preserved** in all install commands/tool prefixes. `when_to_use` rebalanced (added `"confluence MCP"`, `"set up the jira/confluence MCP"`, `JIRA/CONFLUENCE_PERSONAL_TOKEN`, `JIRA/CONFLUENCE_SSL_VERIFY`, `CONFLUENCE_SPACES_FILTER`; routed Confluence *usage* → `confluence-best-practices`; dropped redundant "env vars for DC MCP"/"self-signed cert"/"mirror image"/"even if not named" phrases). Combined frontmatter **1501/1536**.
- **Re-probe (Haiku, eval set extended to 11 pos / 7 neg): 18/18.** All 3 new Confluence-MCP positives fire 1.00; the two dropped-phrase positives (self-signed cert, mirror image) still fire 1.00 off the description's TLS/air-gap content; the new Confluence-**usage** negative ("organise our confluence spaces") declines 0.00 (routes to `confluence-best-practices`). No regression on the Jira side.

### 2026-06-07 — Trigger + Improve + Freshen (full pipeline)

- **Trigger mode: 14/14 on BOTH Haiku and Opus** (train 9/9, test 5/5) at baseline — converged, **0 iterations/mutations**. Eval set: `references/trigger-evals.json` (8 should-trigger, 6 should-NOT; seed 42, holdout 0.4).
  - Positives (install / DC env vars / air-gap / 401 / hardening / image-mirror / self-signed cert) all fire 1.00.
  - Negatives clean: **runtime-usage** "search jira for my open issues" (Haiku 0.33 → **Opus 0.00** — correctly declines *using* the tools), **different-MCP decoy** "set up the github MCP server" (0.00), sibling decoys "create a jira ticket from the CLI" / "is this an epic or a story" (0.00), generics (0.00). The explicit NOT-boundary in the frontmatter holds on the real model.
- **Improve mode: blind 88 / self 89** — aligned (no dimension where self ≥ blind+2). Baseline + (since nothing mutated) final blind both = 88. **Ceiling mapped, 0 kept iterations.** No Boris caps (0 procedural-flow lists, 0 model-version-compensation phrases), no Dim 9 staleness cap (all 14 source rows dated 2026-06-07). The only flagged lever (CA consolidation) was rejected as a user-requirement conflict (see Open). Lowest blind dims (4/5/7 = 8) are "defers to references" = correct progressive disclosure, not defects.
- **Freshen mode: `fresh`, 0 changes.** Re-probed the one volatile claim — latest release still **v0.21.1 (2026-04-10)**, repo live/not-archived — matches the skill. All sources verified this session; `references/sources.md` already carries per-row `Verified: 2026-06-07`.
- **Boris minimalism:** body 106 lines + 5 references invoked → substantial, progressive-disclosure shape (not a collapse candidate).
