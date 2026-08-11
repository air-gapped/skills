# Runner / task / convert flag migration — operator reference

Load when the question is about `--task` vs `--runner`, what replaces
`encode`, whether `--enable-scoring-api` exists, or when debugging
"why did my model load with the wrong endpoints".

## 1. The 2026 state

| Flag | Status | Replacement |
|---|---|---|
| `--runner {auto|generate|pooling|draft}` | **current, preferred** | — |
| `--convert {auto|none|embed|classify}` | **current** | — |
| `--pooler-config '{...}'` | **current** | — |
| `--task {generate|embed|score|classify|reward|encode|...}` | **removed** — not a CLI arg at v0.27.0 | `--runner` + `--convert` |
| `--enable-scoring-api` | **never existed** | auto per-model |

`--task` is gone, not merely warned about: at v0.27.0 there is no `task`
field in `ModelConfig` (`vllm/config/model.py`), no `--task` in
`vllm/engine/arg_utils.py`, and `docs/models/pooling_models/README.md`
documents only `--runner`/`--convert`. Passing it fails argument parsing.
The table in §2 is now a **migration table for old configs and old blog
posts**, not a description of two live spellings.

Runner types (`vllm/config/scheduler.py:21`):
`RunnerType = Literal["generate", "pooling", "draft"]`.

Pooling tasks (`vllm/tasks.py:8-15`):
`PoolingTask = Literal["embed", "classify", "token_embed", "token_classify", "plugin", "embed&token_classify"]`.

Score types (`vllm/tasks.py:18`):
`ScoreType = Literal["bi-encoder", "cross-encoder", "late-interaction"]`.

## 2. Translation table — old `--task` → new flags

| Old | New | When still needed |
|---|---|---|
| `--task generate` | (default, nothing) | — |
| `--task embed` | `--runner pooling` | — |
| `--task embed` (on a `*ForCausalLM`) | `--runner pooling --convert embed` | custom causal-LM checkpoints without a pooling head |
| `--task classify` | `--runner pooling` (or `--convert classify`) | — |
| `--task score` | `--runner pooling` (cross-encoder models auto-expose `/score` + `/rerank`) | — |
| `--task reward` | `--runner pooling --convert classify` | reward-model checkpoints |
| `--task encode` | `--runner pooling` (task split into `token_embed` and `token_classify` — pick explicit) | — |
| `--task transcription` | (default `generate`, the model's `SupportsTranscription` interface handles it) | — |

## 3. Deprecations — landed in v0.20.0 (2026-04-27)

From the v0.20.0 release notes and the pooling-models docs
(`docs/models/pooling_models/README.md`):

1. **`--task` flag** — replaced entirely by `--runner` + `--convert`. It was
   accepted with a deprecation warning in the v0.20 era; by v0.22.0 it was
   already absent from `arg_utils.py`, and it is still absent at v0.27.0.
2. **`score` pooling task** — replaced by `classify` + `num_labels==1`.
   Now hard-removed: `vllm/tasks.py:check_removed_pooling_task` raises
   `VLLMValidationError` for `score` and `encode` with the replacement named
   in the message.
3. **Pooling multitask support** — a model that supports multiple pooling
   tasks must now be served with an explicit pick, via
   `PoolerConfig(task=...)` (offline) or `--pooler-config.task <task>`
   (online). Automatic multitasking is gone.
4. **`encode` task** — split into `token_embed` and `token_classify`.
5. **`normalize` in `PoolingParams`** — removed; use `use_activation`.
6. **`logit_bias` / `logit_scale`** in `PoolerConfig` — renamed to
   `logit_mean` / `logit_sigma` in v0.20.0 (PR #39530, explicit breaking
   change in release notes). Old names work with a warning.
7. **Async scheduling OFF by default for pooling** (PR #39592, v0.20.0
   breaking). Stability over throughput; re-enable per-deployment if a
   previous v0.19 benchmark demonstrated a win.

## 4. How the runner + convert combination resolves

Resolution order (`vllm/config/model.py:525-547`):

1. Read `--runner`. If `auto`, check the registry:
   - If the architecture is in the pooling-model registry
     (`registry.is_pooling_model(arch, config)`) → `pooling`.
   - Else if in text-generation registry → `generate`.
   - Else default to `generate`.
2. Read `--convert`. If `auto`:
   - For pooling runner on a generative LM: auto-apply `embed` converter.
   - Otherwise no conversion.
3. Read `--pooler-config` and merge into the resolved `PoolerConfig`.

Converters (`_RUNNER_CONVERTS` in `vllm/config/model.py:95-99`):

- `embed` — attaches a pool head (default LAST for causal LMs, configurable).
- `classify` — attaches a classification head (requires labels info).

## 5. Pooling runner under the hood

- **CUDA graphs**: PIECEWISE mode (not full graphs). Pooling outputs have
  variable shape; full-graph mode wouldn't capture them cleanly.
- **Async scheduling**: disabled by default for pooling (PR #39592,
  merged 2026-04-12). Sync scheduling is more stable; async was too racy
  for pooling workloads.
- **Sequence scheduling**: no decode phase; the "request" is a single
  forward. Continuous batching still applies.
- **Prefix caching**: works (cross-request prefix reuse helps large-doc
  embedding). Chunked prefill: works.

## 6. When the scoring API auto-enables

`vllm/entrypoints/pooling/utils.py:140-154` — `enable_scoring_api()` gates
`/score` + `/rerank` endpoint registration. Active if the model's pooler
reports any of:

- `classify` in supported tasks AND `num_labels == 1` → cross-encoder.
- `embed` in supported tasks → bi-encoder.
- `token_embed` in supported tasks → late-interaction.

That's it. If the endpoints aren't live, check:

1. Is `--runner pooling` set?
2. Does the model's `Pooler.get_supported_tasks()` include one of the
   three tasks above? For custom checkpoints, may need `--convert classify`
   and explicit `num_labels`.

## 7. Common flag mistakes

1. **`--task embed --runner pooling`** — the whole command fails: `--task`
   is no longer a recognised argument. Set only `--runner`.
2. **`--enable-scoring-api`** — doesn't exist. Don't pass it.
3. **`--runner pooling` on a generate-only model** — serve fails with
   "no pooling support"; fix with `--convert embed` (or accept that the
   model needs `/v1/chat/completions` instead).
4. **`--convert embed` without `--runner pooling`** — has no effect; the
   converter is gated on pooling runner.
5. **`--pooler-config '{"task":"score"}'`** — `score` is a removed task
   name and now raises `VLLMValidationError`. Use `"task":"classify"` with
   `num_labels==1`, or drop it entirely (auto-detect). Same for `encode`.

## 8. Debugging a misrouted model

Symptoms and fixes:

| Symptom | Likely cause | Fix |
|---|---|---|
| `/v1/embeddings` returns 404 | runner is `generate` | `--runner pooling` |
| `/rerank` returns 404 | model's pooler doesn't report `classify`/`embed`/`token_embed` | check `--convert` and model's `supported_tasks` |
| Embeddings look random | wrong `pooling_type` | override via `--pooler-config '{"pooling_type":"MEAN"}'` (or CLS/LAST/ALL per model) |
| Pool outputs garbled | loaded as `generate` + `--convert embed` auto-failed | explicit `--runner pooling --convert embed` |
| `dimensions=N` returns 400 | model doesn't declare Matryoshka | `--hf-overrides '{"is_matryoshka": true}'` or accept the model doesn't support MRL |

## 9. Source anchors

- `vllm/config/scheduler.py:21` — `RunnerType`
- `vllm/config/model.py:95-124` — `_RUNNER_CONVERTS`, `--runner`/`--convert` CLI
- `vllm/config/model.py:525-547` — runner resolution
- `vllm/config/pooler.py` — `PoolerConfig` schema
- `vllm/entrypoints/pooling/factories.py:38-100` — IO processor registry
- `vllm/entrypoints/pooling/utils.py:140-154` — scoring API auto-enable
- `vllm/tasks.py:5-18` — `GenerationTask`, `PoolingTask`, `ScoreType` enums
- Docs: `docs/models/pooling_models/README.md`

## 10. Recent PRs worth knowing (all merged, all shipped in v0.20.0)

- **#34539** (merged 2026-03-31) — Generative Scoring (experimental):
  scoring via generate path, for models without a classify head.
- **#38559** — mean-pooling optimisation (+5.9%).
- **#39113** — redundant-sync removal for pooling (+3.7% throughput, per
  v0.20.0 release notes).
