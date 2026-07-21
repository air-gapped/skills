# External sources — verification log

Tracks external references cited in this skill. `Last verified` indicates the most recent date an agent confirmed the URL resolves, the content still exists, and (where relevant) the claim the skill makes about it is still accurate. Stale dates mean: re-probe before trusting cited specifics.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM bench CLI docs | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-04-24 | 200 OK. `sonnet` dataset now flagged **deprecated** in overview table. Page is "latest developer preview" — no stable version pin. |
| `vllm bench serve` reference | https://docs.vllm.ai/en/latest/cli/bench/serve/ | 2026-04-24 | 200 OK. `--endpoint-type` gone. `--num-warmups` default 0. Backend value set expanded: `openai`, `openai-chat`, `openai-audio`, `openai-embeddings`, `openai-embeddings-chat`, `openai-embeddings-clip`, `openai-embeddings-vlm2vec`, `vllm`, `vllm-chat`, `vllm-pooling`, `vllm-rerank`, `infinity-embeddings`, `infinity-embeddings-clip`. |
| vLLM env vars (`VLLM_USE_MODELSCOPE` etc.) | https://docs.vllm.ai/en/latest/configuration/env_vars/ | 2026-04-24 | 200 OK. `VLLM_USE_MODELSCOPE` still documented. `HF_ENDPOINT` not explicitly listed on this page (upstream huggingface_hub env var, honored transparently). |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-07-21 | **v0.25.1 is current stable** (2026-07-14, `isLatest`). Four minors since the last stamp: v0.22.1 (2026-06-05), v0.23.0 (2026-06-15), v0.24.0 (2026-06-29), v0.25.0 (2026-07-11), v0.25.1. Skill text now uses "post-v0.25.1" for source-line claims. |
| `vllm-project/vllm#32841` (ModelScope LoRA) | https://github.com/vllm-project/vllm/issues/32841 | 2026-07-21 | **CLOSED / COMPLETED** 2026-01-23, unchanged. Run through the stale-close check (`skill-improver` freshen-patterns §3.0): the issue has **zero comments**, so it was *not* bot-closed — but there is also no linked fix PR and no closing rationale. Neither "fixed" nor "stale" is supported, so the skill's existing hedge ("historical gap; re-verify on your vLLM version") is the correct call and is **kept deliberately**, not through inattention. |
| `vllm/benchmarks/serve.py` | https://github.com/vllm-project/vllm/blob/main/vllm/benchmarks/serve.py | 2026-07-21 | On main, now **2284 lines**. Line refs **re-resolved**: `BenchmarkMetrics` ~L176-215 → **~L321**; JSON assembly ~L989-1020 → **~L1198-1219**. `endpoint_type` still absent from the emitted JSON. All five previously-noted fields still present. **Three in-scope additions since the last cycle:** `--chat-template-kwargs` for client-rendered reasoning benchmarks (#44244, 2026-06-03), client/server tokenizer-mismatch auto-correction for `random` (#44708, 2026-06-08), and the BFCL tool-calling dataset (#42457, 2026-06-10). `--num-warmups` default re-read: still **0**. |
| `vllm bench` dataset table (rendered docs) | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-05-28 | Rendered dataset table lists (in addition to the prior catalog): `spec_bench` (Spec-Bench, speculative decoding), `speed_bench` (SPEED-Bench, NeMo-Skills), `custom_audio`, `custom_image`. `sonnet` still flagged deprecated. All four newly-surfaced names confirmed via WebFetch this cycle and added to `datasets.md`. |
| `vllm/benchmarks/sonnet.txt` | https://github.com/vllm-project/vllm/blob/main/benchmarks/sonnet.txt | 2026-04-24 | 22,706 bytes. Still in tree. Dataset itself marked deprecated in docs; file remains. |
| In-tree benchmarks dir | https://github.com/vllm-project/vllm/tree/main/benchmarks | 2026-04-24 | Tree exists (verified via sonnet.txt contents API). |
| Air-gapped discussion thread | https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916 | not probed | Low priority — forum thread, supplementary. Probe next cycle if cited. |
| vLLM performance dashboard | https://docs.vllm.ai/en/latest/benchmarking/dashboard/ | not probed | Low priority this cycle; subdomain of already-verified docs.vllm.ai. |
| Blog: Anatomy of a High-Throughput LLM Inference System (2025-09-05) | https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html | not probed | Blog post, dated; excluded per freshen rule "drop blogs/social posts." |
| Blog: Large Scale Serving — DeepSeek @ 2.2k tok/s/H200 (2025-12-17) | https://blog.vllm.ai/2025/12/17/large-scale-serving.html | not probed | Same — blog; not on the priority list for this cycle. |

## Probe budget 2026-05-28 cycle: 8/8 used

