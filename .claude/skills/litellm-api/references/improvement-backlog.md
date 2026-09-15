# Improvement backlog — litellm-api

Carries ceiling findings across skill-improver runs. See skill-improver `references/backlog-format.md` for admission rules.

## Resolved — 2026-09-15 (a skill about the auth model with no security floor)

- **Eight published advisories against LiteLLM's auth surface, none of them in
  the skill.** Three bypass authentication outright: OIDC userinfo cache-key
  collision (CVE-2026-35030, critical), SQL injection in proxy API-key
  verification (CVE-2026-42208, critical), and `Host:` header injection
  (CVE-2026-49468, critical). Reasoning about `allowed_routes` on a build where
  auth can be skipped entirely is wasted work, which is why the floor now sits
  above the recon protocol rather than in a reference.
- **Floor: v1.94.0**, the highest of the eight upper bounds (CVE-2026-84377).
  Every range is bounded, so each upper bound gives its floor directly — no
  `first_patched_version` is populated on any of them, which is normal for this
  feed and not evidence a fix is missing. Contrast the unbounded-range case
  recorded in `vllm-configuration`, where the same reasoning would produce "no
  safe version".
- **Two compound documented behaviour rather than sitting beside it.** The MCP
  auth bypass (CVE-2026-59822) lands on the same surface as the `/v1/mcp/*` RBAC
  bypass this skill already documents — one defeats authentication, the other
  authorisation, and a proxy under both has no MCP access control at all. And
  CVE-2026-84377 exfiltrates **provider credentials**, so remediation on an
  exposed build is rotating upstream keys, not just upgrading.
- **Latest-stable figure was six minors behind**: the header read "latest stable
  v1.94.0" against an actual v1.100.1 (2026-09-10). The grounding tag
  `4d543245` (v1.95.0-dev) is left as written — it records when the source was
  read and is not a claim about the world — but the gap is now stated as a
  number, which is what the skill's own "re-verify on the deployed tag" advice
  needs to be actionable.
- Added the one-line version probe (`/health/readiness` → `litellm_version`) so
  the floor can be checked before any of the auth analysis is applied.

## Open

- **Run `scripts/litellm-key-audit.sh` against a real proxy** — Dim 7. Execution-tested against a mock paginated `/key/list` (all four flag categories verified, fields checked against `LiteLLM_VerificationToken` in schema.prisma), but never against a live deployment. Requires author environment.

## Decided — do not re-propose

- **Trim the SKILL.md budget section's overlap with `budgets-spend.md`** — Dim 6. The baseline blind scorer flagged that the budget bullets (SKILL.md §"Budget semantics") repeat #29066/#34492/#35076 at near-reference detail. Deliberately NOT applied this pass: budgets are the highest-risk area the skill covers, and the SKILL.md rules are the always-loaded operative layer — reducing them to pointers would make the most dangerous semantics load-on-demand only. Revisit only with evidence that the duplication misleads (e.g. the two copies drift).
- **Frontmatter is 14 chars OVER the listing cutoff** (1,550/1,536 combined: description 797 + when_to_use 753), re-measured 2026-09-15 with `skill-improver/scripts/frontmatter-lengths.py`. **The previous note here claimed 6 chars of headroom, which was wrong in the unsafe direction** — an edit trusting it would have added text to a field that is already truncating. The tail of `when_to_use` (the NOT-for clause) is what gets cut, so any trigger addition must trade an existing phrase out, and a trim big enough to get under the cutoff should be verified by a trigger-mode run rather than by eye. Guard for future edits.

## Unblocked — actionable

- **Measure `delta_pass_rate`** — Dim 10 (capped at 8 unmeasured). Requires `evals/evals.json` + skill-creator's `aggregate_benchmark`. Flagged by the blind scorer as the binding cap.
- **Organizations coverage is comparatively thin** — Dim 5 (blind-baseline finding). Deeper org-lifecycle content (v2 PATCH clear-token semantics beyond the one row, org-admin permission bugs) needs research-pass material, not a one-iteration edit.

## Resolved — 2026-09-15 (freshen to v1.100.1)

- **The skill's headline budget claim was reverted upstream on the same day the
  skill last verified it.** The frontmatter description, a SKILL.md bullet, a
  whole `budgets-spend.md` section and a numbered rule all taught that team-key
  spend counts against members' personal budgets "since ~v1.94", with a broken
  opt-out. PR **#35271** (`revert(proxy)!: stop enforcing user budget on team
  keys`) merged **2026-07-30** and shipped in **v1.96.0**: team keys use team
  budgets only, and `skip_user_budget_on_team_key` was **deleted outright**,
  config field and UI toggle included. **v1.97.0** then added a deliberate
  opt-*in*, `general_settings.apply_user_budget_to_team_keys`, default off
  (PR #36102, 2026-08-07).
- **The direction of the error is the part worth remembering.** The v1.94
  behaviour was the surprising one, so the skill's advice — model personal
  budgets as personal plus team spend — was written to warn about it. On v1.96.0
  and later that advice **over-provisions**: the team key never touches the
  personal budget unless someone opted back in. Guidance that is correct for
  exactly one minor is a sharper hazard than guidance that is merely old, and
  a date-based freshen would not have caught it because the skill's stamp and
  the revert share a date.
- Corrected in all four places, as a version table rather than a single rule,
  since which behaviour applies is a version question and all three states are
  still in the field.

## Resolved this pass — 2026-07-30

Blind scores: baseline 84, final **88** (self final 87 — 1-point alignment, no bias flags). Post-final fix from the final blind's issue 2: added the verified `/spend/logs/v2` filter list + worked query recipe to `endpoint-map.md` (params read from `spend_management_endpoints.py:1595+`). Its issue 3 (6-char frontmatter headroom) recorded below as a guard; issue 1 (eval set) already in Open.

Initial improve run on the day the skill was authored. Self-score 80 → 87 (cold rescore); blind baseline 84 (higher than self — no inflation flags). 7 kept iterations:

- Dim 3: 4 second-person sentences → imperative.
- Dim 1: combined description+when_to_use trimmed 2026 → 1534 chars (under the 1536 cap; symptom triggers and NOT-for disambiguation no longer truncated). Dropped "litellm scim"/"litellm pass through" triggers whose payload was two one-liners (blind issue 2).
- Dim 7: key-audit script — removed fictional `object_permission.access_group_ids` branch after verifying `access_group_ids` is a direct `LiteLLM_VerificationToken` column (schema.prisma:444); jq logic unit-tested; then executed end-to-end against a mock paginated `/key/list` (correct A/C/D flags, safe key unflagged, pagination terminates).
- Dim 4/9: recon protocol's `/key/info` jq was wrong (`.info.user_role` doesn't exist — the info payload is the token row); replaced with verified fields and the `{"key","info"}` shape note.
- Dim 9: script paths now `${CLAUDE_SKILL_DIR}`-relative.
- Dim 6/8: tracker-health gotcha collapsed into a pointer; `/v2/organization/{id}` → `{organization_id}` standardized; blind-flagged broken backticks (config-db.md) and empty table cell (endpoint-map.md) fixed.

Discard rationales (anti-re-proposal guards):
- None discarded by score this pass; the budget-section trim was evaluated and deliberately declined (see Open) rather than attempted-and-reverted.
