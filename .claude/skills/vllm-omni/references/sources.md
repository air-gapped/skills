# Sources

Citation anchors backing every claim in this skill. Use to verify — or to feed follow-up searches when a claim looks stale.

## First-party

| Ref | URL | Last verified |
|---|---|---|
| Repo | <https://github.com/vllm-project/vllm-omni> | 2026-07-21 |
| Docs root (canonical — **not** `vllm-omni.readthedocs.io`, that subdomain 302s / 403s) | <https://docs.vllm.ai/projects/vllm-omni/en/latest/> | 2026-04-18 |
| Supported models | <https://github.com/vllm-project/vllm-omni/blob/main/docs/models/supported_models.md> | 2026-04-18 |
| Architecture overview | <https://github.com/vllm-project/vllm-omni/blob/main/docs/design/architecture_overview.md> | 2026-04-18 |
| Serving endpoint docs | <https://github.com/vllm-project/vllm-omni/tree/main/docs/serving> | 2026-04-18 |
| Contact / community | <https://github.com/vllm-project/vllm-omni/blob/main/docs/community/contact_us.md> | 2026-04-18 |
| Feature docs (ComfyUI, Sleep mode, verl) | <https://github.com/vllm-project/vllm-omni/tree/main/docs/features> | 2026-04-18 |
| PyPI (`info.version` = **0.24.0** @ 2026-07-21; **0.24.1 absent** — see channel-mismatch table) | <https://pypi.org/project/vllm-omni/> | 2026-07-21 |
| Docker Hub (newest versioned tag **v0.24.0**; `latest` -> v0.24.0; no v0.24.1 image) | <https://hub.docker.com/r/vllm/vllm-omni/tags> | 2026-07-21 |

## Paper

- arXiv abstract: <https://arxiv.org/abs/2602.02204>
- HTML mirror: <https://arxiv.org/html/2602.02204v1>
- Submitted 2026-02-02. Title: "vLLM-Omni: Fully Disaggregated Serving for Any-to-Any Multimodal Models". Up to 91.4% JCT reduction claim (baseline unspecified in abstract).

## Releases

