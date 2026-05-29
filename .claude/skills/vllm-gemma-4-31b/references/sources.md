# Sources — vllm-gemma-4-31b

External references cited by SKILL.md and `references/*.md`. Each row carries
the upstream URL, classification, last verification date, and pinned version
or git ref where applicable. Re-probe via `/skill-improver freshen vllm-gemma-4-31b`.

## Authoritative model + template sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r01 | https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja | hf-model | 2026-05-28 | sha256:36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0 (17466 B; **DRIFTED** from the 2026-04-30 pull `94899c0f…25bff413` — Google re-patched the template on `main`) |
| r02 | https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit | hf-model | 2026-04-30 | — |
| r03 | https://huggingface.co/RedHatAI/gemma-4-31B-it-speculator.eagle3 | hf-model | 2026-04-30 | — |

## vLLM engine sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r04 | https://github.com/vllm-project/vllm | github | 2026-05-28 | v0.21.0 latest (2026-05-15); v0.20.2 (2026-05-10), v0.20.1 (2026-05-04); v0.20.0 audit baseline (2026-04-27). Skill's "0.20+" floor still valid. |
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
- The skill's "vLLM 0.20+" claim aligns with r04 (re-confirmed 2026-05-28
  via `gh release list vllm-project/vllm`: v0.21.0 is now latest, released
  2026-05-15; the 0.20.0 audit baseline and the "0.20+" floor both remain
  valid). The r05/r06 line-pinned source paths were NOT re-probed against
  v0.21.0 this pass — line numbers drift on every release, so a future
  freshen should re-pin them against the current tag and re-check the
  EAGLE3 / TRITON_ATTN / spec-config CLI surface (in flux upstream).
- r01 chat_template re-pulled and re-hashed 2026-05-28 (curl, HTTP 200,
  17466 B): the SHA **DRIFTED** from `94899c0f…25bff413` (2026-04-30) to
  `36e3a42e…bead3f0`. Google re-patches the `main` template, so this is a
  moving target by design — every section that references "the new
  chat_template" should re-pull and re-pin per deploy rather than trust a
  historical SHA. The body (SKILL.md fact #3) now records both hashes and
  the moving-target warning. The structural staleness claim (cyankiwi/
  RedHatAI quants ship a stale template until they re-pull) still holds —
  it is even more strongly supported now that the canonical hash has moved.
