# External-reference provenance

Cited upstream sources for this skill, probed on the `Last verified` date. Used
by skill-improver Dim 9 (staleness) and by anyone auditing whether a claim is
still current.

Method: `gh pr view` / `gh api repos/.../contents/...` / `gh api
repos/.../releases/latest` / HF `/api/models/<id>`. URLs are the canonical
upstream; for pinned line numbers in vLLM source, the skill cites the current
file path (line numbers drift across refactors — re-verify on upgrade).

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vllm/config/speculative.py — `SpeculativeMethod` enum | https://github.com/vllm-project/vllm/blob/main/vllm/config/speculative.py | 2026-04-24 | Enum unchanged (ngram, medusa, mlp_speculator, draft_model, suffix + EagleModelTypes + NgramGPUTypes). `MTPModelTypes` grew to include `qwen3_5_mtp`, `glm4_moe_lite_mtp`, `glm_ocr_mtp`, `exaone4_5_mtp`, `step3p5_mtp`, `hy_v3_mtp`. All aliases still route to unified `method="mtp"`. |
| vllm/config/speculative.py — aux_hidden_states allowlist | https://github.com/vllm-project/vllm/blob/main/vllm/config/speculative.py | 2026-04-24 | List identical (14 entries). Now at **lines 895-909**, not 818-833 — line numbers drifted. Content stable. |
| PR #25916 — EAGLE-3 preamble fix (+32% MTBench) | https://github.com/vllm-project/vllm/pull/25916 | 2026-04-24 | MERGED 2025-10-02. v0.11.1 gate still correct. |
| PR #36847 — DFlash method | https://github.com/vllm-project/vllm/pull/36847 | 2026-04-24 | MERGED 2026-03-30. v0.19 gate still correct. |
| PR #32887 — Unified Parallel Drafting (P-EAGLE enabler) | https://github.com/vllm-project/vllm/pull/32887 | 2026-04-24 | MERGED 2026-02-05. v0.16 gate still correct. |
| PR #29184 — ngram_gpu + async scheduler | https://github.com/vllm-project/vllm/pull/29184 | 2026-04-24 | MERGED 2026-03-07. v0.18 gate still correct. |
| ArcticInference repo (suffix + LSTM speculators) | https://github.com/snowflakedb/ArcticInference | 2026-04-24 | Latest release v0.1.2 (2026-01-24); repo still active (last push 2026-04-23). |
| yuhuili/EAGLE3-LLaMA3.1-Instruct-8B HF checkpoint | https://huggingface.co/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B | 2026-04-24 | Present, 245k downloads, Apache-2.0, last modified 2025-09-19. |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-04-24 | **v0.20.0** released 2026-04-23 (one day ago). Skill's version-gate table caps at v0.19; v0.20 spec-dec additions not yet audited. Re-run freshen on next skill-improver cycle. |

## Classifications summary

- **Fresh (no action):** all four vLLM PRs, ArcticInference, yuhuili HF checkpoint, aux_hidden_states allowlist content.
- **Version-drift (minor):** line numbers in `vllm/config/speculative.py` drifted (818-833 → 895-909). Fixed in SKILL.md and methods.md.
- **New-feature (noted only):** `MTPModelTypes` now includes 6 new model-specific aliases. Skill already documents that all `*_mtp` aliases route to unified `method="mtp"` so the eleven-method count remains correct; noted in this file for future audits. v0.20.0 exists but is un-audited — pins not bumped.

## Re-verification recipe

```bash
# vllm source (line-number drift check)
gh api repos/vllm-project/vllm/contents/vllm/config/speculative.py \
  --header "Accept: application/vnd.github.raw" \
  | grep -n "aux_hidden_states_supported\|SpeculativeMethod = Literal"

# PR state (all at once)
for pr in 25916 36847 32887 29184; do
  gh pr view "$pr" --repo vllm-project/vllm --json state,mergedAt,title
done

# Arctic Inference freshness
gh api repos/snowflakedb/ArcticInference/releases/latest --jq '{tag:.tag_name, published:.published_at}'

# HF checkpoint existence
curl -s "https://huggingface.co/api/models/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B" | head -c 400

# vLLM latest release (check for new minor)
gh api repos/vllm-project/vllm/releases --jq '.[0].tag_name'
```
