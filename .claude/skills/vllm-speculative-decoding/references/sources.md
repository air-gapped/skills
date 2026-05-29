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
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-05-29 | Latest stable **v0.21.0** (2026-05-15); **v0.22.0rc** in flight as of 2026-05-29 (v0.20.0 2026-04-27, then v0.20.1/.2, v0.21.0). Version-gate table caps at v0.19 — audit v0.20/v0.21/v0.22 release notes for new spec-dec gates. Re-run freshen on next skill-improver cycle. |
| EAGLE 3.1 announcement (vLLM blog) | https://vllm.ai/blog/2026-05-26-eagle-3-1 | 2026-05-29 | Config-driven extension of eagle3 (same `method` enum). FC-normalisation curbs attention drift at deeper k; up to 2× longer acceptance in long-context. Reference checkpoint `lightseekorg/kimi-k2.6-eagle3.1-mla`. Captured in `references/eagle3.md`. |
| HF EAGLE-3 + DFlash recipe survey | `hf models list --search {eagle3,dflash} --limit 500` | 2026-04-30 | 369 EAGLE-3 + 97 DFlash repos. Top ~50 + top ~25 inspected for documented training datasets. Five recipe families recur. Tabulated in `references/training-data-recipes.md`. Re-run survey if Speculators / SGLang / SpecForge ship new defaults. |

## Classifications summary

- **Fresh (no action):** all four vLLM PRs, ArcticInference, yuhuili HF checkpoint, aux_hidden_states allowlist content.
- **Version-drift (minor):** line numbers in `vllm/config/speculative.py` drifted (818-833 → 895-909). Fixed in SKILL.md, methods.md, eagle3.md, and dflash.md.
- **New-feature (noted only):** `MTPModelTypes` now includes 6 new model-specific aliases. Skill already documents that all `*_mtp` aliases route to unified `method="mtp"` so the eleven-method count remains correct; noted in this file for future audits. EAGLE 3.1 (2026-05-26) is a config-driven `eagle3` extension — captured in `eagle3.md`, no new method enum. v0.20/v0.21/v0.22 release notes not yet audited for new spec-dec gates — pins not bumped.

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

# Re-survey EAGLE-3 / DFlash training-data recipes (drives training-data-recipes.md)
hf models list --search eagle3 --limit 500 --format json | python3 -c '
import json,sys
data = sorted(json.load(sys.stdin), key=lambda d: d.get("downloads",0), reverse=True)
for d in data[:50]: print(d["id"])'
# Then for each repo:
#   curl -sL "https://huggingface.co/$ID/raw/main/README.md" | grep -iE "magpie|ultrachat|sharegpt|nemotron|perfectblend|eaglechat|specforge"
```
