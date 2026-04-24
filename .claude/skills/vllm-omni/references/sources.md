# Sources

Citation anchors backing every claim in this skill. Use to verify — or to feed follow-up searches when a claim looks stale.

## First-party

| Ref | URL | Last verified |
|---|---|---|
| Repo | <https://github.com/vllm-project/vllm-omni> | 2026-04-24 |
| Docs root (canonical — **not** `vllm-omni.readthedocs.io`, that subdomain 302s / 403s) | <https://docs.vllm.ai/projects/vllm-omni/en/latest/> | 2026-04-18 |
| Supported models | <https://github.com/vllm-project/vllm-omni/blob/main/docs/models/supported_models.md> | 2026-04-18 |
| Architecture overview | <https://github.com/vllm-project/vllm-omni/blob/main/docs/design/architecture_overview.md> | 2026-04-18 |
| Serving endpoint docs | <https://github.com/vllm-project/vllm-omni/tree/main/docs/serving> | 2026-04-18 |
| Contact / community | <https://github.com/vllm-project/vllm-omni/blob/main/docs/community/contact_us.md> | 2026-04-18 |
| Feature docs (ComfyUI, Sleep mode, verl) | <https://github.com/vllm-project/vllm-omni/tree/main/docs/features> | 2026-04-18 |
| PyPI | <https://pypi.org/project/vllm-omni/> | 2026-04-18 |
| Docker Hub | <https://hub.docker.com/r/vllm/vllm-omni/tags> | 2026-04-18 |

## Paper

- arXiv abstract: <https://arxiv.org/abs/2602.02204>
- HTML mirror: <https://arxiv.org/html/2602.02204v1>
- Submitted 2026-02-02. Title: "vLLM-Omni: Fully Disaggregated Serving for Any-to-Any Multimodal Models". Up to 91.4% JCT reduction claim (baseline unspecified in abstract).

## Releases

| Release | Date | Notes | URL | Last verified |
|---|---|---|---|---|
| Release index | — | — | <https://github.com/vllm-project/vllm-omni/releases> | 2026-04-24 |
| v0.11.0rc1 | 2025-12-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.11.0rc1> | 2026-04-18 |
| v0.12.0rc1 | 2026-01-05 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.12.0rc1> | 2026-04-18 |
| v0.14.0 | 2026-01-31 | **First stable** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.14.0> | 2026-04-24 |
| v0.16.0 | 2026-02-28 | **rebased on vLLM v0.16.0** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.16.0> | 2026-04-24 |
| v0.17.0rc1 | 2026-03-09 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.17.0rc1> | 2026-04-24 |
| v0.18.0rc1 | 2026-03-21 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0rc1> | 2026-04-24 |
| v0.18.0 | 2026-03-28 | **current stable, rebased on vLLM v0.18.0** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0> | 2026-04-24 |
| v0.19.0rc1 | 2026-04-04 | **FLUX regression present in tag artifacts; fix merged to `main` 2026-04-24 via PR #2760 but not yet re-tagged — avoid until next RC ships** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.19.0rc1> | 2026-04-24 |

## Community

- Slack `#sig-omni`: <https://slack.vllm.ai>
- Forum: <https://discuss.vllm.ai>
  - Voxtral + omni thread: <https://discuss.vllm.ai/t/issues-with-voxtral-models-and-omni/2549>
- Weekly meeting: Tuesday 19:30 PDT (see 2025-11-30 launch blog)
- Launch blog (Nov 2025): <https://github.com/vllm-project/vllm-project.github.io/blob/main/_posts/2025-11-30-vllm-omni.md>
- Hong Kong Meetup 2026-03-07: <https://opensource.hk/vllm-hong-kong-meetup/>

## Third-party

- Community skills plugin: <https://github.com/hsliuustc0106/vllm-omni-skills>
- AIToolly coverage 2026-03-23: <https://aitoolly.com/ai-news/article/2026-03-23-vllm-omni-a-new-framework-for-efficient-omni-modality-model-inference-released-on-github>

## Key issues referenced

