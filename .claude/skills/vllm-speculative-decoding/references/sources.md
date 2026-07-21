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
| vllm/config/speculative.py — `SpeculativeMethod` enum | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/config/speculative.py | 2026-07-21 | **Enum grew: 11 → 13 base methods.** Two additions — **`custom_class`** (callable proposer backend, PR #39487, v0.22.0) and **`dspark`** via new `DSparkModelTypes` (#46995, v0.25.0). Structure: `EagleModelTypes = ["eagle", "eagle3", "extract_hidden_states", MTPModelTypes, DFlashModelTypes]`, so `dflash` and all `*_mtp` aliases nest inside it. `MTPModelTypes` now 20 entries (adds `mimo_v2_mtp`, `minimax_m3_mtp`, `bailing_hybrid_mtp`, `gemma4_mtp` since the last pass). Also new: `RejectionSampleMethod = ["standard", "synthetic", "block"]` — `block` from #46781. File is 1276 lines. |
| aux_hidden_states model support | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/v1/worker/gpu/spec_decode/eagle/eagle3_utils.py | 2026-07-21 | **BROKEN CITATION — the allowlist left `config/speculative.py`.** The prior two passes chased line-number drift (818-833 → 895-909) on a list that has since been **removed from the file entirely**. Support is now a capability interface: `SupportsEagle3` in `vllm/model_executor/models/interfaces.py`, checked by `supports_eagle3(model)` in `eagle3_utils.py`, which raises `RuntimeError("Model does not support EAGLE3 interface")`. Models declare layers via `get_eagle3_aux_hidden_state_layers()` / `set_aux_hidden_state_layers()`. `speculative.py` retains only the *method* tuple that consumes aux states: `eagle3`, `extract_hidden_states`, `dflash`, `dspark` (~line 301). |
| PR #25916 — EAGLE-3 preamble fix (+32% MTBench) | https://github.com/vllm-project/vllm/pull/25916 | 2026-04-24 | MERGED 2025-10-02. v0.11.1 gate still correct. |
| PR #36847 — DFlash method | https://github.com/vllm-project/vllm/pull/36847 | 2026-04-24 | MERGED 2026-03-30. v0.19 gate still correct. |
| PR #32887 — Unified Parallel Drafting (P-EAGLE enabler) | https://github.com/vllm-project/vllm/pull/32887 | 2026-04-24 | MERGED 2026-02-05. v0.16 gate still correct. |
| PR #29184 — ngram_gpu + async scheduler | https://github.com/vllm-project/vllm/pull/29184 | 2026-04-24 | MERGED 2026-03-07. v0.18 gate still correct. |
| ArcticInference repo (suffix + LSTM speculators) | https://github.com/snowflakedb/ArcticInference | 2026-04-24 | Latest release v0.1.2 (2026-01-24); repo still active (last push 2026-04-23). |
| yuhuili/EAGLE3-LLaMA3.1-Instruct-8B HF checkpoint | https://huggingface.co/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B | 2026-04-24 | Present, 245k downloads, Apache-2.0, last modified 2025-09-19. |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-07-21 | Latest stable **v0.25.1** (2026-07-14). **The v0.20→v0.25 spec-dec audit the last pass deferred is now done** — see the new gates section below. The version-gate table previously capped at v0.19; it now runs to v0.25.0. |
| Spec-dec changes v0.20.0 → v0.25.1 | release notes, all six minors | 2026-07-21 | Audited. Headlines: **TLI heterogeneous-vocabulary spec-dec** (#38174, v0.25.0), **`custom_class`** proposer (#39487, v0.22.0), **`dspark`** drafter (#46995, v0.25.0), **Dynamic SD** (#32374, v0.24.0; CUDA-graph-compatible #45953 in v0.25.0), **thinking-budget support** (#34668, v0.21.0), independent drafter attention backend (#39930, v0.21.0), block verification for rejection sampling (#46781, v0.25.0), and a **remote-DoS fix in spec-dec** (#44744, v0.24.0). DFlash matured well past its v0.19 debut: CPU support (#44029), backend selection (#46770), FlashInfer (#43081), per-layer RMSNorm fusion (#46761), causal DFlash (#43445), prefix-cache corruption fix (#42971). |
| PR #38174 — TLI universal spec-dec | https://github.com/vllm-project/vllm/pull/38174 | 2026-07-21 | **MERGED 2026-07-02**, ships v0.25.0. "Token-Level Intersection (TLI) speculative decoding, allowing target and draft models to have different (but overlapping) vocabularies." Based on an ICML 2025 method; closes #38173. **This relaxes the same-tokenizer rule taught in three places in this skill.** |
| PR #44744 — spec-dec DoS fix | https://github.com/vllm-project/vllm/pull/44744 | 2026-07-21 | Listed under **Security / Denial of service** in the v0.24.0 notes: "remote DoS via invalid recovered-token reinjection in speculative decoding". Anyone running spec-dec on a reachable endpoint should be ≥ v0.24.0. |
| EAGLE 3.1 announcement (vLLM blog) | https://vllm.ai/blog/2026-05-26-eagle-3-1 | 2026-05-29 | Config-driven extension of eagle3 (same `method` enum). FC-normalisation curbs attention drift at deeper k; up to 2× longer acceptance in long-context. Reference checkpoint `lightseekorg/kimi-k2.6-eagle3.1-mla`. Captured in `references/eagle3.md`. |
| HF EAGLE-3 + DFlash recipe survey | `hf models list --search {eagle3,dflash} --limit 500` | 2026-04-30 | 369 EAGLE-3 + 97 DFlash repos. Top ~50 + top ~25 inspected for documented training datasets. Five recipe families recur. Tabulated in `references/training-data-recipes.md`. Re-run survey if Speculators / SGLang / SpecForge ship new defaults. |

## Classifications summary (2026-07-21 pass)

- **Broken:** the aux-hidden-states allowlist citation. It is not a line-number
  drift this time — the list was **deleted from `config/speculative.py`** and
  replaced by the `SupportsEagle3` capability interface. Two prior passes
  re-pinned line numbers on this row; a third would have found no list at all.
  **Lesson: when a cited line range drifts twice, stop re-pinning and check
  whether the construct still belongs in that file.**
- **New-feature (applied):** enum grew 11 → 13 base methods (`custom_class`,
  `dspark`); `RejectionSampleMethod` gained `block`; `MTPModelTypes` reached 20
  aliases. Version-gate table extended v0.19 → v0.25.0 with twelve new rows.
- **New-feature (capability change):** **TLI** (#38174, v0.25.0) allows target
  and drafter to hold different-but-overlapping vocabularies. The
  same-tokenizer rule was stated unconditionally in `SKILL.md`,
  `methods.md` and `troubleshooting.md`; all three now scope it to
  pre-v0.25.0 or non-TLI use.
- **Security:** #44744 (v0.24.0) fixes a **remote DoS via invalid
  recovered-token reinjection in speculative decoding** — the first
  security-classified item in this skill's domain.
- **Not re-probed this pass:** the four original PRs (#25916, #36847, #32887,
  #29184 — all long-merged, gates unchanged), ArcticInference, the yuhuili HF
  checkpoint, and the EAGLE-3/DFlash training-data recipe survey. Budget went
  to the deferred v0.20→v0.25 audit, which was the outstanding item.

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
