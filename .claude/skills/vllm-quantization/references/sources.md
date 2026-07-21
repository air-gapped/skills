# External sources — last verified 2026-07-21 (against vLLM v0.25.1)

Freshness audit for externally-referenced material in SKILL.md. Probes were
issued via the `gh` CLI and GitHub API. Re-run the freshen loop when the
rolling delta exceeds two minor vLLM releases.

**All three items the 2026-05-28 pass deferred were probed this pass**, and two
of them moved:

- **#38652 is fixed** — and it was the load-bearing "avoid FP8 KV on MLA
  multi-turn" rule. Guidance reversed.
- **`config/cache.py:18-34` had drifted** — two dtypes were missing from the
  skill's table. Line-range citation replaced with a symbol grep.
- `quantization/__init__.py:107-184` is still in-bounds (191-line file).

## Probe results

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM issue #38652 — MLA FP8 KV multi-turn garbage | https://github.com/vllm-project/vllm/issues/38652 | 2026-07-21 | **fixed (CLOSED `COMPLETED` 2026-05-15)** | Closed with *"Fixed by #37054"*. **Guidance reversed**: the skill's load-bearing "avoid FP8 KV on MLA multi-turn" rule is retired. Note the lag — #37054 merged **2026-03-18**, so the fix predated the issue closure by ~2 months and this skill's warning by ~4. Open state is not evidence of a live bug any more than closed state is evidence of a fix. |
| vLLM PR #37054 — MLA/FlashInfer KV-scale fix | https://github.com/vllm-project/vllm/pull/37054 | 2026-07-21 | fresh (MERGED 2026-03-18) | *"Fix KV scales inconsistency in fp8 MLA & FlashInfer kv_cache_dtype 'auto' leading to gibberish."* Two causes: FlashInfer applied `layer._[qkv]_scale` unconditionally even on unscaled BF16 QKV (normal **and** MLA paths, under `kv_cache_dtype=auto`); and MLA requires K/V to share one scale, so only one of `_k_scale`/`_v_scale` was handled. Already cited in `kv-cache.md` item 5 — this pass joined it to #38652. |
| vLLM issue #39407 — Gemma 4 FP8-block logit saturation | https://github.com/vllm-project/vllm/issues/39407 | 2026-07-21 | fresh (**still OPEN**) | Fix in flight: last comment notes [PR #40391](https://github.com/vllm-project/vllm/pull/40391) was reworked against current main. "Avoid FP8-block on Gemma 4" still stands; re-probe next pass to see if #40391 landed. |
| vLLM issue #40252 — Qwen3-Next NVFP4 linear_attn silent corruption | https://github.com/vllm-project/vllm/issues/40252 | 2026-07-21 | fixed (CLOSED 2026-04-20) | Closing comment scopes the fix narrowly: PR #34697 is *"specifically for the Qwen3-Next-family hybrid-attention models that ship fused in_proj_qkvz / in_proj_ba"*. That narrowness is why the general "audit the `ignore` list on any new hybrid-attention model" rule is kept. |
| vLLM issue #39663 — online FP8 drops bias weights | https://github.com/vllm-project/vllm/issues/39663 | 2026-07-21 | fresh (**OPEN, stale-bot-marked**) | Bot has flagged it for auto-close after 90 days of inactivity. If a later pass finds it CLOSED, that will mean abandonment, not a fix — keep preferring a pre-quantized checkpoint for any bias-ed target. |
| vLLM issue #32220 — NVFP4 KV cache support | https://github.com/vllm-project/vllm/issues/32220 | 2026-07-21 | **fixed (CLOSED `COMPLETED` 2026-05-04)** | Closed by a maintainer thanking a contributor — a real completion, not a bot. `nvfp4` is an accepted `CacheDType` value at v0.25.1, and v0.25.0 shipped NVFP4 KV cache with skip-layers sliding window (#42890). `kv-cache.md` row changed from "Roadmap" to shipped. |
| vLLM source — `vllm/config/cache.py` `CacheDType` | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/config/cache.py | 2026-07-21 | **drift** | The cited `18-34` range is stale — the `Literal` block has grown. At v0.25.1 it holds 16 entries; `int4_per_token_head` and `nvfp4` were both missing from this skill's table. Citation switched from a line range to "grep the `CacheDType = Literal[...]` block". |
| vLLM source — `vllm/model_executor/layers/quantization/__init__.py` | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/model_executor/layers/quantization/__init__.py | 2026-07-21 | fresh | 191 lines at v0.25.1 (was 194 on main at the 2026-04-24 probe). Cited range `107-184` remains in-bounds, but is within 7 lines of EOF — prefer a symbol reference on the next pass. |
| llm-compressor releases | https://github.com/vllm-project/llm-compressor/releases | 2026-07-21 | **drift** | Was recorded as "latest `v0.10.0.1` (2026-03-13)". Now **0.12.0 (2026-06-15)** is `isLatest`. **This project runs parallel maintenance lines** — 0.7.1.3 published **2026-06-26**, *later* than 0.12.0 but on an older branch. Sorting releases by date picks the wrong one; sort by version. Active lines: 0.7.1.x, 0.9.0.x, 0.10.0.x, 0.11.0, 0.12.0. |
| NVIDIA ModelOpt releases | https://github.com/NVIDIA/TensorRT-Model-Optimizer/releases | 2026-07-21 | version-drift | Latest stable **0.45.0** (2026-07-06), up from 0.43.0. The skill pins no ModelOpt version, so no body change was needed. |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-07-21 | re-stamped (window bumped) | **v0.25.1 (2026-07-14)** is current, four minors past the v0.21.0 baseline of the last pass. |

## Classification summary

- fresh: 4 — #39407 (open, fix in flight), #39663 (open, stale-marked), `quantization/__init__.py`, PR #37054
- **fixed (closed against a named fix): 3** — #38652 (**guidance reversed**), #32220 (nvfp4 KV now shipped), #40252 (fix scoped narrowly, general rule kept)
- **drift: 2** — `config/cache.py` line range + two missing dtypes; llm-compressor v0.10 → 0.12.0
- version-drift: 1 — ModelOpt 0.43.0 → 0.45.0 (no body change; skill pins no version)
- re-stamped (window bumped): 1 — vLLM releases, v0.21 → v0.25.1
- deprecation / broken / unverifiable: 0

## Re-probe cadence

- Quantization layer churns at ~one format per vLLM minor. Re-run this
  freshen pass on each new minor release or every ~6 weeks, whichever is
  shorter.
- If an issue count rises above ~20 active bugs on the
  `component:quantization` label, bump priority.
