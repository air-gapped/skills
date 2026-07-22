# Improvement backlog — open-webui-api

Carries findings across skill-improver runs. Append-only history; do not drop prior passes.

## Open

(empty — no attempted-but-unappliable items this pass)

## Resolved this pass — 2026-07-22 (improve mode, first pass)

Baseline self 84 / blind 91 → final self 90 / blind 90. Stop: 90+ with no dim below 7, at iteration 7 of 10.

- iter 1 keep (simplification): trimmed 3 weak trigger phrases; combined frontmatter 1607→1533 chars — NOT-for exclusion boundary now survives the 1,536 listing truncation (Dim 1).
- iter 2 keep (simplification): deduped the api_type-responses/reasoning explanation to `config-system.md` canonical + pointer in `admin-workflows.md` (Dim 6). Independently named by the blind baseline as its issue 3.
- iter 3 keep: TOC added to `admin-workflows.md` (>100-line rubric requirement; blind baseline issue 2) (Dim 2).
- iter 4 keep: second-person slip "before blaming yourself" fixed in `config-system.md` (blind-flagged) (Dim 3).
- iter 5 keep: executable preflight block (version + role probes with interpreted failures) added to SKILL.md (Dim 4).
- iter 6 **discard (noise)**: added single-user/trusted-header auth-modes line to SKILL.md auth section — Dim 5 check method (all trigger scenarios addressed) was already satisfied pre-change; +0, additive, reverted. Anti-re-proposal guard: do not re-add auth-mode coverage to SKILL.md without evidence a real query missed it; `events-scim.md` already covers trusted-header.
- iter 7 keep: bundled `scripts/owui-curl.sh` (2xx + JSON-content-type wrapper + `owui_preflight`) — evidence: both skill-creator eval agents independently reinvented this wrapper; live smoke-tested against a v0.10.2 instance incl. HTML-200 trap detection (Dim 7).
- post-stop fixes from final blind (objective, evidence-checked): "27 routers" → "26 (+2 feature-gated)" (verified against main.py mount block, 26 unconditional + analytics + scim); two second-person slips in `endpoint-map.md`/`events-scim.md` removed.

Known non-items (deliberately NOT open): combined frontmatter sits at ~1534/1536 chars — zero headroom is a future-edit constraint, not a defect; any future `when_to_use` addition must trim elsewhere first. Trigger-mode measurement has not run yet — use `/skill-improver trigger open-webui-api` (per repo convention), not description guessing.