| Release | Date | Notes | URL | Last verified |
|---|---|---|---|---|
| Release index | — | — | <https://github.com/vllm-project/vllm-omni/releases> | 2026-05-28 |
| v0.11.0rc1 | 2025-12-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.11.0rc1> | 2026-04-18 |
| v0.12.0rc1 | 2026-01-05 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.12.0rc1> | 2026-04-18 |
| v0.14.0 | 2026-01-31 | **First stable** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.14.0> | 2026-04-24 |
| v0.16.0 | 2026-02-28 | **rebased on vLLM v0.16.0** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.16.0> | 2026-04-24 |
| v0.17.0rc1 | 2026-03-09 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.17.0rc1> | 2026-04-24 |
| v0.18.0rc1 | 2026-03-21 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0rc1> | 2026-04-24 |
| v0.18.0 | 2026-03-28 | rebased on vLLM v0.18.0 (former stable) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0> | 2026-05-28 |
| v0.19.0rc1 | 2026-04-04 | **FLUX.1-dev regression present in tag artifacts (#2730); fix shipped in v0.20.0 (PR #2760) — avoid this specific tag** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.19.0rc1> | 2026-05-28 |
| v0.20.0rc1 | 2026-05-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0rc1> | 2026-05-28 |
| v0.20.0 | 2026-05-07 | **current stable, rebased on upstream vLLM v0.20.0 (CUDA 13.0 / PyTorch 2.11); release notes: removal of old vLLM entrypoint hijack + 0.20.0 integration path (#3232/#3082/#3352/#3393/#2306), Transformers 5.x compat, TTS CUDA-graph capture (#2690/#2758/#2803), FLUX T5 fix (#2760)** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0> | 2026-05-28 |
| v0.21.0rc1 | 2026-05-25 | **rc only — no v0.21.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.21.0rc1> | 2026-07-21 |
| v0.22.0rc1 | 2026-06-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0rc1> | 2026-07-21 |
| v0.22.0 | 2026-06-06 | stable, aligned to vLLM 0.22 line. 339 commits / 124 contributors. **Cosmos3 world-model day-0 support** (#3454, #4073, #4102), DreamZero + OpenPI robot serving (#2162, #3673), `OmniCoordinator` integrated into the stage engine pipeline (#3569), broad quantization expansion (W4A16 autoround, MXFP4/MXFP8, ModelOpt mixed FP8/NVFP4, ROCm AITER, XPU, Ascend NPU) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0> | 2026-07-21 |
| v0.23.0rc1 | 2026-06-14 | **rc only — no v0.23.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.23.0rc1> | 2026-07-21 |
| v0.24.0rc1 | 2026-06-30 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0rc1> | 2026-07-21 |
| v0.24.0 | 2026-07-06 | stable, rebased on vLLM v0.23.0 + v0.24.0 (#4286, #4709). 285 commits / 112 contributors. **Newest version available as a wheel and as a container.** Omni stage runtime + distributed replica control-plane refactor (#3855), diffusion **request-level batching** (#4079), async output materialization (#4476), orchestrator output-path split (#4527), HF-config-based pipeline resolution (#3760), structured `VllmOmniConfig` (#4425). Speech hardening: SSE audio streaming, word-level timestamps, cross-request audio-corruption fix (#4034, #4490, #4706) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0> | 2026-07-21 |
| **v0.24.1** | 2026-07-10 | **Current GitHub "Latest" — but published to NO other channel.** Single PR #5017: restores `vllm_c` IR op priority and `torch.nn.RMSNorm` for Qwen-Image, fixing the perf regression in issue #4964 | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.1> | 2026-07-21 |
| v0.25.0rc1 | 2026-07-12 | latest pre-release | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.25.0rc1> | 2026-07-21 |

### Distribution-channel mismatch — verified 2026-07-21

The three channels disagree, and GitHub's "Latest" badge is the outlier. Check
all three before quoting a version for this project.

| Channel | Newest | Evidence |
|---|---|---|
| GitHub releases | **v0.24.1** (2026-07-10) | `gh release list -R vllm-project/vllm-omni` |
| PyPI | **0.24.0** (2026-07-07) | `pypi.org/pypi/vllm-omni/json` — full release index is `0.11.0rc1, 0.12.0rc1, 0.14.0, 0.14.0rc1, 0.16.0, 0.18.0, 0.18.0rc1, 0.20.0, 0.20.0rc1, 0.21.0rc1, 0.22.0, 0.23.0rc1, 0.24.0, 0.24.0rc1, 0.25.0rc1`. **`0.24.1` is absent entirely** — not yanked, never uploaded. |
| Docker Hub | **v0.24.0** (2026-07-07), and `latest` resolves to it | Docker Hub v2 tags API. Per-tag `-x86_64` / `-aarch64` variants exist. A `cosmos3` tag (2026-07-20) is newer than any versioned tag — a model-specific build, not a release. |

Consequence: the Qwen-Image regression fix in v0.24.1 is **not** reachable via
`pip install vllm-omni` or `vllm/vllm-omni:latest`. Use
`git+https://github.com/vllm-project/vllm-omni@v0.24.1`.

Note v0.22.0's release notes list "PyPI upload support" (#3667) as a *new*
capability for that release, which is consistent with the channel plumbing
still being immature — a reason to keep re-checking rather than assume parity.

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
| #4964 | Qwen-Image performance degradation (nightly CI) | **CLOSED 2026-07 — genuinely fixed** by PR #5017, shipped **v0.24.1 only** (not on PyPI/Docker) | <https://github.com/vllm-project/vllm-omni/issues/4964> | 2026-07-21 |
| #2898 | NPU 910B install regression | **CLOSED 2026-04-20 — answered, not patched.** Resolution is a usage correction: `--dtype`, `--max-model-len`, `--served-model-name` etc. "can't be passed correctly currently, because omni is multi-stage deployment", so set them in the **YAML stage config** instead of on the CLI | <https://github.com/vllm-project/vllm-omni/issues/2898> | 2026-07-21 |
| #2880 | HunyuanVideo-1.5 flash-attn shape on NPU mindiesd | **CLOSED 2026-06-02**, `COMPLETED`. Last comment is a maintainer ping (`@gcanlin PTAL`, 2026-04-20) with no fix reference — **fix unconfirmed**, re-test before relying on it | <https://github.com/vllm-project/vllm-omni/issues/2880> | 2026-07-21 |
| #2866 | Qwen3-TTS code2wav crash when enforce_eager=false | **CLOSED 2026-04-29** (CUDA-graph capture shipped via PR #2690 in v0.20.0) | <https://github.com/vllm-project/vllm-omni/issues/2866> | 2026-05-28 |
| #2804 | Diffusion API accepts model mismatch silently | **CLOSED 2026-04-19** | <https://github.com/vllm-project/vllm-omni/issues/2804> | 2026-04-24 |
| #2777 | v0.18 Pydantic ChatCompletionResponse validation bug | **still OPEN.** Last comment asks the reporter to re-check against the latest version per issue #4610 | <https://github.com/vllm-project/vllm-omni/issues/2777> | 2026-07-21 |
| #2768 | Orphan procs after Wan2.2 crash | **CLOSED 2026-05-16 `COMPLETED` — but treat as UNRESOLVED.** The last comment (2026-05-12, four days before closure) is a **fresh reproduction by a different reporter** — *"When I kill the serve process … the same bug occurred."* No fix PR referenced. Keep the process-group mitigation | <https://github.com/vllm-project/vllm-omni/issues/2768> | 2026-07-21 |
| #2760 | [Bugfix] T5 text encoder to render correct text in FLUX.1-dev | **MERGED 2026-04-24** (closes #2730); shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/2760> | 2026-05-28 |
| #2730 | FLUX.1-dev regression on v0.19.0rc1 | **CLOSED 2026-04-24** via PR #2760 — **fixed in v0.20.0 stable** | <https://github.com/vllm-project/vllm-omni/issues/2730> | 2026-05-28 |
| #2690 | [Perf] Speedup VoxCPM2 TTS + PagedAttention | **MERGED 2026-04-13**; shipped in v0.20.0 (lifts the Qwen3-TTS enforce-eager requirement) | <https://github.com/vllm-project/vllm-omni/pull/2690> | 2026-05-28 |
| #3232 | [Rebase] Rebase to vllm 0.20.0 | **MERGED 2026-04-29**; shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/3232> | 2026-05-28 |
| #2683 | mimo_audio online_serving bug | **CLOSED 2026-04-20**, `COMPLETED`. Last comment root-causes it in the online input processor (`llm2code2wav` in `stage_input_processors/mimo_audio.py` flattens the full stage-0 talker output, ~36 ids per frame) — **root-caused, fix unconfirmed** | <https://github.com/vllm-project/vllm-omni/issues/2683> | 2026-07-21 |
| #2635 | BAGEL YAML / docs field name mismatch | **CLOSED 2026-04-26**, `COMPLETED`. Last comment traces the cause: `OmniDiffusionConfig.from_kwargs()` filters kwargs to valid dataclass fields, and `tensor_parallel_size` is not a field, so it is silently dropped — **root-caused, fix unconfirmed** | <https://github.com/vllm-project/vllm-omni/issues/2635> | 2026-07-21 |
| #2595 | Qwen3-TTS max_model_len validation error | **CLOSED 2026-04-28 on a workaround, not a fix**: set `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (see PR #2508). Expect it still to be needed | <https://github.com/vllm-project/vllm-omni/issues/2595> | 2026-07-21 |
| #2562 | Audio gaps on Qwen3-TTS streaming | **CLOSED 2026-07-04 for INACTIVITY, not fixed** — verbatim: *"close as no response over 1 month. I can reopen if needed."* Treat as still open | <https://github.com/vllm-project/vllm-omni/issues/2562> | 2026-07-21 |

**Reading the closures (freshen-patterns §3.0).** Six of this skill's tracked
issues flipped to `CLOSED` / `COMPLETED` between the 2026-05-28 and 2026-07-21
passes. Only **one** (#4964) closed against a named fix PR. The rest split into
*answered* (#2898 — use YAML, not CLI), *root-caused but unconfirmed* (#2683,
#2635, #2880), *closed on a workaround* (#2595), and *closed for inactivity*
(#2562, and #2768 whose last word is a reproduction). Reading the state field
alone would have retired five live caveats from this skill.

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
- `vllm_omni/patch.py` — early-import patch registering OmniModelConfig (**removed in v0.20.0**; the old entrypoint hijack was dropped for the 0.20.0 integration path per release notes, rebase PR #3232)
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

Also re-check the **distribution channels**, not just the release list. The
2026-07-21 pass found GitHub, PyPI, and Docker Hub disagreeing on the newest
version, with a real bugfix reachable from only one of them.

Compiled 2026-04-18 against v0.18.0 stable. Freshened 2026-05-28 (rebased to
v0.20.0 stable). **Last freshened 2026-07-21**: rebased v0.20.0 -> v0.24.0/v0.24.1
across four minors, documented the GitHub/PyPI/Docker channel mismatch, and
re-probed all tracked issues — six had flipped to CLOSED but only one against a
named fix (see the §3.0 note in the issue table).

**Not re-probed this pass:** the docs-root / supported-models / architecture /
serving / features doc pages (all still 2026-04-18), the arXiv paper, and the
open RFC list. Four minors of model additions mean `references/models.md` is
very likely incomplete — v0.22.0 alone added Cosmos3, DreamZero, MiniCPM-o 4.5,
MOSS-TTS, GLM-TTS, Higgs Audio v2, HiDream-I1-Full, SenseNova U1 and more, and
v0.24.0 added Higgs Audio V3, IndexTTS2, Step-Audio2, SDXL, GR00T-N1.7 and
others. Re-syncing that roster against `supported_models.md` should lead the
next pass.
