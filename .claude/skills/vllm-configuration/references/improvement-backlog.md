# Improvement Backlog — vllm-configuration

Work-not-done log from skill-improver passes. Open = attempted but not applicable in one atomic iteration.

## Open

- Trim generic implicit triggers (`audit model X`, `deploy-memo`) from `when_to_use` — Dim 1, SKILL.md frontmatter (L7). Not applied: removing these risks under-triggering on the implicit per-model deploy-recipe contexts they were added for. Validating the trade-off needs trigger-mode measurement (60/40 split, 3 runs/query, blinded test scores), which this APPLY stage does not run. Carry to a dedicated trigger-mode pass. (carried 2026-05-28)
- Re-stamp the docs.vllm.ai env_vars / serve_args rows and the discuss.vllm.ai / GH-discussion #1405 rows in sources.md — Dim 9. Not re-confirmed this pass: the canonical docs URL `docs.vllm.ai/en/.../configuration/env_vars.html` 302-redirects and WebFetch of the redirect target 404s from this sandbox; only the `/serving/env_vars.html` variant resolved. Could not truthfully re-stamp those four rows to 2026-05-28, so they retain their 2026-04-24 date. GitHub-hosted rows (#8947, releases/latest) WERE re-verified via `gh` and stamped 2026-05-28. (carried 2026-05-28)

## Resolved this pass (2026-05-28)

- Release-version freshen: corrected sources.md latest-release line and row from v0.19.1 (2026-04-18) to the real latest **v0.21.0 (2026-05-15)**, verified via `gh api repos/vllm-project/vllm/releases/latest` — Dim 9. (A mid-pass intermediate edit briefly set this to a wrong "v0.11.2 (2026-05-23)"; corrected to v0.21.0. v0.11.2 actually published 2025-11-20.)
- Version-gate freshen: env-vars.md L3 "this table reflects v0.18–v0.20" → "v0.18–v0.21"; removed the stale "~260 lines as of v0.19" envs.py size claim — Dim 9. Gated on a v0.19/v0.20/v0.21 release-notes scan confirming their breaking changes touch torch/C++/pooling, not the operator env vars this table lists.
- #8947 fix-point reconciliation across three files — Dim 8. SKILL.md (config-file gotcha L62) and troubleshooting.md (L51) said "v0.10–v0.11"; config-file.md said "fixed in v0.10.1". Confirmed v0.10.1 tag (published 2025-08-18) and aligned all three to "fixed in v0.10.1 / pre-v0.10.1 affected". sources.md #8947 row re-stamped 2026-05-28 with the v0.10.1 fix detail.
- Removed the duplicate `VLLM_HOST_IP`-is-not-the-API-host pitfall (was Critical-pitfalls #2, a verbatim restatement of "Why this matters" point 3 and the Networking env-var entry) and renumbered the catalog 10→9 entries — Dim 6 simplification, no information lost.
