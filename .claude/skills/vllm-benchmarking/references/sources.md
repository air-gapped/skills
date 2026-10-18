# External sources — verification log

Freshened: 2026-10-18 — every row probed at v0.32.0 (all URLs 200, 25 issue/PR states batched, serve.py flags/JSON keys diffed v0.30.0→v0.32.0: no change). Moved: `sonnet` dataset removed (13 `--dataset-name` values), `openai-responses` backend added (13 backends), sweep `--warmup-num-prompts`/`--continue-on-error`, `transformers >= 5.16.1, < 5.20.0` + `tokenizers >= 0.23.2`; corrected long-standing `--metric-percentiles`/`--percentile-metrics` defaults and sweep sub-mode names.

**Freshened: 2026-09-15** — all 15 rows probed. Every URL 200s with no redirect drift, and every claim pinned to tag `v0.27.0` was re-read at that tag and holds exactly (`serve.py` 2363 lines, `BenchmarkMetrics` L321, `sonnet.txt` 22706 bytes, six bench subcommands, `transformers >= 5.5.3`). The docs still lag the tree on `VLLM_USE_RUST_BENCH` and still list `sonnet` as the only deprecated dataset. One row drifted: current stable is **v0.29.0** (2026-09-09) via v0.28.0, not v0.27.1.

