# Improvement backlog — open-webui-api

Carries findings across skill-improver runs. Append-only history; do not drop prior passes.

## Open

- **Family-level-only coverage (carried, needs author judgement on scope).** Three admin families are named but not enumerated, so a script author cannot call them from the skill alone: the 11 `/api/v1/knowledge/external/*` endpoints (covered by the token `/external/*`), the 13 admin `functions` endpoints, and the 8 admin `pipelines` endpoints (both covered by "all admin" blankets). Enumerating all 32 with payload shapes is a multi-file expansion that would roughly double `endpoint-map.md`; it may belong in a separate layered reference rather than inline. Not attempted this pass.
- **Trigger-mode measurement still has not run.** Unchanged from the 2026-07-22 note — use `/skill-improver trigger open-webui-api`, not description guessing. The frontmatter is at 1533/1536 chars, so any trigger-mode mutation must trim before it adds.

## Resolved this pass — 2026-07-29 (freshen mode, v0.10.2 → v0.11.0)

10 findings applied, 0 discarded. Verification-based decision rule (not score-based); every claim traced to code or a live probe against a v0.11.0 instance. Skill was 616 upstream commits stale (+2,593/−740 across the API surface).

- **models/model/update root-caused.** Prior text said "can 500, fall back to delete+create". Actual cause: `ModelForm.access_grants` is typed `list[dict | None]` but defaults to `None` (`models/models.py:180`); the omitted field survives request parsing, then `routers/models.py:752` re-validates explicitly and pydantic raises `list_type`. Sending `"access_grants": []` works. Both failure and fix executed live.
- **7 auth-level mismatches corrected** — `users/{id}/info` and `/{id}/active` are [user] not [admin] (info-disclosure surface); `models/export`+`import` are [user]+permission, only `/sync` is [admin]; `configs/banners` GET is [user]; `ollama/api/version` went public→[user] (401 verified live); `chats/share/{share_id}` is now anonymously readable for open shares; `ENV=dev` registers an unauthenticated `GET /retrieval/ef/{text}`.
- **22 missing admin endpoints added**, incl. the entire `audio` and `images` config routers (both return provider API keys — a real gap for config-backup and secret-audit scripts) and the SSRF-shaped `configs/terminal_servers/{policy,lifecycle,refresh}` proxies.
- **v0.11.0 silent-break class documented** — access-level response redaction (`models/list` params, `tools` content, model knowledge stripped *and rewritten in the DB*) which can round-trip an emptied catalog back through import/sync; `usage.prompt_tokens` now last-call-only; `updated_at` not bumped by background writes; internal chats hidden from all chat queries; admin exemption removed from automations (404).
- **`sharing.open_chats` upstream bug** — defined at `config.py:1950`, enforced at `chats.py:2041`, absent from `SharingPermissions` (`users.py:191-205`), so every permissions save through the API drops it. Verified live (the `sharing` block returns without the key) and independently corroborated by #27607.
- **SAFE_MODE vs ENABLE_PLUGINS** separated — SAFE_MODE is a destructive per-startup DB mutation that is *not* reversible by unsetting it; ENABLE_PLUGINS is the non-destructive 0.11.0 switch whose failure mode is `200 []`.
- **SSO-only token bootstrap** added — `ENABLE_LOGIN_FORM=False` + `ENABLE_API_KEYS=false` leaves no API-reachable way to get a token; documents minting a JWT from `.webui_secret_key`, including that `start.sh` exports it only into the app process.
- Version restamped throughout (frontmatter kept length-neutral at 1533/1536); open-issue set refreshed; `sources.md` re-stamped.

Method notes for the next pass: **regex decorator scans are unsafe** — `@router.get(` spans lines in 0.11.0 and a single-line regex reported `models GET /list` as removed when it was not; AST-parse instead. **Probe live before believing a diff**: the same false removal was caught in one curl. **Content-type, not status code** — SCIM returned `200 text/html` (the skill's own HTML-200 trap) and would have been logged as "mounted" on status alone. #27595 was logged as *not reproduced* rather than asserted, per the `unverifiable` gate.

## Resolved previous pass — 2026-07-22 (improve mode, first pass)

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
