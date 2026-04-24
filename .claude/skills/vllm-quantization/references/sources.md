# External sources — last verified 2026-04-24

Freshness audit for externally-referenced material in SKILL.md. Probes were
issued via the `gh` CLI and GitHub API. Re-run the freshen loop when the
rolling delta exceeds two minor vLLM releases.

## Probe results

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM issue #38652 — MLA FP8 KV multi-turn garbage | https://github.com/vllm-project/vllm/issues/38652 | 2026-04-24 | fresh (OPEN) | Title confirms DeepSeek/GLM MLA scope. Still unresolved — SKILL guidance "avoid on MLA multi-turn" remains correct. |
| vLLM issue #39407 — Gemma 4 FP8-block logit saturation | https://github.com/vllm-project/vllm/issues/39407 | 2026-04-24 | fresh (OPEN) | Updated today (2026-04-24). Title confirms "Gemma 4 31B FP8_BLOCK … absorbed activation scales being double-applied". Avoid FP8-block on Gemma 4 stands. |
| vLLM issue #40252 — Qwen3-Next NVFP4 linear_attn silent corruption | https://github.com/vllm-project/vllm/issues/40252 | 2026-04-24 | fixed (CLOSED 2026-04-20) | SKILL text softened — the specific regression is resolved, but the "audit `ignore` list" rule still applies to any new hybrid-attention model. |
| vLLM issue #39663 — online FP8 drops bias weights | https://github.com/vllm-project/vllm/issues/39663 | 2026-04-24 | fresh (OPEN) | Still open; prefer pre-quantized checkpoint for any bias-ed target (Qwen2 etc.). |
| vLLM source — `vllm/model_executor/layers/quantization/__init__.py` | https://github.com/vllm-project/vllm/blob/main/vllm/model_executor/layers/quantization/__init__.py | 2026-04-24 | fresh | 194 lines on main @ sha df052fdc. Cited range `107-184` remains in-bounds. |
| llm-compressor releases | https://github.com/vllm-project/llm-compressor/releases | 2026-04-24 | fresh | Latest tag `v0.10.0.1` (2026-03-13). SKILL references `v0.10+` for NVFP4 schemes — accurate. |
| NVIDIA ModelOpt releases | https://github.com/NVIDIA/TensorRT-Model-Optimizer/releases | 2026-04-24 | fresh | Latest stable `0.43.0` (2026-04-16); `0.44.0rc1` pre-release (2026-04-20). SKILL does not pin a version — no drift. |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-04-24 | version-drift (minor) | **v0.20.0 pre-release** cut 2026-04-23; v0.19.1 remains latest stable (2026-04-18). SKILL's "v0.14 → v0.19.1" window is still the production-pinned range. Added a v0.20 pre-release note under Version-gate highlights. |

## Classification summary

- fresh: 6
- fixed (closed): 1 — #40252 (content softened in place)
- version-drift: 1 — v0.20 pre-release noted
- deprecation / broken / unverifiable: 0

## Re-probe cadence

- Quantization layer churns at ~one format per vLLM minor. Re-run this
  freshen pass on each new minor release or every ~6 weeks, whichever is
  shorter.
- If an issue count rises above ~20 active bugs on the
  `component:quantization` label, bump priority.