Tracks external references cited in this skill. `Last verified` indicates the most recent date an agent confirmed the URL resolves, the content still exists, and (where relevant) the claim the skill makes about it is still accurate. Stale dates mean: re-probe before trusting cited specifics.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM bench CLI docs | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-10-18 | 200 OK. `sonnet` is gone from the page (removed in v0.32.0) and no dataset is flagged deprecated any more. Documents the `openai-responses` backend (Responses API benchmark section, incl. the `include_reasoning: false` TTFT warning). Its "all sampling flags except `--min-p`" sentence is stale: #48084 removed that rejection in v0.32.0 code. Still no mention of `VLLM_USE_RUST_BENCH`; `commands.md` is source-verified instead. |
| `vllm bench serve` reference | https://docs.vllm.ai/en/latest/cli/bench/serve/ | 2026-10-18 | 200 OK. `--endpoint-type` absent. `--num-warmups` default **0**. `--backend` choices = 13 entries incl. `openai-responses`; `vllm-chat` not among them. `--dataset-name` choices = 13 (no `sonnet`), default `random` — identical to the v0.32.0 argparse source. |
| vLLM env vars (`VLLM_USE_MODELSCOPE` etc.) | https://docs.vllm.ai/en/latest/configuration/env_vars/ | 2026-10-18 | 200 OK. `VLLM_USE_MODELSCOPE`, `VLLM_USE_RUST_BENCH`, `VLLM_USE_RUST_FRONTEND`, `VLLM_RUST_FRONTEND_PATH` all documented. `HF_ENDPOINT` not listed here (upstream huggingface_hub var, honored transparently). |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-10-18 | **v0.32.0 is current stable** (2026-10-18, `isLatest`), via v0.31.0 (2026-10-05) and v0.30.0 (2026-09-22). Skill text re-verified at the **v0.32.0** tag. Benchmark-surface changes in the two hops: v0.31.0 — `openai-responses` backend (#54628), `model_id` in latency/throughput JSON (#58112), transformers upper bound (#59614); v0.32.0 — `sonnet` removed (#60129), `bench throughput --dataset` removed (#60923), sweep `--warmup-num-prompts`/`--continue-on-error` (#57305), Responses `min_p` accepted (#48084), `transformers>=5.16.1,<5.20.0` + `tokenizers>=0.23.2` (#57387, #59796). The Rust-frontend-only `mm-processor` benchmark (v0.31.0, #51922) does not change the Python `vllm bench mm-processor` this skill documents. |
| `vllm-project/vllm#32841` (ModelScope LoRA) | https://github.com/vllm-project/vllm/issues/32841 | 2026-10-18 | **CLOSED / COMPLETED** 2026-01-23, still **zero comments**, no linked fix PR. Neither "fixed" nor "stale" is supported, so the skill's hedge ("historical gap; re-verify on your vLLM version") is **kept deliberately**. Do not delete it on the strength of `stateReason: COMPLETED`. |
| `vllm/benchmarks/serve.py` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/benchmarks/serve.py | 2026-10-18 | Read at tag **v0.32.0**: **2410 lines** (2425 at v0.30.0). `BenchmarkMetrics` **L328**, `EmbedBenchmarkMetrics` L363, `result_json["date"]` **L2258**, `endpoint_type` backward-compat alias L2259. **Argparse flag diff v0.30.0 → v0.32.0: zero additions, zero removals**; JSON key set unchanged. `--num-warmups` default **0**; `--percentile-metrics` default `None` → `ttft,tpot,itl` (generative) / `e2el` (pooling); `--metric-percentiles` default **`"99"`** (same at v0.27.0 and v0.30.0 — the skill previously misdescribed both defaults). `--max-concurrency <= 0` raises at L2009. |
| `vllm/entrypoints/cli/benchmark/` + `vllm/envs.py` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/entrypoints/cli/benchmark/main.py | 2026-10-18 | At v0.32.0: six subcommands unchanged (serve, throughput, latency, sweep, startup, mm-processor). `maybe_exec_rust_bench()` still fires only when `sys.argv[1:3] == ["bench","serve"]` **and** `VLLM_USE_RUST_BENCH` is truthy, then `os.execv`s `VLLM_RUST_FRONTEND_PATH`. `envs.py` L170-172 declares `VLLM_USE_RUST_FRONTEND`/`VLLM_USE_RUST_BENCH` (default `False`) and `VLLM_RUST_FRONTEND_PATH` (default `"auto"`). Python is the default path. |
| `requirements/common.txt` (runtime dep floors) | https://github.com/vllm-project/vllm/blob/v0.32.0/requirements/common.txt | 2026-10-18 | v0.32.0: **`transformers >= 5.16.1, < 5.20.0`**, **`tokenizers >= 0.23.2`**, `huggingface_hub >= 1.31.0`. v0.31.0: `transformers >= 5.10.4, < 5.18.0`, `tokenizers >= 0.21.1`. v0.30.0: `transformers >= 5.10.4` (no upper bound). v0.27.0: `>= 5.5.3`. Release-note "Transformers 5.x" bumps in `requirements/test/*` (#49223, #59621, #60381) are CI pins, not runtime floors. |
| `vllm bench` dataset table (rendered docs) | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-10-18 | 13 `--dataset-name` values at v0.32.0 (14 through v0.31.x; `sonnet` removed by #60129), cross-checked against `add_dataset_parser` choices in `vllm/benchmarks/datasets/datasets.py` (L1593) — identical between docs and source. `bfcl` is **not** a `--dataset-name` value (selected via `--dataset-path`/`--hf-name` + `--backend openai-chat`). `bench throughput` keeps its own 8-value list (`throughput.py` L785). |
| `benchmarks/sonnet.txt` (removed) | https://github.com/vllm-project/vllm/pull/60129 | 2026-10-18 | **Removed in v0.32.0** by #60129 (merged 2026-10-06): deletes `benchmarks/sonnet.txt`, `SonnetDataset`, the `sonnet` choice and `--sonnet-input-len/--sonnet-output-len/--sonnet-prefix-len`. The file still exists at the v0.27.0–v0.31.0 tags (https://github.com/vllm-project/vllm/blob/v0.27.0/benchmarks/sonnet.txt, 200). |
| In-tree benchmarks dir | https://github.com/vllm-project/vllm/tree/v0.32.0/vllm/benchmarks | 2026-10-18 | Contents at v0.32.0 unchanged from v0.27.0: `datasets/`, `lib/`, `sweep/`, `latency.py`, `mm_processor.py`, `plot.py`, `serve.py`, `startup.py`, `throughput.py`. `sweep/` sub-modes by `parser_name`: `serve`, `serve_workload`, `startup`, `plot`, `plot_pareto` (underscores; argparse does not normalize positional names). `sweep serve`/`serve_workload` gained `--warmup-num-prompts` (default 0) and `--continue-on-error` in v0.32.0 (#57305, merged 2026-09-30). |
| Air-gapped discussion thread | https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916 | 2026-10-18 | 200 OK, live. |
| vLLM performance dashboard | https://docs.vllm.ai/en/latest/benchmarking/dashboard/ | 2026-10-18 | 200 OK, live. |
| Blog: Anatomy of a High-Throughput LLM Inference System (2025-09-05) | https://vllm.ai/blog/2025-09-05-anatomy-of-vllm | 2026-10-18 | 200 OK. blog.vllm.ai 301s here; SKILL.md now cites this canonical URL. |
| Blog: Large Scale Serving — DeepSeek @ 2.2k tok/s/H200 (2025-12-17) | https://vllm.ai/blog/2025-12-17-large-scale-serving | 2026-10-18 | 200 OK. blog.vllm.ai 301s here; SKILL.md now cites this canonical URL. |
| `vllm-project/vllm#54136` (client queue time) | https://github.com/vllm-project/vllm/pull/54136 | 2026-10-18 | MERGED 2026-09-01. Still present at v0.32.0: `client_queue_time` recorded (`serve.py` L984), unconditional `latencies`/`queue_times`; `--percentile-metrics` help lists `client_queue_time`/`e2el_including_client_queue`. |
| `vllm-project/vllm#55508` (streaming TTFT/E2EL accounting fix) | https://github.com/vllm-project/vllm/pull/55508 | 2026-10-18 | MERGED 2026-09-13, shipped v0.30.0. Still present at v0.32.0 (`endpoint_request_func.py`: "Never received a valid chunk to calculate TTFT." failure path). Re-baseline trigger for streaming-endpoint numbers across v0.29.0→v0.30.0. |
| `vllm-project/vllm#54887` (reject non-positive `--max-concurrency`) | https://github.com/vllm-project/vllm/pull/54887 | 2026-10-18 | MERGED 2026-09-04, shipped v0.30.0. Check still at v0.32.0 `serve.py` L2009. |
| `vllm-project/vllm#56760` (complete pooling responses measured) | https://github.com/vllm-project/vllm/pull/56760 | 2026-10-18 | MERGED 2026-09-15, shipped v0.30.0. Still at v0.32.0: pooling bodies drained via `iter_any()`, `bytes_only` handled (`endpoint_request_func.py` L818-828). |
| `vllm-project/vllm#56662` (credentials redacted from benchmark logs) | https://github.com/vllm-project/vllm/pull/56662 | 2026-10-18 | MERGED 2026-09-14, shipped v0.30.0. At v0.32.0: `redact_sensitive_namespace()` in `vllm/benchmarks/lib/utils.py`; `_SENSITIVE_ARG_FIELDS = ("header",)` lives in `serve.py` (L66), applied to the printed arg namespace (L2008) and the PyTorch-benchmark-format args (L1532). |
| `vllm-project/vllm#54628` + `#48084` (Responses API backend) | https://github.com/vllm-project/vllm/pull/54628 | 2026-10-18 | #54628 MERGED 2026-09-28, shipped v0.31.0: `openai-responses` in `ASYNC_REQUEST_FUNCS`, docs section in `docs/benchmarking/cli.md` (reasoning deltas count toward TTFT/ITL; stream without terminal `response.completed` = failed; `include_reasoning: false` warning). v0.31.0 `serve.py` raised `ValueError` for `--min-p` with this backend; #48084 (https://github.com/vllm-project/vllm/pull/48084, MERGED 2026-10-08, v0.32.0) removed that check. |
| `vllm-project/vllm#60923` (scheduled deprecations removed) | https://github.com/vllm-project/vllm/pull/60923 | 2026-10-18 | MERGED 2026-10-10, shipped v0.32.0: removes `vllm bench throughput --dataset` (use `--dataset-path`). |
| `vllm-project/vllm#58112` (`model_id` in latency/throughput JSON) | https://github.com/vllm-project/vllm/pull/58112 | 2026-10-18 | MERGED 2026-09-25, shipped v0.31.0: `"model_id": args.model` in `latency.py` L173 and `throughput.py` L1119 at v0.32.0. |

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

