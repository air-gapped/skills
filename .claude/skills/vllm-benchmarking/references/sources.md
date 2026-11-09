# External sources — verification log

Freshened: 2026-11-09

Every row below was probed on that date: web rows by URL fetch, issue/PR rows through the GitHub API, code rows by reading `vllm-project/vllm` at tag **v0.33.0** (commit `4ba787ec`). Line numbers are at that tag unless a row says otherwise.

**Earlier pass, 2026-10-18:** every row probed at v0.32.0 (all URLs 200, 25 issue/PR states batched, serve.py flags/JSON keys diffed v0.30.0→v0.32.0: no change). Moved: `sonnet` dataset removed (13 `--dataset-name` values), `openai-responses` backend added (13 backends), sweep `--warmup-num-prompts`/`--continue-on-error`, `transformers >= 5.16.1, < 5.20.0` + `tokenizers >= 0.23.2`; corrected long-standing `--metric-percentiles`/`--percentile-metrics` defaults and sweep sub-mode names.

**Earlier pass, 2026-09-15:** all 15 rows probed. Every URL 200s with no redirect drift, and every claim pinned to tag `v0.27.0` was re-read at that tag and holds exactly (`serve.py` 2363 lines, `BenchmarkMetrics` L321, `sonnet.txt` 22706 bytes, six bench subcommands, `transformers >= 5.5.3`). The docs still lag the tree on `VLLM_USE_RUST_BENCH` and still list `sonnet` as the only deprecated dataset. One row drifted: current stable is **v0.29.0** (2026-09-09) via v0.28.0, not v0.27.1.

## Releases and docs

| Ref | URL | Notes |
|---|---|---|
| vLLM releases | https://github.com/vllm-project/vllm/releases | **v0.33.0 is current stable**, published 2026-11-02. The GitHub Release object is titled `v0.33.0` but hangs off tag `v0.33.0rc3` (https://github.com/vllm-project/vllm/releases/tag/v0.33.0rc3: `isLatest`, not a prerelease); git tag `v0.33.0` points at the same commit `4ba787ec`, and PyPI `vllm 0.33.0` was uploaded 2026-11-02. A release listing that prints only tag names shows the newest release as an rc — it is not. Previous: v0.32.0 (2026-10-18). No v0.32.1 release (tag `v0.32.1rc0` only). The v0.33.0 notes do not mention `vllm bench` at all; every benchmark change below was read from `git log v0.32.0..v0.33.0 -- vllm/benchmarks docs/benchmarking` and the diffs. |
| vLLM bench CLI docs | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 200. No `sonnet`, no dataset flagged deprecated. Has "Model Forward Benchmark", "Responses API Benchmark" (incl. the `include_reasoning: false` TTFT warning) and "Saving Server-Side Per-Request Metrics". Still says "All sampling parameter flags are supported except --min-p, which the Responses API does not accept" — stale since #48084 (v0.32.0 code accepts it). Still no mention of `VLLM_USE_RUST_BENCH`. Sweep `--warmup-num-prompts`/`--continue-on-error` are not on this page. Recommends GuideLLM for production servers (unchanged since v0.32.0). |
| `vllm bench serve` reference | https://docs.vllm.ai/en/latest/cli/bench/serve/ | 200. `--endpoint-type` absent. `--num-warmups` default 0. `--backend`: 13 choices incl. `openai-responses`, no `vllm-chat`. `--dataset-name`: 13 choices, default `random`. `--metric-percentiles` default 99. `--percentile-metrics` help matches the source. `latest` (main) adds "Always skipped for chat backends" to `--skip-chat-template` (#65245, unreleased). `/en/stable/` renders v0.33.0 (identical to `/en/v0.33.0/cli/bench/serve/`). |
| `vllm bench forward` reference | https://docs.vllm.ai/en/v0.33.0/cli/bench/forward/ | 200. Prose description: `docs/cli/README.md` "### forward" at v0.33.0. |
| vLLM env vars | https://docs.vllm.ai/en/latest/configuration/env_vars/ | 200 (`latest` and `stable`). `VLLM_USE_MODELSCOPE`, `VLLM_USE_RUST_BENCH`, `VLLM_USE_RUST_FRONTEND`, `VLLM_RUST_FRONTEND_PATH`, `VLLM_SERVER_DEV_MODE` documented. `HF_ENDPOINT` not listed (upstream `huggingface_hub` variable). |
| vLLM performance dashboard | https://docs.vllm.ai/en/latest/benchmarking/dashboard/ | 200, "Performance Dashboard". |
| Air-gapped discussion thread | https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916 | 200, thread live. |
| Blog: Anatomy of a High-Throughput LLM Inference System (2025-09-05) | https://vllm.ai/blog/2025-09-05-anatomy-of-vllm | 200, no redirect. `blog.vllm.ai` still forwards to `vllm.ai/blog`. |
| Blog: Large Scale Serving — DeepSeek @ 2.2k tok/s/H200 (2025-12-17) | https://vllm.ai/blog/2025-12-17-large-scale-serving | 200. "sustained throughput of 2.2k tokens/s per H200 GPU". |
| hf-mirror | https://hf-mirror.com | 200. Page documents `export HF_ENDPOINT=https://hf-mirror.com`. |
| ShareGPT file | https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json | Resolves (ranged GET 206 via the Hub CDN). |