- **#39530** (merged 2026-04-13) — `logit_bias`/`logit_scale` →
  `logit_mean`/`logit_sigma`. **Breaking** (old names accepted with
  warning).
- **#39592** (merged 2026-04-12) — disable async scheduling by default
  for pooling. **Breaking.**
- **#39675** — refactor pooling entrypoints (cleanup).
- **#39763** — pre/post-processing offloaded to thread pool (async
  rendering for pooling).

## 11. Model Runner V2 and the pooling runner (v0.26.0 → v0.27.0)

MRV2 grew a pooling path across two releases: encoder-only attention
(#49331), sequence `embed` + `classify` pooling (#48791), `token_classify`
(#50293), `token_embed` (#50574), and BGE-M3's combined
`embed&token_classify` (#50661). Encoder-only pooling is complete for every
in-tree pooling task as of #50661.

**It is not the default for pooling.** `VLLM_USE_V2_MODEL_RUNNER` defaults to
`None` ("use config defaults", `vllm/envs.py`), and
`VllmConfig._is_default_v2_model_runner_model` returns `False` for any
`runner_type != "generate"` at v0.27.0. The PR that would flip pooling models
to V2 by default (#48290) is still **open**. So a pooling deployment behaves
exactly as before unless the operator opts in.

If you do opt in with `VLLM_USE_V2_MODEL_RUNNER=1`:

- Token-wise tasks (`token_embed`, `token_classify`) are enabled **only for
  encoder-only models** — `PoolingRunner._get_enabled_tasks` subtracts them
  for anything else, so decoder-backbone late-interaction models are rejected.
- An unsupported selection fails at startup with `Model Runner V2 supports
  pooling tasks [...], but this model selects '<task>'`, and the error itself
  names the escape hatch: **`VLLM_USE_V2_MODEL_RUNNER=0`**.
- Source: `vllm/v1/worker/gpu/pool/pooling_runner.py`.

Last verified: 2026-08-11 against vLLM v0.27.0 source. Two real changes since
v0.25.1: `--task` is **gone from the CLI** (and the `score` / `encode` task
names raise `VLLMValidationError`), and MRV2 gained an opt-in pooling path.
The `--runner` / `--convert` / `--pooler-config` surface itself is still
unchanged since v0.20.0. Flag stability is not surface stability — v0.24.0
tightened request validation (#46313, #46119) and v0.26.0 fixed a pooling
*correctness* bug (#48901) without touching a single flag.
