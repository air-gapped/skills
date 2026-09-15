# Improvement backlog — open-webui-api

Carries findings across skill-improver runs. Append-only history; do not drop prior passes.

## Resolved — 2026-09-15 (no security floor, and the grounding tag is below it)

- **The skill carried no advisory content at all**, while Open WebUI published 69
  advisories between 2026-06-01 and 2026-09-15. Floor is **v0.11.1**; this file
  is grounded in **v0.11.0** source, so its own grounding tag sits *below* the
  floor. The file:line claims still describe 0.11.0 correctly — the instance they
  are pointed at should not be on it. Stated explicitly rather than quietly
  bumping the grounding stamp, which would have been a lie about what was read.
- **Four advisories defeat what this skill teaches**, which is why they are in
  the body and not a reference:
  - CVE-2026-87016 (`>= 0.6.41, < 0.11.1`) — sign in as another user via wildcard
    characters in the OAuth subject claim, **on SQLite**.
  - CVE-2026-70482 (`>= 0.8.0, < 0.11.0`) — account takeover; OAuth token
    exchange accepts tokens issued to any client.
  - CVE-2026-87998 (`>= 0.10.0, < 0.11.1`) — a non-admin deletes admin-owned
    external knowledge connections, so the `access_grants` model this file
    documents does not hold on 0.10.0–0.11.0.
  - CVE-2026-87999 (`< 0.11.1`) — any authenticated user reaches an internal
    platform channel via server-side web fetch.
- **The consequence is ordering, not just patching.** The first two mean user
  identity is not trustworthy below the floor, so group-membership and user
  provisioning cannot be meaningfully audited on such a build. The third means a
  permissions audit written against the `access_grants` section returns the wrong
  answer, because deletion did not honour it.
- **Derivation deliberately not duplicated.** `open-webui-valkey-websocket`
  §"Security floor" already carries the count, the all-null `first_patched_version`
  problem, and why an authenticating reverse proxy does not cover most of these.
  This file states the floor, the four that bear on its own subject, and points
  there — an overview developed in a sibling rather than a copy.

## Resolved — 2026-09-15 (security floor for API consumers)

- **69 advisories in a 3.5-month window, and the advisory feed cannot give you
  the floor.** Every one of those 69 (2026-06-01 to 2026-09-15) has
  `first_patched_version` set to **null** — not most, all. Tooling that reads
  that field concludes nothing is fixed. The floor has to be derived from
  `vulnerable_version_range` ceilings, the highest being `< 0.11.1` and
  `<= 0.11.0`, giving **v0.11.1**. Upstream additionally states some security
  fixes are withheld from the enumerated notes for a period, so that list is a
  lower bound.
- **Framed for this skill's reader specifically.** The largest advisory cluster
  (~30) is cross-tenant and privilege issues — endpoints checking ownership at
  the wrong granularity, trusting a client-supplied `knowledge_id`, folder
  parent or model metadata instead of re-deriving access server-side. That is
  the class most relevant to anyone driving the API, because it needs only an
  authenticated caller, which is exactly what an API token is.
- Checked and found already correct, so left alone: the `usage.prompt_tokens` /
  `completion_tokens` inversion to last-call-only, with `input_tokens` /
  `output_tokens` / `total_tokens` staying cumulative, is already documented in
  `breaking-changes.md` with the metering consequence spelled out.

## Open

## Unblocked — actionable

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