## Code at tag v0.33.0

| Ref | URL | Notes |
|---|---|---|
| `vllm/benchmarks/serve.py` | https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/benchmarks/serve.py | **2460 lines** (2410 at v0.32.0). `BenchmarkMetrics` **L342**, `EmbedBenchmarkMetrics` L377, `result_json["date"]` **L2306**, `endpoint_type` alias L2307. **Argparse flag set identical to v0.32.0** (54 flag strings). `--num-warmups` default 0 (L1781); `--percentile-metrics` default `None` → `ttft,tpot,itl` / `e2el` (L1848); `--metric-percentiles` default `"99"` (L1859); `--max-concurrency <= 0` raises at L2057; `completed`/`failed` keys L1321-1322. Warmup loop L926-942 replays `test_input` (L893), built from the first sampled request. |
| `vllm/entrypoints/cli/benchmark/` + `vllm/envs.py` | https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/entrypoints/cli/benchmark/main.py | **Seven** subcommand modules: forward, latency, mm_processor, serve, startup, sweep, throughput (six at v0.32.0). `maybe_exec_rust_bench()` fires only for `sys.argv[1:3] == ["bench","serve"]` with `VLLM_USE_RUST_BENCH` truthy, then `os.execv`s `VLLM_RUST_FRONTEND_PATH`. `envs.py` L168-171: `VLLM_USE_RUST_FRONTEND`/`VLLM_USE_RUST_BENCH` default `False`, `VLLM_RUST_FRONTEND_PATH` default `"auto"`, `VLLM_SERVER_DEV_MODE` default `False`. |
| `vllm bench forward` (#61339) | https://github.com/vllm-project/vllm/pull/61339 | MERGED 2026-10-14, new in v0.33.0 (follow-ups #61692, #63613, #63616, #63622). `vllm/benchmarks/forward/main.py`: `--case`, `--shapes`, `--kv-len-jitter` 0.5, `--routing auto`, `--exclude-drafter`, `--iters` 20, `--samples` 5, `--output-json`, `--profile-dir`; `set_defaults(load_format="dummy", enable_prefix_caching=False)`; `median_us` per case, each replay the max over ranks; "unstable timing" warning above 0.5% sample spread. |
| `requirements/common.txt` | https://github.com/vllm-project/vllm/blob/v0.33.0/requirements/common.txt | v0.33.0: `transformers >= 5.16.1, < 5.21.0`, `tokenizers >= 0.23.2`, `huggingface_hub >= 1.31.0`. v0.32.0: `< 5.20.0`. v0.31.0: `transformers >= 5.10.4, < 5.18.0`, `tokenizers >= 0.21.1`. v0.30.0: `transformers >= 5.10.4`, `tokenizers >= 0.21.1`. v0.27.0: `>= 5.5.3`. "Transformers 5.x" bumps in `requirements/test/*` (#49223, #59621, #60381) are CI pins, not runtime floors. |
| Dataset choices | https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/benchmarks/datasets/datasets.py | `add_dataset_parser` `--dataset-name` at L1593: 13 choices, default `random`; file unchanged since v0.32.0. `bfcl` is not a choice (selected via `--dataset-path`/`--hf-name` + `--backend openai-chat`). `bench throughput` has its own 8-value list (`throughput.py` L785) and backends `vllm`, `hf`, `mii`, `vllm-chat` (L781). The rendered docs table lists dataset families, not the argparse values. |
| `benchmarks/sonnet.txt` (removed) | https://github.com/vllm-project/vllm/pull/60129 | MERGED 2026-10-06, shipped v0.32.0. Path absent at v0.33.0, present at v0.31.0. |
| In-tree benchmarks dirs | https://github.com/vllm-project/vllm/tree/v0.33.0/vllm/benchmarks | `datasets/`, `forward/` (new), `lib/`, `sweep/`, `latency.py`, `mm_processor.py`, `plot.py`, `serve.py`, `startup.py`, `throughput.py`. Sweep `parser_name`s: `serve`, `serve_workload`, `startup`, `plot`, `plot_pareto`. `sweep/serve.py` `--warmup-num-prompts` L548, `--continue-on-error` L558 (#57305, MERGED 2026-09-30, v0.32.0). The legacy top-level `benchmarks/` dir (https://github.com/vllm-project/vllm/tree/main/benchmarks, 200) has no `sonnet.txt` and no `disagg_benchmarks/`. |
| `benchmarks/disagg_benchmarks/` (removed) | https://github.com/vllm-project/vllm/pull/44854 | MERGED 2026-06-08 (commit `5add018beb`, first in the v0.24.0 line): removed with `P2pNcclConnector`. Absent at v0.27.0, v0.32.0, v0.33.0. `examples/disaggregated/disaggregated_serving/disagg_proxy_demo.py` and `examples/disaggregated/lmcache/disagg_prefill_lmcache_v1/` exist at v0.33.0. |
| `vllm/benchmarks/sweep/server.py` | https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/benchmarks/sweep/server.py | Unchanged since v0.32.0: reset endpoints L16-18, server launched with `VLLM_SERVER_DEV_MODE=1` (L53), `after_bench()` L72. Basis for the reset in `scripts/bench-sweep.sh`. |
| Dev-mode cache routes + prefix-caching default | https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/entrypoints/serve/dev/cache/api_router.py | `/reset_prefix_cache` L20, `/reset_mm_cache` L47, `/reset_encoder_cache` L57; attached only under `VLLM_SERVER_DEV_MODE` (`launchers/api_server/routers.py` L46). `enable_prefix_caching: bool = True` (`vllm/config/cache.py` L257); CLI default `None` resolves to `model_config.is_prefix_caching_supported` (`vllm/engine/arg_utils.py` L3045, L3075). Counters `vllm:prefix_cache_queries` / `vllm:prefix_cache_hits` (`vllm/v1/metrics/loggers.py` L662, L673). `bench latency` sets `enable_prefix_caching=False` (`latency.py` L77). |

## Issues and PRs

| Ref | URL | Notes |
|---|---|---|
| `#32841` + `#32844` (ModelScope LoRA) | https://github.com/vllm-project/vllm/pull/32844 | Issue #32841 CLOSED/COMPLETED 2026-01-23 by its reporter, zero comments, no timeline cross-reference. **Fixed by #32844** (MERGED 2026-01-22, same author, body names #32841): `vllm/lora/utils.py` has no ModelScope branch at v0.14.1 and has `if envs.VLLM_USE_MODELSCOPE:` at v0.15.0 and v0.33.0 (L371). Four earlier passes kept a "status unclear" hedge because the issue links no PR; the code settles it. |
| `#54136` (client queue time) | https://github.com/vllm-project/vllm/pull/54136 | MERGED 2026-09-01, v0.30.0. At v0.33.0: `client_queue_time` recorded `serve.py` L1016; `queue_times` L1335/L1353. |
| `#55508` (streaming TTFT/E2EL accounting) | https://github.com/vllm-project/vllm/pull/55508 | MERGED 2026-09-13, v0.30.0. "Never received a valid chunk to calculate TTFT." at `endpoint_request_func.py` L303, L498, L796. |
| `#54887` (reject non-positive `--max-concurrency`) | https://github.com/vllm-project/vllm/pull/54887 | MERGED 2026-09-04, v0.30.0. Check at `serve.py` L2057. |
| `#56760` (complete pooling responses) | https://github.com/vllm-project/vllm/pull/56760 | MERGED 2026-09-15, v0.30.0. `bytes`/`bytes_only` drained via `iter_any()` at `endpoint_request_func.py` L856-866. |
| `#56662` (credentials redacted) | https://github.com/vllm-project/vllm/pull/56662 | MERGED 2026-09-14, v0.30.0. `redact_sensitive_namespace()` in `lib/utils.py` L12; `_SENSITIVE_ARG_FIELDS = ("header",)` `serve.py` L66, applied at L2056 and L1580. |
| `#54628` + `#48084` (Responses API backend) | https://github.com/vllm-project/vllm/pull/54628 | #54628 MERGED 2026-09-28, v0.31.0: `openai-responses` in `ASYNC_REQUEST_FUNCS` (L1155-1170, 13 entries). #48084 (https://github.com/vllm-project/vllm/pull/48084) MERGED 2026-10-08, v0.32.0, removed the `--min-p` rejection; none at v0.33.0. |
| `#60923` (scheduled deprecations removed) | https://github.com/vllm-project/vllm/pull/60923 | MERGED 2026-10-10, v0.32.0: `bench throughput --dataset` gone (no such flag in `throughput.py` at v0.33.0). |
| `#58112` (`model_id` in latency/throughput JSON) | https://github.com/vllm-project/vllm/pull/58112 | MERGED 2026-09-25, v0.31.0: `latency.py` L173, `throughput.py` L1119. |
| `#49611` + `#60511` (probe requests) | https://github.com/vllm-project/vllm/pull/60511 | #49611 MERGED 2026-08-01, v0.27.0. #60511 MERGED 2026-10-15, **first in v0.33.0** (not in the v0.32.0 tag): probes get their own session, duration is taken before the probe task stops. PR table: probe p99 3.0-7.8 s → 0.24-0.29 s at `--max-concurrency 32`. |
| `#66246` (probes inherit `--extra-body`) | https://github.com/vllm-project/vllm/issues/66246 | OPEN, created 2026-11-07. At v0.33.0 `probe_loop` keeps `extra_body` and `_update_payload_common` applies it over the length field. |
| `#55809` (server-side per-request metrics) | https://github.com/vllm-project/vllm/pull/55809 | MERGED 2026-10-22, v0.33.0: `server_queue_times`/`server_ttfts` under `--save-detailed`; populated only by the completions and chat request funcs. |
| `#62341` + `#64937` (chat streamed-output counting) | https://github.com/vllm-project/vllm/pull/62341 | #62341 MERGED 2026-10-19, v0.33.0: `_choice_has_streamed_output` (role-only chunk no longer the first token). #64937 (https://github.com/vllm-project/vllm/pull/64937) MERGED 2026-11-04 to main, **not in v0.33.0**: accepts `reasoning_content`; v0.33.0 checks `delta.get("reasoning")` only (L398). `vllm/entrypoints/openai/protocol.py` carries a `reasoning` field at v0.12.0 and only `reasoning_content` at v0.10.0. |
| `#51172` (SSE across transport chunks) | https://github.com/vllm-project/vllm/pull/51172 | MERGED 2026-10-14, first in v0.33.0: per-chunk `.strip()` removed from the completions, chat and audio loops. |
| `#59888` (`/tokenize` alignment warning) | https://github.com/vllm-project/vllm/pull/59888 | MERGED 2026-10-17, first in v0.33.0. Alignment (#44708, v0.23) runs for `random` and `prefix_repetition` (`serve.py` L2215) and posts `model` = `--model`. |
| `#57519` (stream ending in an error event) | https://github.com/vllm-project/vllm/pull/57519 | MERGED 2026-11-03 to main, **not in v0.33.0**: only the Responses path checks error events at the tag. |
| `#65245` (client chat template on chat backends) | https://github.com/vllm-project/vllm/pull/65245 | MERGED 2026-11-03 to main, **not in v0.33.0**: `get_samples` passes `args.skip_chat_template` unchanged at the tag. |
| `#64227` (throughput length flags) | https://github.com/vllm-project/vllm/pull/64227 | MERGED 2026-10-28 to main, **not in v0.33.0**: `throughput.py` L549-551 at the tag. |
| `#65071` + `#65083` (numeric-string prompts) | https://github.com/vllm-project/vllm/pull/65083 | Issue closed 2026-11-02; fix on main (`f48cc6262e`), **not in v0.33.0** (`datasets.py` L2454 has no `dtype`). |
| Rust bench client: `#50081`, `#64551`, `#64946`, `#64308` | https://github.com/vllm-project/vllm/pull/50081 | #50081 MERGED 2026-07-28 (opt-in, v0.27.0); #48107/#48930 the port. Issues #64538, #64939, #64226 closed 2026-11-04 by #64551, #64946, #64308 on main, **none in v0.33.0** (checked in `rust/src/bench/src/config.rs` and `output/json.rs` at the tag). Rust-only, no effect on the Python client: HF ShareGPT multi-turn (#51104, #56915) and the `mm-processor` port (#51922). |
| `#66359` (Rust client, short random prompts) | https://github.com/vllm-project/vllm/issues/66359 | OPEN, created 2026-11-08: Rust client sends prompts shorter than `--random-input-len`. Not written into `commands.md` (no fix or workaround to state beyond "do not opt in"). |
| `#61701` (Medusa, MLP speculator removed) | https://github.com/vllm-project/vllm/pull/61701 | MERGED 2026-10-15, v0.33.0 breaking change; zero `medusa` hits under `vllm/` and `docs/` at the tag. |
| Older feature PRs cited in `commands.md` | https://github.com/vllm-project/vllm/pull/39795 | All MERGED: #39795 timed trace replay 2026-05-28; #44244 `--chat-template-kwargs` 2026-06-03; #44708 tokenizer alignment 2026-06-08; #42457 BFCL 2026-06-10; #57387, #59796, #59614 dependency bumps 2026-10-02; #56300 mm-processor crash fix 2026-09-11. |

**Not applied, logged:** `bench throughput`/`mm-processor` crashes with HF datasets (#65583, #64831), sweep worker cleanup (#60010), boolean sweep plot filters (#60774), tool-call deltas in `openai-responses` token counts (#62753), ASR stereo-duration filter (#65072, open) — outside what the skill documents.

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

## Content updates applied 2026-08-11 (freshen, v0.25.1 → v0.27.0)

Probes (12): `gh release list` (v0.27.0 latest, 2026-08-10) · `gh api contents/vllm/entrypoints/cli/benchmark?ref=v0.27.0` (subcommand list) · `.../benchmark/main.py` (Rust delegation gate) · `.../benchmark/serve.py` (entrypoint unchanged) · `.../vllm/envs.py` (`VLLM_USE_RUST_BENCH`) · `.../vllm/benchmarks/serve.py` at v0.27.0 **and** v0.25.1 (full argparse flag diff) · same file at v0.21.0/v0.24.0/v0.26.0 (`endpoint_type` history) · `.../lib/endpoint_request_func.py` at v0.25.1/v0.26.0/v0.27.0 (backend keys) · `.../requirements/common.txt` (dep floors) · `gh pr view 50081 / 49611 / 49223` · `gh issue view 32841` · WebFetch of the three `docs.vllm.ai` rows.

- **v0.25.1 → v0.27.0** across `SKILL.md`, `output-schema.md`, `troubleshooting.md`,
  `datasets.md`, `sources.md`. Every bumped claim was individually re-read at the
  v0.27.0 tag; nothing was extrapolated from the release notes.
- **`vllm bench serve` now has two implementations.** A Rust client shipped in
  `vllm-rs` (#48107, #48930), but #50081 made it **opt-in** — `VLLM_USE_RUST_BENCH=1`,
  resolved via `VLLM_RUST_FRONTEND_PATH`. Python stays the default because the two
  diverge on accepted arguments (underscore aliases, defaults, help text). Recorded
  in `commands.md` as a re-baseline trigger. The rendered docs do not mention it yet.
- **`--probe-request-rate`** (#49611) added to `commands.md` + the five `probe_*`
  JSON fields to `output-schema.md`. First native way to measure how a heavy
  workload stalls *unrelated* requests — it deliberately bypasses `--max-concurrency`.
- **BROKEN CLAIM CORRECTED — `endpoint_type` was never removed from the output JSON.**
  The 2026-04-24 pass wrote it out of `output-schema.md` and the 2026-07-21 pass
  "re-confirmed absent". Both were wrong: the line is unconditional at every tag from
  v0.21.0 to v0.27.0. Only the `--endpoint-type` **flag** is gone. The correction is
  left in the file as a visible note so a future pass does not re-delete the field.
- **Air-gap dep floor fixed:** `transformers>=4.45` → **`transformers >= 5.5.3`**, read
  from `requirements/common.txt`. The release notes' "Transformers 5.14.1" (#49223)
  is a `requirements/test/*` CI pin and was **not** applied as the runtime floor.
  Also `huggingface-cli download` → `hf download` (the old name now resolves to
  `huggingface_hub.cli.deprecated_cli:main`).
- **Two wrong value-set entries deleted:** `vllm-chat` removed from the `bench serve`
  `--backend` list (it is a `bench throughput` backend, and was absent from
  `ASYNC_REQUEST_FUNCS` at v0.25.1 too — so this was never version drift, just an
  error), and `bfcl` removed from the `--dataset-name` list in `datasets.md`
  (selected via `--dataset-path` + `--backend openai-chat` instead).
- **Reassuring negative result:** the complete argparse flag diff between v0.25.1 and
  v0.27.0 is **one addition, zero removals**. Every other flag this skill documents
  still exists at v0.27.0. `--num-warmups` default re-read as `0`, so "does not
  auto-warm" holds through v0.27.
- **#32841 hedge kept for the third cycle** — see the row above for the reasoning.
- **Still not probed:** the two blog rows and the performance-dashboard row. They keep
  their existing stamps rather than borrowing today's date.

## Content updates applied 2026-09-23 (release-note sweep, v0.30.0)

Verified against the local v0.29.0/v0.30.0 tags (`serve.py`, `endpoint_request_func.py`,
`throughput.py`, `lib/utils.py`) plus `gh pr view` on each PR body.

- **`SKILL.md`, `commands.md`, `output-schema.md`:** client-side queue time and
  `e2el_including_client_queue` percentiles (#54136); streaming TTFT/E2EL accounting
  fix, a re-baseline trigger (#55508); non-positive `--max-concurrency` now rejected
  (#54887); credentials (`--header`) redacted from printed args and saved metadata
  (#56662).
- **`output-schema.md`:** corrected the pooling (`EmbedBenchmarkMetrics`) field list —
  it was missing `completed`, `failed`, `total_input`, `total_input_sequences`,
  `input_sequence_throughput`, and the `e2el` percentile fields (pre-existing gap, not
  v0.30.0-specific). Also documented the v0.30.0 fix making pooling E2EL wait for the
  full response body, including the new `bytes_only` encoding format (#56760).
- **`troubleshooting.md`:** added a note that new post-upgrade failures on requests
  that streamed no valid chunk are the v0.30.0 fix working correctly (#55508), not a
  regression.
- **Not applied (cap):** `mm-processor` crash on `--dataset-name random-mm` fixed via
  `throughput.py`'s `_to_serve_args` reading legacy length/backend flags with `getattr`
  instead of direct attribute access (#56300) — confirmed by diff, but the skill never
  documented the crash, so there was nothing to fix and the 5-finding cap was already
  spent on higher-priority items.
- **Confirmed correctly silent:** HF ShareGPT multi-turn dataset loading (#51104,
  #56915) is Rust-bench-client-only per both PR bodies — the Python `vllm bench serve`
  this skill documents has no `--multi-turn` flag. No change needed.