Probes:
1. `gh issue view 32841` — closed
2. `gh api .../contents/benchmarks/sonnet.txt` — fresh
3. `gh api .../contents/vllm/benchmarks/serve.py` — fresh + drift
4. `gh release list` — confirms v0.11.0 → v0.19.1 → v0.20.0
5. WebFetch docs.vllm.ai/en/latest/cli/bench/serve/ — new-feature (backend list)
6. WebFetch docs.vllm.ai/en/latest/configuration/env_vars/ — fresh
7. WebFetch docs.vllm.ai/en/latest/benchmarking/cli/ — deprecation (sonnet)
8. `gh api .../issues/32841/comments` — empty (consumed as part of #1 clarification)

## Content updates applied 2026-04-24

- `SKILL.md`: expanded `--backend` value list; softened #32841 claim to "historical gap, re-verify."
- `references/commands.md`: expanded `--backend` value list with verification note.
- `references/datasets.md`: flagged `sonnet` as deprecated upstream.
- `references/air-gapped.md`: softened #32841 claim.
- `references/output-schema.md`: removed `endpoint_type` from top-level JSON (no longer emitted); corrected source-line refs (~L176-215, ~L989-1020); added new fields (`request_goodput`, `max_output_tokens_per_s`, `max_concurrent_requests`, `rtfx`, `start_times`); stamped header with Last verified 2026-04-24.

## Content updates applied 2026-05-28

Probes: `gh release list` (v0.21.0 latest stable, 2026-05-15), `gh issue view 32841` (CLOSED/COMPLETED, unchanged), `gh api commits?path=vllm/benchmarks/serve.py` (trace-replay commit `bfb9ebc211` / PR #39795, 2026-05-28), WebFetch `docs.vllm.ai/en/latest/benchmarking/cli/` (dataset table: `spec_bench`, `speed_bench`, `custom_audio`, `custom_image`, `sonnet` deprecated).

- Release framing bumped v0.19.1 → **v0.21.0** as current stable across `sources.md` and `output-schema.md` (header + stable-fields note + source-of-truth stamp).
- Warmup version-boundary unified to **v0.11–v0.21** across `SKILL.md`, `troubleshooting.md`, `output-schema.md`, `methodology.md` (was inconsistent: v0.19 vs v0.11–v0.19). "Does not auto-warm" still holds — no commit added auto-warm.
- `commands.md`: added **timed trace replay** (v0.21+) under `vllm bench serve` Load shape (verified merged feature).
- `datasets.md`: added **`spec_bench`** (Spec-Bench, speculative decoding), **`speed_bench`** (SPEED-Bench), **`custom_audio`** and **`custom_image`** (multimodal `custom` variants) — all four confirmed present in the rendered `docs.vllm.ai/en/latest/benchmarking/cli/` dataset table this cycle.
- `methodology.md`: replaced corrupted placeholder text in "Capturing prod prompts" and "Statistical hygiene" sections with real content (mirrors `datasets.md` + SKILL.md reporting guidance).
- `SKILL.md`: trimmed `when_to_use` so combined description+when_to_use = 1529 chars (≤ 1536 listing cap); dropped only redundant/deprecated phrases (`sonnet dataset`, `does this deploy get faster`, `can {model} hit TTFT Y`).

## Content updates applied 2026-07-21

Probes (7): `gh issue view 32841` (stale-close check — zero comments), `gh release list`
(v0.25.1), `gh api commits?path=vllm/benchmarks/serve.py&since=2026-05-28` (6 commits),
`gh api contents/.../serve.py` (flags, defaults, JSON assembly, line re-resolution),
`gh api contents/vllm/benchmarks` (module layout), `gh api contents/.../datasets/datasets.py`
(dataset names), plus the three PR titles resolved from commit messages.

- **v0.21.0 → v0.25.1** across `sources.md` and `output-schema.md`.
- **Warmup boundary extended v0.11–v0.21 → v0.11–v0.25** in `SKILL.md` and
  `troubleshooting.md` — not assumed: `--num-warmups` default re-read as `0` in the
  current tree, so "does not auto-warm" still holds.
- **`output-schema.md` line refs re-resolved** (~L321 and ~L1198-1219). The old refs had
  drifted by hundreds of lines; the file now says to resolve by symbol, not by line.
- **`commands.md`: three new features added.** The important one is the
  `--chat-template-kwargs` vs `--extra-body chat_template_kwargs` distinction — two
  near-identically-named knobs on **opposite sides of the wire**, where picking wrong
  silently benchmarks the wrong mode. Also the `random`-dataset tokenizer-mismatch
  auto-correction, which is a **re-baseline trigger**: numbers taken either side of
  2026-06-08 are not comparable.
- **`datasets.md`: module move recorded** — `vllm/benchmarks/datasets.py` is now the
  package `vllm/benchmarks/datasets/datasets.py`; the old flat path 404s. Newly observed
  in-tree names logged as observations, not as a completeness claim.
- **NOT re-probed this cycle:** the three `docs.vllm.ai` rendered-docs rows (2026-04-24)
  and the two blog rows. They keep their old stamps rather than borrowing today's date.

