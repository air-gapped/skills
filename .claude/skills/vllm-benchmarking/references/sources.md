# External sources — verification log

Tracks external references cited in this skill. `Last verified` indicates the most recent date an agent confirmed the URL resolves, the content still exists, and (where relevant) the claim the skill makes about it is still accurate. Stale dates mean: re-probe before trusting cited specifics.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM bench CLI docs | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-08-11 | 200 OK. `sonnet` still the **only** dataset flagged deprecated. Page makes no mention of `VLLM_USE_RUST_BENCH` or the Rust bench client — docs lag the v0.27.0 tree here; `commands.md` is source-verified instead. |
| `vllm bench serve` reference | https://docs.vllm.ai/en/latest/cli/bench/serve/ | 2026-08-11 | 200 OK. `--endpoint-type` still absent. `--num-warmups` default still **0**. `--probe-request-rate` now documented. Backend value set = 12 entries, and **`vllm-chat` is not among them** (the skill previously listed it in error; it is a `bench throughput` backend). |
| vLLM env vars (`VLLM_USE_MODELSCOPE` etc.) | https://docs.vllm.ai/en/latest/configuration/env_vars/ | 2026-08-11 | 200 OK. `VLLM_USE_MODELSCOPE` still documented. **New and in scope:** `VLLM_USE_RUST_BENCH` ("If set, use the packaged Rust client for `vllm bench serve`"), `VLLM_USE_RUST_FRONTEND`, `VLLM_RUST_FRONTEND_PATH` (defaults `auto`). `HF_ENDPOINT` still not listed here (upstream huggingface_hub var, honored transparently). |
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-08-11 | **v0.27.1 is current stable** (published 2026-08-11 10:47Z) — a patch on v0.27.0 whose sole change is "Support quantized DSpark Markov heads" (#50424), which touches no benchmarking surface. Two minors plus a patch since the last stamp: v0.26.0 (2026-07-27), v0.27.0 (2026-08-10), v0.27.1. Skill text is baselined and source-verified at the **v0.27.0** tag, which remains valid for every claim here. The `v0.27.1` container images were pushed 10:24-10:42Z, *before* the 10:47Z release — image availability, not the PyPI wheel, gates this stack. |
| `vllm-project/vllm#32841` (ModelScope LoRA) | https://github.com/vllm-project/vllm/issues/32841 | 2026-08-11 | **CLOSED / COMPLETED** 2026-01-23, still **zero comments** — unchanged from the 2026-07-21 probe. Stale-close check re-run: not bot-closed (no comments at all), but still no linked fix PR and no closing rationale. Neither "fixed" nor "stale" is supported, so the skill's hedge ("historical gap; re-verify on your vLLM version") is **kept deliberately** for the third cycle running. Do not delete it on the strength of `stateReason: COMPLETED`. |
| `vllm/benchmarks/serve.py` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/benchmarks/serve.py | 2026-08-11 | Read at tag **v0.27.0**: **2363 lines** (was 2284 at v0.25.1). `BenchmarkMetrics` **L321**, `EmbedBenchmarkMetrics` L356, JSON assembly **~L2206-2217**. **Full argparse flag diff v0.25.1 → v0.27.0: exactly one addition (`--probe-request-rate`), zero removals** — so every flag this skill documents still exists. `--num-warmups` default re-read: still **0**. **Correction:** `endpoint_type` **is** emitted (`result_json["endpoint_type"] = args.backend  # for backward compatibility`) — confirmed present at v0.21.0, v0.24.0, v0.25.1, v0.26.0 and v0.27.0. The prior "removed" claim was wrong at the time it was written. |
| `vllm/entrypoints/cli/benchmark/` + `vllm/envs.py` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/entrypoints/cli/benchmark/main.py | 2026-08-11 | Six subcommands unchanged (serve, throughput, latency, sweep, startup, mm-processor). `maybe_exec_rust_bench()` fires only when `sys.argv[1:3] == ["bench","serve"]` **and** `VLLM_USE_RUST_BENCH` is truthy, then `os.execv`s `VLLM_RUST_FRONTEND_PATH`. `envs.py` L156-158 declares `VLLM_USE_RUST_FRONTEND`/`VLLM_USE_RUST_BENCH` (both default `False`) and `VLLM_RUST_FRONTEND_PATH` (default `"auto"`). Python is the default path. |
| `requirements/common.txt` (runtime dep floors) | https://github.com/vllm-project/vllm/blob/v0.27.0/requirements/common.txt | 2026-08-11 | Runtime floor is **`transformers >= 5.5.3`** at v0.27.0. Note: the "Transformers 5.14.1" figure in the v0.27.0 release notes (#49223) touches only `requirements/test/*` — it is a **CI pin, not the runtime floor**. Air-gap staging lists must satisfy 5.5.3, not 4.45. |
| `vllm bench` dataset table (rendered docs) | https://docs.vllm.ai/en/latest/benchmarking/cli/ | 2026-08-11 | Dataset set unchanged since 2026-05-28. Cross-checked against argparse `choices` in the v0.27.0 tree — 14 values, identical between docs and source. `bfcl` is **not** a `--dataset-name` value (selected via `--dataset-path`/`--hf-name` + `--backend openai-chat`); `datasets.md` corrected. |
| `vllm/benchmarks/sonnet.txt` | https://github.com/vllm-project/vllm/blob/v0.27.0/benchmarks/sonnet.txt | 2026-08-11 | 22,706 bytes at v0.27.0 — unchanged, still in tree. Dataset still marked deprecated in docs; file remains, so the air-gapped "never downloads" claim holds. |
| In-tree benchmarks dir | https://github.com/vllm-project/vllm/tree/v0.27.0/vllm/benchmarks | 2026-08-11 | Contents at v0.27.0: `datasets/`, `lib/`, `sweep/`, `latency.py`, `mm_processor.py`, `plot.py`, `serve.py`, `startup.py`, `throughput.py`. `sweep/` still carries all five documented sub-modes (serve, serve_workload, startup, plot, plot_pareto). |
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