| # | Title | State | URL | Last verified |
|---|---|---|---|---|
| #2898 | NPU 910B install regression | OPEN | <https://github.com/vllm-project/vllm-omni/issues/2898> | 2026-04-18 |
| #2880 | HunyuanVideo-1.5 flash-attn shape on NPU mindiesd | OPEN | <https://github.com/vllm-project/vllm-omni/issues/2880> | 2026-04-24 |
| #2866 | Qwen3-TTS code2wav crash when enforce_eager=false | OPEN (active 2026-04-20) | <https://github.com/vllm-project/vllm-omni/issues/2866> | 2026-04-24 |
| #2804 | Diffusion API accepts model mismatch silently | **CLOSED 2026-04-19** | <https://github.com/vllm-project/vllm-omni/issues/2804> | 2026-04-24 |
| #2777 | v0.18 Pydantic ChatCompletionResponse validation bug | OPEN | <https://github.com/vllm-project/vllm-omni/issues/2777> | 2026-04-24 |
| #2768 | Orphan procs after Wan2.2 crash | OPEN | <https://github.com/vllm-project/vllm-omni/issues/2768> | 2026-04-24 |
| #2760 | [Bugfix] T5 text encoder to render correct text in FLUX.1-dev | **MERGED 2026-04-24** (closes #2730) | <https://github.com/vllm-project/vllm-omni/pull/2760> | 2026-04-24 |
| #2730 | FLUX.1-dev regression on v0.19.0rc1 | **CLOSED 2026-04-24** via PR #2760 — fix is on `main`, not yet in a tagged release | <https://github.com/vllm-project/vllm-omni/issues/2730> | 2026-04-24 |
| #2683 | mimo_audio online_serving bug | OPEN (not re-probed) | <https://github.com/vllm-project/vllm-omni/issues/2683> | 2026-04-18 |
| #2635 | BAGEL YAML / docs field name mismatch | OPEN (not re-probed) | <https://github.com/vllm-project/vllm-omni/issues/2635> | 2026-04-18 |
| #2595 | Qwen3-TTS max_model_len validation error | OPEN (not re-probed) | <https://github.com/vllm-project/vllm-omni/issues/2595> | 2026-04-18 |
| #2562 | Audio gaps on Qwen3-TTS streaming | OPEN (not re-probed) | <https://github.com/vllm-project/vllm-omni/issues/2562> | 2026-04-18 |

## Open RFCs (shape of roadmap)

- [#677 2026 Q1 Roadmap](https://github.com/vllm-project/vllm-omni/issues/677)
- [#938 Qwen3-TTS Production Ready milestone](https://github.com/vllm-project/vllm-omni/issues/938)
- [#984 Omni Coordinator](https://github.com/vllm-project/vllm-omni/issues/984)
- [#1217 Continuous Diffusion Model Acceleration Support](https://github.com/vllm-project/vllm-omni/issues/1217)
- [#765 SpargeAttn Sparse Attention Backend](https://github.com/vllm-project/vllm-omni/issues/765)

## Source-file anchors (code in the repo)

- `vllm_omni/config/model.py` — OmniModelConfig
- `vllm_omni/config/stage_config.py` — StageConfig YAML loader + pipeline validation
- `vllm_omni/engine/async_omni_engine.py` — AsyncOmniEngine
- `vllm_omni/engine/orchestrator.py` — multi-stage orchestrator
- `vllm_omni/engine/stage_engine_core_client.py` — per-stage engine client
- `vllm_omni/entrypoints/cli/serve.py` — `--omni` CLI interceptor
- `vllm_omni/entrypoints/openai/api_server.py` — OpenAI-compat server (854-2451)
- `vllm_omni/entrypoints/openai/realtime_connection.py` — `/v1/realtime` WebSocket
- `vllm_omni/entrypoints/openai/serving_speech.py` — `/v1/audio/speech`
- `vllm_omni/entrypoints/openai/serving_speech_stream.py` — `/v1/audio/speech/stream`
- `vllm_omni/distributed/omni_connectors/connectors/*.py` — connector implementations
- `vllm_omni/diffusion/` — DiT engine
- `vllm_omni/diffusion/cache/teacache/` + `cache_dit/` — DiT activation caches
- `vllm_omni/inputs/data.py:174-300` — OmniDiffusionSamplingParams
- `vllm_omni/quantization/factory.py:138-178` — unified quantization factory
- `vllm_omni/platforms/__init__.py:21-130` — platform auto-detect
- `vllm_omni/profiler/omni_torch_profiler.py` — profiler wrapper
- `vllm_omni/patch.py` — early-import patch registering OmniModelConfig
- `vllm_omni/version.py` — version resolution + vLLM alignment check
- `vllm_omni/model_executor/stage_configs/*.yaml` — reference stage configs
- `examples/online_serving/qwen3_omni/openai_realtime_client.py` — realtime client template
- `examples/online_serving/qwen3_omni/README.md` — realtime deployment notes
- `examples/online_serving/text_to_video/README.md` — video job API walkthrough

## Refresh policy

Refresh this skill when:

- A new stable release lands (watch for rebase onto newer upstream vLLM).
- A new model family joins the supported list — cross-check against current `supported_models.md`.
- A key issue in the reference list (Qwen3-TTS enforce-eager, FLUX regression, GLM-Image transformers pin) closes — those are the advice that directly affects operators.
- Paper gets updated / superseded.

Compiled 2026-04-18 against v0.18.0 stable. Last freshened 2026-04-24.
