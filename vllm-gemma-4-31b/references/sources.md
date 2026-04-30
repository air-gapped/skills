# Sources — vllm-gemma-4-31b

External references cited by SKILL.md and `references/*.md`. Each row carries
the upstream URL, classification, last verification date, and pinned version
or git ref where applicable. Re-probe via `/skill-improver freshen vllm-gemma-4-31b`.

## Authoritative model + template sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r01 | https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja | hf-model | 2026-04-30 | sha256:94899c0f917d93f6fe81c95744d1e8ddab2d21d39228d2e4aec1fb2a25bff413 |
| r02 | https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit | hf-model | 2026-04-30 | — |
| r03 | https://huggingface.co/RedHatAI/gemma-4-31B-it-speculator.eagle3 | hf-model | 2026-04-30 | — |

## vLLM engine sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r04 | https://github.com/vllm-project/vllm | github | 2026-04-30 | v0.20.0 (released 2026-04-27) |
| r05 | https://github.com/vllm-project/vllm/blob/v0.20.0/vllm/engine/arg_utils.py | github-source | 2026-04-30 | v0.20.0 (sha ef3a9a982a, lines 2207-2288 — `get_batch_defaults` H100/H200 same code path) |
| r06 | https://github.com/vllm-project/vllm/blob/v0.20.0/vllm/v1/spec_decode/llm_base_proposer.py | github-source | 2026-04-30 | v0.20.0 (sha 94e09b209c, line 341 — P-EAGLE `pard_token` / `ptd_token_id` / `dflash_config.mask_token_id` requirement) |

## vLLM issue / PR citations

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r07 | https://github.com/vllm-project/vllm/issues/35467 | github-issue | 2026-04-30 | open — "non-optimal performance of `linear` for medium batches" (B200 numerical proof of HBM-bandwidth-bound saturation) |
| r08 | https://github.com/vllm-project/vllm/issues/22780 | github-issue | 2026-04-30 | closed — "Performance Drop with Concurrent Requests Using BnB-4bit Quantized Models" (AWQ vs BnB scaling contrast) |
| r09 | https://github.com/vllm-project/vllm/issues/6801 | github-issue | 2026-04-30 | open — "[RFC]: Performance Roadmap" (concurrency framed as Pareto knob, not fixed cap) |
| r10 | https://github.com/vllm-project/vllm/pull/17885 | github-pr | 2026-04-30 | merged 2025-05-11 — "[Perf] Use small max_num_batched_tokens for A100" (the only hardware-aware default branch in the engine) |

## Notes

- The template SHA pin in r01 is the operational handshake — if that hash
  changes, every section that references "the new chat_template" needs a
  re-read, and the cyankiwi/RedHatAI staleness claim in
  `SKILL.md:36-43` may flip.
- vLLM source paths in r05/r06 are line-pinned at `v0.20.0`. Bumping the
  pinned vLLM version requires re-probing both files; line numbers drift
  on every release.
- The skill's "vLLM 0.20+" claim aligns with r04 (latest is v0.20.0). When
  v0.21 ships, re-run freshen — the EAGLE3 / TRITON_ATTN / spec-config
  CLI surface is in flux upstream.
