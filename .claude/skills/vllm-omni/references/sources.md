# Sources

Freshened: 2026-11-24 — every row probed against omni v0.34.0 (2026-11-22, current stable, on vLLM 0.34.0 released 2026-11-16). Earlier stamp: 2026-11-09 at omni v0.32.0.

Citation anchors backing every claim in this skill. Use to verify — or to feed follow-up searches when a claim looks stale.

## First-party

| Ref | URL |
|---|---|
| Repo | <https://github.com/vllm-project/vllm-omni> |
| Docs root (canonical; `vllm-omni.readthedocs.io` redirects here) | <https://docs.vllm.ai/projects/vllm-omni/en/latest/> |
| Supported models | <https://github.com/vllm-project/vllm-omni/blob/main/docs/models/supported_models.md> |
| Architecture overview | <https://github.com/vllm-project/vllm-omni/blob/main/docs/design/architecture_overview.md> |
| Serving endpoint docs | <https://github.com/vllm-project/vllm-omni/tree/main/docs/serving> |
| Contact / community | <https://github.com/vllm-project/vllm-omni/blob/main/docs/community/contact_us.md> |
| Feature docs — at v0.34.0: `comfyui.md`, `custom_pipeline.md`, `hf_numerics.md`, `independent_stage_execution.md`, `pd_disaggregation.md`, `session_state_manager.md`, `sleep_mode.md`, `watermarking.md` (no `verl.md`) | <https://github.com/vllm-project/vllm-omni/tree/main/docs/features> |
| PyPI (`info.version` = **0.34.0**, uploaded 2026-11-22; `requires_python <3.14,>=3.11`; 0.32.0 uploaded 2026-10-28, 0.33.0rc1 2026-11-04 and 0.34.0rc1 2026-11-18; no 0.33.0; 0.24.1 never uploaded) | <https://pypi.org/project/vllm-omni/> |
| Docker Hub (newest stable **v0.34.0** pushed 2026-11-24 + `-x86_64`/`-aarch64`; `latest` manifest `9ebe23bf849e…` and per-arch digests (amd64 `29d77930a366`, arm64 `170d323159f5`) = **v0.34.0**; no v0.33.0, v0.34.0rc1 or v0.31.0 tag; newest `nightly` dated 2026-11-04; model tags `mosimage`, `flux-3-image-klein`, `minimax-h3-image`, `praxis-1`, `cosmos3`) | <https://hub.docker.com/r/vllm/vllm-omni/tags> |
| Docker Hub ROCm (newest stable **v0.30.0**, pushed 2026-10-21 with v0.29.0rc1, v0.30.0rc1 and v0.31.0rc1; no tag after v0.31.0rc1, so none for v0.32.0–v0.34.0; no `latest`) | <https://hub.docker.com/r/vllm/vllm-omni-rocm/tags> |
| vLLM ROCm wheel index for 0.30.0 (200; `vllm-0.30.0+rocm723-cp312-cp312-manylinux_2_39_x86_64.whl` only) | <https://wheels.vllm.ai/rocm/0.30.0/rocm723/> |
| vLLM ROCm wheel index for 0.33.0 and 0.34.0 (`/rocm/0.33.0/rocm723/` and `/rocm/0.34.0/rocm723/` return 404; the version indexes list only `rocm72` / `rocm100`) | <https://wheels.vllm.ai/rocm/0.34.0/> |
| vLLM ROCm wheel index for 0.32.0 (200; `vllm-0.32.0+rocm723-cp312-cp312-manylinux_2_39_x86_64.whl` only). vllm-omni v0.34.0 `docs/getting_started/installation/gpu/rocm.inc.md`: prebuilt ROCm instructions still install the 0.30.0 pair; the source build targets vLLM 0.34.0 built from its tag ("the older 0.32.0 ROCm wheel does not provide the 0.34 APIs"), ROCm runtime validation pending | <https://wheels.vllm.ai/rocm/0.32.0/rocm723/> |

## Paper

- arXiv abstract: <https://arxiv.org/abs/2602.02204>
- HTML mirror: <https://arxiv.org/html/2602.02204v1>
- Submitted 2026-02-02. Title: "vLLM-Omni: Fully Disaggregated Serving for Any-to-Any Multimodal Models". Up to 91.4% JCT reduction claim (baseline unspecified in abstract).

## Releases

| Release | Date | Notes | URL |
|---|---|---|---|
| Release index | — | — | <https://github.com/vllm-project/vllm-omni/releases> |
| v0.11.0rc1 | 2025-12-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.11.0rc1> |
| v0.12.0rc1 | 2026-01-05 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.12.0rc1> |
| v0.14.0 | 2026-01-31 | **First stable** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.14.0> |
| v0.16.0 | 2026-02-28 | **rebased on vLLM v0.16.0** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.16.0> |
| v0.17.0rc1 | 2026-03-09 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.17.0rc1> |
| v0.18.0rc1 | 2026-03-21 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0rc1> |
| v0.18.0 | 2026-03-28 | rebased on vLLM v0.18.0 (former stable) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0> |
| v0.19.0rc1 | 2026-04-04 | **FLUX.1-dev regression present in tag artifacts (#2730); fix shipped in v0.20.0 (PR #2760) — avoid this specific tag** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.19.0rc1> |
| v0.20.0rc1 | 2026-05-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0rc1> |
| v0.20.0 | 2026-05-07 | **stable, rebased on upstream vLLM v0.20.0 (CUDA 13.0 / PyTorch 2.11); release notes: removal of old vLLM entrypoint hijack + 0.20.0 integration path (#3232/#3082/#3352/#3393/#2306), Transformers 5.x compat, TTS CUDA-graph capture (#2690/#2758/#2803), FLUX T5 fix (#2760)** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0> |
| v0.21.0rc1 | 2026-05-25 | **rc only — no v0.21.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.21.0rc1> |
| v0.22.0rc1 | 2026-06-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0rc1> |
| v0.22.0 | 2026-06-06 | stable, aligned to vLLM 0.22 line. 339 commits / 124 contributors. **Cosmos3 world-model day-0 support** (#3454, #4073, #4102), DreamZero + OpenPI robot serving (#2162, #3673), `OmniCoordinator` integrated into the stage engine pipeline (#3569), broad quantization expansion (W4A16 autoround, MXFP4/MXFP8, ModelOpt mixed FP8/NVFP4, ROCm AITER, XPU, Ascend NPU) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0> |
| v0.23.0rc1 | 2026-06-14 | **rc only — no v0.23.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.23.0rc1> |
| v0.24.0rc1 | 2026-06-30 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0rc1> |
| v0.24.0 | 2026-07-06 | stable, rebased on vLLM v0.23.0 + v0.24.0 (#4286, #4709). 285 commits / 112 contributors. Omni stage runtime + distributed replica control-plane refactor (#3855), diffusion **request-level batching** (#4079), async output materialization (#4476), orchestrator output-path split (#4527), HF-config-based pipeline resolution (#3760), structured `VllmOmniConfig` (#4425). Speech hardening: SSE audio streaming, word-level timestamps, cross-request audio-corruption fix (#4034, #4490, #4706) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0> |
| **v0.24.1** | 2026-07-10 | GitHub tag only — never uploaded to PyPI, no image. Single PR #5017: restores `vllm_c` IR op priority and `torch.nn.RMSNorm` for Qwen-Image, fixing the perf regression in issue #4964 | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.1> |
| v0.25.0rc1 | 2026-07-12 | **rc only — no v0.25.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.25.0rc1> |
| v0.26.0rc1 | 2026-07-28 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.26.0rc1> |
| **v0.26.0** | 2026-08-03 | Stable. Rebased on vLLM **0.26.0** (#5443). 252 changes / 96 contributors. Headline: MiniMax H3 joint video+audio via `/v1/videos` (#5691), experimental full-duplex realtime runtime for MiniCPM-o 4.5 (#3907), distributed layerwise diffusion offload with mmap-backed sharded weights + DP multi-concurrency (#5397, Ascend 910B3 Cosmos3-Nano DP4: 178 GB → 47 GB peak). **Two breaking changes** — LTX registry renames (#5148) and GGUF diffusion moved out of tree (#4769). Also: `guidance_scale=0` honored (#4999), composable parallel-strategy overlays phase 1 (#4281), TensorRT-LLM diffusion attention with Skip-Softmax (#5283) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.26.0> |
| v0.27.0rc1 | 2026-08-11 | **rc only — no v0.27.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.27.0rc1> |
| v0.28.0rc1 | 2026-08-27 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.28.0rc1> |
| v0.28.0 | 2026-08-31 | Stable. Removed `--stage-configs-path` + legacy `stage_args` loader (use `--deploy-config` + `--async-chunk`), `qwen3_omni_moe_async_chunk.yaml`, and DreamID-Omni / MagiHuman / SoulX-Singer / AudioX support | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.28.0> |
| v0.29.0rc1 | 2026-09-10 | **rc only — no v0.29.0 stable was ever cut**; rebase to vLLM 0.29.0 (#7230) landed in v0.30.0 | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.29.0rc1> |
| v0.30.0rc1 | 2026-09-22 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.30.0rc1> |
| **v0.30.0** | 2026-09-25 | Former stable; newest ROCm image. Rebased on vLLM **0.30.0** (#7820, #8027). 504 changes / 183 contributors. Breaking: `diffusion_batch_size` removed → `max_num_seqs` (#6484); unknown diffusion config fields raise (#5172); duplex contract — `/v1/duplex` alias of `/v1/realtime?duplex=1`, `native_duplex` and `full_duplex` removed, use `auto_response` (#7413, #7647, #8024); realtime events renamed to non-beta OpenAI names (#7339, #7426); Dynin-Omni + dots.tts removed (#7655). Also: NIXL connectors (#6093, #6264), native Mooncake AR→DiT KV (#7166, opt-in), Qwen3-TTS default MRv2 + event-driven orchestration (#7930, #7088), `--api-server-count` (#6923, opt-in) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.30.0> |
| v0.31.0rc1 | 2026-10-06 | **rc only — no v0.31.0 stable was ever cut.** Aligned to vLLM **0.31.0** (#8459, #8500). Own notes: reused nightly #16714 was 54 passed / 3 failed / 4 broken. Ray executor for multi-node inference (#7938), `token_ids` output type + canonical output-type names enforced (#7843), async chunk disabled with a warning on pipelines that do not support it (#5099), OpenAI-compliant `/v1/realtime` for Qwen3-Omni (#7285), opt-in single-stage Qwen3-TTS (#8259) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.31.0rc1> |
| v0.32.0rc1 | 2026-10-19 | Pre-release; carries the full changelog (297 changes since v0.31.0rc1) that the v0.32.0 notes summarize. Generalized turn-based `/v1/realtime` (#8339), server VAD on it (#8600), voice registry shared across API processes (#8424), event-driven orchestration default for all pipelines (#8675), Pi0.5 / HiDream-I1 / LTX-2-19b-distilled removal (#9065) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.32.0rc1> |
| **v0.32.0** | 2026-10-28 | Former stable (no ROCm image). Aligned to vLLM **0.32.0** (#9066); source commit `5917730a4b02`. Requires Python `>=3.11,<3.14`. Notes are a summary of changes since v0.30.0 plus `release/v0.32.0` fixes (#9515 HunyuanImage-3 idle MoE LoRA context); install line `uv pip install "vllm==0.32.0" "vllm-omni==0.32.0" --torch-backend=cu130`. New models: YuE2-3B, Qwen-Image-2.1 / 2.1-Turbo, Kandinsky6, MOSS-Image, TaoMate-H3, LTX 2.5 text-to-audio | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.32.0> |
| v0.33.0rc1 | 2026-11-04 | **rc only — no v0.33.0 stable was ever cut** (GitHub title "vLLM-Omni v0.33.0rc1"). Aligned to final vLLM 0.33.0 (#9648); wheel on PyPI; no Docker Hub tag | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.33.0rc1> |
| v0.34.0rc1 | 2026-11-18 | Pre-release (PyPI 0.34.0rc1; no image tag) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.34.0rc1> |
| **v0.34.0** | 2026-11-22 | **Current stable** (GitHub Latest, PyPI, CUDA image + `latest`; no ROCm image). Source commit `06a28821a`. 776 PRs / 185 contributors. Rebased on vLLM **0.34.0** (#10365, which also removes Model Runner V1). Requires Python `>=3.11,<3.14`. **Breaking:** `model_runner: v2` is the only runner (any resolved `v1` stage fails at startup: shipped `qwen3_omni_duplex.yaml`, PersonaPlex Talker, VibeVoice, LFM3-Omni, Fish Drama 3 DAC, MUSA overrides); JoyAI-Image-Edit and Kokoro-82M removed (#10393); `--shm-threshold-bytes` removed (#9992). Also: Thinker prefix cache on by default for Qwen3-Omni and MiniCPM-o 4.5 on CUDA (#9203, #9162, #9193); `semantic_vad` on turn-based `/v1/realtime` (#9170); `/v1/run` experimental stage API; ConvRot INT8/INT4 DiT quantization (#9343); LMCache KV offload (#1330); sampling defaults applied across diffusion APIs (#9700). New models: MiniMax-H3-Image, FLUX.3 Klein, PAN2, Hy-Nomas, Haru-4B, Ming-3.0 TTS/audio, Stable Audio 3, SAM 3, Video Depth Anything, Alpamayo 2 Super, Praxis-1; Pi0.5 restored (#9080) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.34.0> |

### Distribution channels — re-verified 2026-11-24

| Channel | Newest | Evidence |
|---|---|---|
| GitHub releases | **v0.34.0** (2026-11-22) Latest; newest rc v0.34.0rc1 (2026-11-18) | `gh release list -R vllm-project/vllm-omni --json tagName,isLatest` |
| PyPI | **0.34.0** default (uploaded 2026-11-22); 0.32.0, 0.33.0rc1, 0.34.0rc1 present | `pypi.org/pypi/vllm-omni/json` |
| Docker `vllm/vllm-omni` | **v0.34.0** (pushed 2026-11-24, manifest `9ebe23bf849e…`); **`latest` = v0.34.0** — manifest and per-arch digests (amd64 `29d77930a366`, arm64 `170d323159f5`) identical; no v0.33.0 or v0.34.0rc1 tag | Docker Hub v2 tags API |
| Docker `vllm/vllm-omni-rocm` | **v0.30.0** (2026-10-21); v0.31.0rc1 present; no tag for v0.32.0–v0.34.0, no `latest` | Docker Hub v2 tags API |

`latest` history: tracked `vtest-nightly` (2026-08-18), then v0.29.0rc1 (2026-09-22), v0.31.0rc1 (seen 2026-10-18), v0.32.0, now v0.34.0 — it has followed rc images, so pin an exact tag.

Release tags not given a row above: v0.14.0rc1 (2026-01-22), v0.15.0rc1 (2026-02-03), v0.16.0rc1 (2026-02-13); `v0.21.0rc2` is a git tag with no GitHub Release.

**vLLM alignment (checked 2026-11-24):** omni v0.34.0 `requirements/common.txt`: `transformers >= 5.16.1, < 5.23.0`, `diffusers==0.42.0`, `kernels==0.16.1`, `cache-dit==1.5.0`; vLLM v0.34.0 (tag `v0.34.0` = commit `0c57b4195da4`, PyPI `info.version` 0.34.0 uploaded 2026-11-16, `requires_python >=3.11,<3.15`) `requirements/common.txt`: same `transformers` range; `requirements/cuda.txt`: `torch==2.14.0`, `torchvision==0.29.0`, `flashinfer-python==0.7.3`. omni v0.32.0: `transformers >= 5.16.1, < 5.20.0`, `diffusers==0.40.0`; vLLM v0.32.0 `torch==2.13.0`, `torchvision==0.28.0`, `flashinfer-python==0.7.0.post1`. omni v0.30.0 and v0.31.0rc1: `>= 5.13.0, < 5.15`; vLLM v0.30.0 `torch==2.13.0`, `flashinfer-python==0.6.18.post1`. `vllm_omni/version.py` `warn_if_misaligned_vllm_version()` warns on any major.minor mismatch. vLLM 0.33.0 is a final release (git tag `v0.33.0` = `v0.33.0rc3` = commit `4ba787ec9959`; `torch==2.14.0`, `flashinfer-python==0.7.2.post1`); omni never cut a stable for it (only v0.33.0rc1). The v0.34.0 tag's `docs/getting_started/installation/gpu/cuda.inc.md` still prints the 0.32.0 prebuilt-wheel pair while its source-build path targets vLLM 0.34.0 with `--torch-backend=cu130`; PyPI serves omni 0.34.0, whose pair is vLLM 0.34.0. `docs/configuration/stage_configs.md` §"Stage-level runner selection": with vLLM 0.34, `model_runner: v2` is the only supported runner.

The v0.24.1 Qwen-Image fix reaches v0.26.0 **as a separate backport, not by descent** — PR #5017's merge commit is `diverged` from v0.26.0 (it *is* the v0.24.1 tag), while the re-landed PR #5009, whose title marks it "Same As #5017", is contained. Verified with `compare <tag>...<sha>` on both. Checking #5017's ancestry alone would say the fix never shipped, which is false. So the
`git+…@v0.24.1` install form is no longer needed.

- **Parity is not guaranteed to persist.** v0.22.0's notes listed "PyPI upload
  support" (#3667) as a *new* capability, so this plumbing is young. Re-check
  all three channels each pass rather than trusting this row.

## Community

- Slack `#sig-omni`: <https://slack.vllm.ai> (200 after redirect to an inviter page)
- Forum: <https://discuss.vllm.ai>
  - Voxtral + omni thread: <https://discuss.vllm.ai/t/issues-with-voxtral-models-and-omni/2549>
- Weekly meeting: Tuesday 19:30 PDT (see 2025-11-30 launch blog)
- Launch blog (Nov 2025): <https://github.com/vllm-project/vllm-project.github.io/blob/main/_posts/2025-11-30-vllm-omni.md>
- Hong Kong Meetup 2026-03-07: <https://opensource.hk/vllm-hong-kong-meetup/>

## Third-party

- Community skills plugin: <https://github.com/hsliuustc0106/vllm-omni-skills> — 24 `skills/*/SKILL.md` files on 2026-11-24 (not archived, pushed 2026-11-23)
- AIToolly coverage 2026-03-23: <https://aitoolly.com/ai-news/article/2026-03-23-vllm-omni-a-new-framework-for-efficient-omni-modality-model-inference-released-on-github>

## Key issues referenced

| # | Title | State | URL |
|---|---|---|---|
| #4964 | Qwen-Image performance degradation (nightly CI) | **CLOSED 2026-07-10 — genuinely fixed**, originally by PR #5017 (v0.24.1-only, a GitHub tag with no wheel) and carried forward into v0.26.0+ by the re-landed **PR #5009**, not by descent from #5017 — that commit is not an ancestor of v0.26.0 | <https://github.com/vllm-project/vllm-omni/issues/4964> |
| #4998 | `guidance_scale=0` silently overridden by the pipeline default | **CLOSED — genuinely fixed** by PR #4999 (merged 2026-08-01, v0.26.0). Sentinel collision in `OmniDiffusionSamplingParams`: `0.0` meant "unset", so an explicit `0` was replaced by the model default (HunyuanImage-3.0 substitutes `5.0`, enabling CFG). Fix makes `None` the sentinel and tests by identity | <https://github.com/vllm-project/vllm-omni/issues/4998> |
| vllm#38729 | All models hang on GB300 (SM103) with FlashInfer 0.6.7 | **CLOSED/COMPLETED 2026-04-01 via workaround PR vllm#38730**, which restricts `supports_trtllm_attention()` to exact SM100 so SM103 falls back. **SM100/GB200 was never affected.** FlashInfer-side issue flashinfer-ai/flashinfer#2939 closed "as fixed" 2026-04-07. This is the origin of the `flashinfer<0.6.7` pin that `diffusion.md` used to recommend — now obsolete *and* unsatisfiable against vLLM 0.30.0's `flashinfer-python==0.6.18.post1` | <https://github.com/vllm-project/vllm/issues/38729> |
| #2898 | NPU 910B install regression | **CLOSED 2026-04-20 — answered, not patched.** Resolution is a usage correction: `--dtype`, `--max-model-len`, `--served-model-name` etc. "can't be passed correctly currently, because omni is multi-stage deployment", so set them in the **YAML stage config** instead of on the CLI | <https://github.com/vllm-project/vllm-omni/issues/2898> |
| #2880 | HunyuanVideo-1.5 flash-attn shape on NPU mindiesd | **CLOSED 2026-06-02** by PR #3178 ("Adjust flash_attn mask shape for hunyuanvideo1.5 on npu", merged 2026-06-02, first in v0.22.0) | <https://github.com/vllm-project/vllm-omni/issues/2880> |
| #2866 | Qwen3-TTS code2wav crash when enforce_eager=false | **CLOSED 2026-04-29** (CUDA-graph capture shipped via PR #2690 in v0.20.0) | <https://github.com/vllm-project/vllm-omni/issues/2866> |
| #2804 | Diffusion API accepts model mismatch silently | **CLOSED 2026-04-19 — fixed** by PR #2805 (merged 2026-04-19, in v0.20.0+): images, edits and video requests return 400 "Model mismatch" (v0.30.0 `api_server.py:2070,2318`, `video/generation/helpers.py:994`) | <https://github.com/vllm-project/vllm-omni/issues/2804> |
| #2777 | v0.18 Pydantic ChatCompletionResponse validation bug | **Treat as still open.** Shows CLOSED/COMPLETED 2026-07-30, but the closing comment is "no response over 1 month. I can reopen if needed" — an inactivity closure, not a fix | <https://github.com/vllm-project/vllm-omni/issues/2777> |
| #2768 | Orphan procs after Wan2.2 crash | **CLOSED 2026-05-16** by PR #3214 ("Support diffusion worker dead detect when use inline engine", first in v0.22.0): worker death now propagates to the inline client so the server exits. The last pre-closure comment (2026-05-12) reproduced it by killing the *serve* process, which the PR body does not address — keep the process-group mitigation | <https://github.com/vllm-project/vllm-omni/issues/2768> |
| #2760 | [Bugfix] T5 text encoder to render correct text in FLUX.1-dev | **MERGED 2026-04-24** (closes #2730); shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/2760> |
| #2730 | FLUX.1-dev regression on v0.19.0rc1 | **CLOSED 2026-04-24** via PR #2760 — **fixed in v0.20.0 stable** | <https://github.com/vllm-project/vllm-omni/issues/2730> |
| #2690 | [Perf] Speedup VoxCPM2 TTS + PagedAttention | **MERGED 2026-04-13**; shipped in v0.20.0 (lifts the Qwen3-TTS enforce-eager requirement) | <https://github.com/vllm-project/vllm-omni/pull/2690> |
| #3232 | [Rebase] Rebase to vllm 0.20.0 | **MERGED 2026-04-29**; shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/3232> |
| #2683 | mimo_audio online_serving bug | **CLOSED 2026-04-20** by PR #2693 ("Truncate mimo-audio code2wav prompt to MAX_CODE2WAV_TOKENS", first in v0.20.0). The thread root-caused it in `llm2code2wav` in `stage_input_processors/mimo_audio.py` | <https://github.com/vllm-project/vllm-omni/issues/2683> |
| #2635 | BAGEL YAML / docs field name mismatch | **CLOSED 2026-04-26**, `COMPLETED`. Last comment traces the cause: `OmniDiffusionConfig.from_kwargs()` filters kwargs to valid dataclass fields, and `tensor_parallel_size` is not a field, so it is silently dropped — root-caused. **The silent drop is gone in v0.30.0**: PR #5172 (merged 2026-09-19, "Reject unknown diffusion config fields") makes unknown diffusion fields fail with field name + stage id; v0.30.0 `OmniDiffusionConfig.from_kwargs()` is `cls(**cls.normalize_init_kwargs(kwargs))` (`vllm_omni/diffusion/data.py:1762`) | <https://github.com/vllm-project/vllm-omni/issues/2635> |
| #3614 | [Feat] audio streaming input for async chunk | **MERGED 2026-05-31**. Removes the `/v1/realtime` handshake rejection under `async_chunk` (the gate is in v0.20.0 `api_server.py:1378`, absent at v0.22.0, v0.24.0, v0.26.0, v0.28.0, v0.30.0) and the docs line "unsupported while `async_chunk` is enabled". v0.30.0 `qwen3_omni_moe.yaml` ships `async_chunk: true`; `DeployConfig.async_chunk` defaults `True` | <https://github.com/vllm-project/vllm-omni/pull/3614> |
| #7339, #7426 | [Realtime] emit current (non-beta) OpenAI event names / fix leftovers | In v0.30.0 notes (breaking). v0.30.0 `realtime_connection.py:179,197` send `response.output_audio.delta` / `.done`; transcripts via upstream `TranscriptionDelta` / `TranscriptionDone` (`transcription.delta` / `transcription.done`, vLLM v0.30.0 `vllm/entrypoints/speech_to_text/realtime/protocol.py:48,55`) | <https://github.com/vllm-project/vllm-omni/pull/7339> |
| #8339, #8600 | [Core] Generalized turn-based /v1/realtime implementation / [Feature] Add server VAD support to turn-based /v1/realtime | **MERGED 2026-10-06 / 2026-10-15**; in v0.32.0rc1 and v0.32.0. v0.32.0 `vllm_omni/entrypoints/openai/realtime/connection.py` (2020 lines): `SAMPLE_RATE_HZ = 24000` at 68, `_is_pcm16_24khz_format` 328, `_handle_audio_commit` 519 (stores the turn, starts nothing), `_handle_response_create` 683, `ResponseAudioDeltaEvent(delta=…)` 1001, transcript events 970/1193, server-VAD defaults 290-300; served by `OpenAIRealtimeHandler` (`vllm_omni/entrypoints/duplex/openai.py:45`). `tests/examples/test_realtime_web_profiles.cjs:57` asserts `transcription.delta` is ignored. The v0.32.0 doc `docs/serving/realtime_openai_duplex_api.md` still lists `transcription.delta` and 16 kHz input — the code and the shipped client (`examples/online_serving/realtime_web/app/static/profiles/qwen3_turn.js`: rate 24000, `input_audio_buffer.commit` + `response.create`, `?duplex=0`) disagree with it; the skill follows the code. Silero resolution: `vllm_omni/engine/duplex/vad.py:251-268` | <https://github.com/vllm-project/vllm-omni/pull/8339> |
| #8424 | [Bugfix][Frontend] Share the runtime voice registry across API processes | **MERGED 2026-10-15**; in v0.32.0. v0.30.0 `api_server.py:1604,1664` reject voice upload and deletion with 409 when `--api-server-count` > 1; v0.32.0 keeps that guard only for async video jobs (1615) and sleep/wakeup (3089, 3111). Persistence: `serving_speech.py:341` at v0.32.0 (240 at v0.30.0) reads `SPEAKER_SAMPLES_DIR`, default `~/.cache/vllm-omni/speakers`; `docs/serving/speech_api.md` ("persisted to disk … On server restart the directory is scanned") at both tags; local-filesystem advice in v0.32.0 `docs/cli/serve.md` | <https://github.com/vllm-project/vllm-omni/pull/8424> |
| #7843 | [Core] Add token_ids output type and enforce canonical names | **MERGED 2026-10-05**; in v0.31.0rc1 and v0.32.0 notes ("Legacy aliases and malformed values are rejected"). PR body: removes `_MODALITY_ALIASES`; accepts only `text`, `image`, `audio`, `latent`, `token_ids`; keeps `None` defaults and `+` / `,` combinations; invalid names fail during LLM output-processor initialization. v0.32.0 `vllm_omni/outputs/output_modality.py` `OutputModality.from_string()` (called from `vllm_omni/engine/arg_utils.py:562`); `final_output_type` is not parsed by it (`video`, `action` remain in use) | <https://github.com/vllm-project/vllm-omni/pull/7843> |
| #5099 | [Config] Disable Async Chunk for Unsupported Pipelines | **MERGED 2026-09-29**; in v0.31.0rc1 notes (Compatibility) and v0.32.0. v0.32.0 `vllm_omni/config/stage_config.py`: `DeployConfig.async_chunk: bool \| None = None` (827; `bool = True` at v0.30.0 line 580), `_resolve_pipeline_async_chunk_enabled()` 1429-1471 (warnings at 1446, 1462, 1467), `resolve_stage_async_chunk()` 1263 | <https://github.com/vllm-project/vllm-omni/pull/5099> |
| #8675, #8259 | [Perf][Engine] Make event-driven orchestration the default for all pipelines / [Model] Add single-stage Qwen3-TTS with in-Talker streaming codec decode | **MERGED 2026-10-13 / 2026-10-02**; both in v0.32.0. v0.32.0 `vllm_omni/engine/orchestrator.py:92-93` (`VLLM_OMNI_EVENT_DRIVEN_ORCH=0` selects the legacy 1 ms poll loop), `vllm_omni/deploy/qwen3_tts_fused_single_gpu.yaml` (`pipeline: qwen3_tts_fused`), `vllm_omni/deploy/qwen3_tts.yaml` (`model_runner: v2`; `platforms.rocm/npu/xpu/musa` set `model_runner: v1`). Batch speech response model: `protocol/audio.py` `SpeechBatchItemResult` / `BatchSpeechResponse` (537-553 at v0.30.0, 611-627 at v0.32.0) | <https://github.com/vllm-project/vllm-omni/pull/8675> |
| #9731 | [Bug]: image API ignores default sampling parameters | **CLOSED 2026-11-10** by PR #9700 ("Apply sampling defaults across diffusion APIs", ancestor of v0.34.0; touches `api_server.py`, `serving_chat.py`, video and audio generate paths, adds `deploy/moss_image.yaml`). Reported on `vllm/vllm-omni:v0.32.0` with MOSS-Image-Base | <https://github.com/vllm-project/vllm-omni/issues/9731> |
| #9358 | [Bug]: With `async_chunk: false`, a failed inter-stage transfer leaves the request hanging instead of failing it | **OPEN** on 2026-11-24 (opened 2026-10-25). Reported on image `vllm/vllm-omni:v0.30.0` with Qwen2.5-Omni-3B, re-run on 0.32.0rc1 and a 2026-10-24 nightly; fix PR #10778 ("Fail the request when a full-payload stage transfer cannot succeed") is open, unmerged. Sibling #9357 (headless NixlConnector split) **CLOSED 2026-11-19** by #9651 (in v0.34.0) and #10412 (open, not in v0.34.0) | <https://github.com/vllm-project/vllm-omni/issues/9358> |
| #5172 | [Refactor] Reject unknown diffusion config fields | **MERGED 2026-09-19**; in v0.30.0 | <https://github.com/vllm-project/vllm-omni/pull/5172> |
| #7820 | [Rebase] Rebase to vLLM 0.30.0 | In v0.30.0 notes; #8459 aligns v0.31.0rc1 to vLLM 0.31.0 | <https://github.com/vllm-project/vllm-omni/pull/7820> |
| #2595 | Qwen3-TTS max_model_len validation error | **CLOSED 2026-04-28 — fixed** by PR #2508 ("[Bugfix][Model] Fix Qwen3-TTS Code2Wav max_model_len validation", merged 2026-04-22, merge commit `2903f528d2b7`, first contained in v0.20.0rc1 / v0.20.0). The issue's only comment (2026-04-08) predates the merge and offers `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` as a workaround, which earlier passes misread as the resolution. Regression test `tests/engine/test_arg_utils.py::test_qwen3_tts_code2wav_injects_max_position_embeddings` present at v0.32.0; `vllm_omni/engine/stage_init_utils.py` auto-sets the env var for a stage whose `max_model_len` exceeds the HF default (1530-1534 at v0.30.0, 1593-1597 at v0.32.0) | <https://github.com/vllm-project/vllm-omni/issues/2595> |
| #2562 | Audio gaps on Qwen3-TTS streaming | **CLOSED 2026-07-04 for INACTIVITY, not fixed** — verbatim: *"close as no response over 1 month. I can reopen if needed."* Treat as still open | <https://github.com/vllm-project/vllm-omni/issues/2562> |

**Reading the closures (freshen-patterns §3.0).** Closure state alone misleads
here. Closed against a named fix PR: #4964, #2768 (PR #3214, covers worker death
only), #2880 (#3178), #2683 (#2693), #2595 (#2508), #9731 (#9700). *Answered*:
#2898 (use YAML, not CLI). *Root-caused, no PR*: #2635 (the silent drop is gone
via #5172). *Closed for inactivity, not fixed*: #2562, #2777.

## Open RFCs (shape of roadmap)

- [#938 Qwen3-TTS Production Ready milestone](https://github.com/vllm-project/vllm-omni/issues/938)
- [#984 Omni Coordinator](https://github.com/vllm-project/vllm-omni/issues/984)
- [#1217 Continuous Diffusion Model Acceleration Support](https://github.com/vllm-project/vllm-omni/issues/1217)
- [#765 SpargeAttn Sparse Attention Backend](https://github.com/vllm-project/vllm-omni/issues/765) — closed `NOT_PLANNED` 2026-11-19

## Source-file anchors (code in the repo)

All paths are in `vllm-project/vllm-omni`; line numbers are at tag **v0.34.0** (commit `06a28821a`) unless a tag is named.

- `vllm_omni/config/model.py` — OmniModelConfig
- `vllm_omni/engine/async_omni_engine.py` — AsyncOmniEngine
- `vllm_omni/engine/orchestrator.py` — multi-stage orchestrator
- `vllm_omni/engine/stage_engine_core_client.py` — per-stage engine client
- `vllm_omni/entrypoints/cli/main.py` — `--omni` CLI entry (`vllm-omni` console script; upstream `vllm` delegates to it)
- `vllm_omni/entrypoints/openai/api_server.py` (3688 lines; 3149 at v0.32.0) — `/v1/audio/voices` upload 1851 (list 1762, delete 1934), multi-API guard `_reject_process_local_state_with_multiple_api_workers` 1817, `_reject_multi_api_duplex` 2117, `/v1/realtime` 2038, `/v1/duplex` alias 2073, `/health` 2243, `"Model mismatch"` 400s at 2403, 2674, 3008, 3092, 3168; the `@router` path set equals v0.32.0 plus `/v1/images/segmentations`, `/v1/videos/segmentations`, `/v1/videos/depth` and `/v1/run`
- `vllm_omni/entrypoints/openai/realtime/connection.py` (2271 lines; `SAMPLE_RATE_HZ = 24000` at 84, `_is_pcm16_24khz_format` 480, `_handle_audio_commit` 689, `unsupported_turn_detection` 322, `semantic_vad_unavailable` 545, `server_vad_unavailable` 550) — turn-mode `/v1/realtime` (see the #8339 row); v0.34.0 also accepts `semantic_vad` (#9170; Silero + Smart Turn v3.2, `docs/serving/realtime_openai_duplex_api.md` §turn_detection, `examples/online_serving/realtime_web/README.md` §Semantic VAD). At v0.30.0 the handler was `vllm_omni/entrypoints/openai/realtime_connection.py` (audio delta payload at 177-183, `TranscriptionDelta` / `TranscriptionDone` from upstream vLLM); that file does not exist at v0.32.0
- `vllm_omni/entrypoints/openai/video/generation/helpers.py:111` — `VIDEO_SYNC_TIMEOUT_S = float(os.environ.get("VLLM_OMNI_VIDEO_SYNC_TIMEOUT", 600.0))` (109 at v0.32.0, 100 at v0.30.0; env read since v0.24.0; plain `600.0` at v0.20.0 and v0.22.0); video "Model mismatch" at 1253
- `vllm_omni/entrypoints/openai/serving_speech.py:1270` — `MAX_FILE_SIZE = 10 * 1024 * 1024` voice-upload cap (1148 at v0.32.0, 879 at v0.30.0); `SPEAKER_SAMPLES_DIR` read at 453; the file also serves `/v1/audio/speech`
- `vllm_omni/entrypoints/openai/serving_speech_stream.py` — `/v1/audio/speech/stream`
- `vllm_omni/entrypoints/openai/protocol/{images,audio,videos}.py` — request/response models behind every field table in `endpoints.md`. Diffed v0.30.0 → v0.32.0 → v0.34.0: no field in those tables changed; additions only (image request `extra="allow"`, `watermarking`, `cache_salt`, `token_count`, `lora` accepts a list; speech `ref_audio_codes`, `sample_rate`; video timeline guides, streaming pacing and `_control_reference_paths` for MiniMax H3; new segmentation and depth response models). Speech `response_format` wav|pcm|flac|mp3|opus, default wav; image `layers` 2-10; video status queued|in_progress|completed|failed. `_require_single_api_video_store` (api_server.py:1835) returns 409 for async video jobs when `--api-server-count` > 1
- `vllm_omni/distributed/omni_connectors/connectors/*.py` — connector implementations; registered names in `omni_connectors/factory.py:142-150` (MooncakeStore, MooncakeTransferEngine, SharedMemory, Yuanrong, YuanrongTransferEngine, MoriTransferEngine, Nixl, and the `MooncakeConnector` alias "will be removed in the future"). No `rdma_connector.py` at v0.28.0, v0.30.0 or v0.32.0. `mooncake_store_connector.py:33-39` holds the extras defaults quoted in `stage-config.md`
- `vllm_omni/config/stage_config.py` (1818 lines; 1673 at v0.32.0, 1312 at v0.30.0): `PipelineConfig.get_validation_errors()` 559 (492 at v0.32.0); `StageDeployConfig` 586 (per-stage `model_runner`, 608); `DeployConfig` 917 (`async_chunk: bool | None = None`, `session_mode: str = "turn"`, `model_runner: Literal["v1", "v2"] = "v2"` — default `"v1"` through v0.32.0 — `duplex_session`); `_resolve_pipeline_async_chunk_enabled` 1566; a platform or stage that resolves to `v1` is rejected at startup (#10365)
- `vllm_omni/entrypoints/cli/serve.py` (1723 lines): `--task-type` 439, `--deploy-config` 477, `--stage-overrides` 492, `--async-chunk` (`BooleanOptionalAction`) 499, `--stage-id` 505, `--replica-id` 514 (deprecated, ignored), `--stage-init-timeout` 524 default 300, `--init-timeout` 530 default 600, `--worker-backend` 563 (`multi_process|ray`), `--ray-address` 570, `--omni-master-address`/`-oma` 576, `--omni-master-port`/`-omp` 582, `--num-gpus` 634, `--model-class-name` 640, `--usp`/`--ulysses-degree` 795, `--ulysses-mode` 804, `--ring-degree` 826, `--cache-backend` 943 (`tea_cache|cache_dit|mag_cache|sea_cache|step_cache`, default `none`). v0.34.0 adds `--disable-websocket-compression`, `--video-output-warmup`, `--watermark-config`, `--controlnet-model-path` and drops `--shm-threshold-bytes`. No `--stage-configs-path`
- `vllm_omni/diffusion/` — DiT engine
- `vllm_omni/diffusion/cache/teacache/`, `cachedit/`, `magcache/`, `stepcache/`, `seacache/` — DiT activation caches. `cache_dit/` was renamed to `cachedit/` by PR #5226 (2026-07-24); `seacache/` is absent at v0.28.0 and v0.29.0rc1, present from v0.30.0 (Cosmos3 SeaCache, #6922)
- `vllm_omni/inputs/data.py:221-548` — OmniDiffusionSamplingParams (last class in the module, runs to EOF; 211-460 at v0.32.0, 204-422 at v0.30.0). `guidance_scale`, `guidance_scale_2`, `true_cfg_scale`, `strength`, `num_inference_steps` default `None`; `need_kv_receive` `True`; `layers` 4
- `vllm_omni/quantization/factory.py:451` — `build_quant_config()` (649 lines; 411 at v0.32.0, 389 at v0.30.0); per-component detection `_is_per_component_dict()` 404
- `vllm_omni/platforms/__init__.py` (209 lines, unchanged since v0.32.0) — per-platform plugin probes 20-131 and `resolve_current_omni_platform_cls_qualname()` 132
- `pyproject.toml`: `requires-python = ">=3.11,<3.14"` (`>=3.10,<3.14` at v0.26.0, v0.28.0 and v0.30.0); `vllm.general_plugins` entry point `vllm_omni_register_models` at 188-189; `[project.scripts]` `vllm-omni` only
- `requirements/common.txt`: `transformers >= 5.16.1, < 5.23.0` (`< 5.20.0` at v0.32.0; `>= 5.13.0, < 5.15` at v0.30.0), `diffusers==0.42.0` (0.40.0 at v0.32.0), `kernels==0.16.1`, `cache-dit==1.5.0`
- `docs/getting_started/installation/gpu/cuda.inc.md`, `rocm.inc.md`, `quickstart.md` — at v0.34.0 the source-build path targets vLLM 0.34.0 (CUDA 13.0, `--torch-backend=cu130`, `uv venv --python 3.12`), the CUDA prebuilt-wheel block prints the 0.32.0 pair and the ROCm one the 0.30.0 pair; PyPI serves omni 0.34.0
- `vllm_omni/profiler/omni_torch_profiler.py` — profiler wrapper
- `vllm_omni/patch.py` — import-time monkey-patch, loaded by `vllm_omni/__init__.py:25`; present at every stable tag v0.18.0–v0.34.0 (`git ls-tree <tag> vllm_omni/patch.py`). At v0.34.0 the loop from line 366 walks `sys.modules` and swap `EngineCoreOutput(s)`, `TokensPrompt`, `MRotaryEmbedding`, `Request`, `StreamingUpdate`, `EngineCoreRequest` for Omni subclasses. What v0.20.0 removed is the `vllm` console-script hijack: v0.18.0 `pyproject.toml` `[project.scripts]` declares `vllm = "vllm_omni.entrypoints.cli.main:main"`, v0.20.0 declares only `vllm-omni`. The earlier "patch.py removed in v0.20.0" wording matched no tag
- `vllm-project/vllm` at v0.34.0 `vllm/entrypoints/cli/main.py:17-36` — `maybe_run_omni()`: with `--omni` in argv, delegates to `vllm_omni.entrypoints.cli.main.main`; `sys.exit(1)` when `vllm_omni` is not importable (present at v0.30.0 too)
- `vllm_omni/version.py` — version resolution + vLLM alignment check (`warn_if_misaligned_vllm_version()` compares major.minor)
- `vllm_omni/deploy/*.yaml` — reference deploy configs: 169 YAML files (142 at v0.32.0, 110 at v0.30.0). `qwen3_omni_moe.yaml` (`model_runner: v2`, `async_chunk: true`, stage 0 `enable_prefix_caching: true`; stage 0 on cuda:0, stages 1+2 on cuda:1; `platforms.musa` still requests `v1`), `qwen3_omni_duplex.yaml` (`base_config: qwen3_omni_moe.yaml`, `session_mode: duplex`; header says it retains V1 and is unsupported), `qwen3_omni_duplex_mrv2.yaml` (`base_config: qwen3_omni_moe_mrv2.yaml`), `qwen3_tts.yaml` (`model_runner: v2`; header: V1 overrides unsupported, MUSA requests V1 and is rejected), `qwen3_tts_fused_single_gpu.yaml`, `personaplex.yaml` (`session_mode: duplex`), `hunyuan-image-3-mooncakeconnector.yaml` (`kv_transfer_config`). Absent: `qwen3_omni_moe_async_chunk.yaml`, `qwen_image.yaml`, `wan2_2_t2v.yaml`
- `examples/online_serving/qwen3_omni/openai_realtime_client.py` **at v0.30.0** — realtime client template; 16 kHz check at line 60, CLI flags `--url --model --input-wav --output-wav --output-text --chunk-ms --send-delay-ms --delta-dump-dir --server-vad --num-requests --concurrency`. Removed at v0.32.0; the turn client is `examples/online_serving/realtime_web/` (`README.md` §"Qwen3: explicit-turn Realtime")
- `examples/online_serving/qwen3_omni/README.md` — at v0.32.0 lines 152-175: `--no-async-chunk` override and the warning against global `--gpu-memory-utilization` on GPU-sharing stages; 306-311 point realtime users at `realtime_web`
- `examples/online_serving/text_to_video/README.md` — video job API walkthrough
- `examples/online_serving/text_to_image/README.md` §LoRA, `docs/user_guide/diffusion/lora.md`, `docs/user_guide/diffusion/offloader/*.md`, `docs/user_guide/quantization/*.md` — diffusion flag and request shapes cited in `diffusion.md`

## Refresh policy

Refresh this skill when:

- A new stable release lands (watch for rebase onto newer upstream vLLM).
- A new model family joins the supported list — cross-check against current `supported_models.md`.
- A key issue in the reference list (Qwen3-TTS enforce-eager, FLUX regression, GLM-Image transformers pin) closes — those are the advice that directly affects operators.
- Paper gets updated / superseded.

Also re-check the **distribution channels**, not just the release list. The
2026-07-21 pass found GitHub, PyPI, and Docker Hub disagreeing on the newest
version, with a real bugfix reachable from only one of them.

Compiled 2026-04-18 against v0.18.0 stable. Freshened 2026-05-28 (v0.20.0) and
2026-07-21 (v0.24.0/v0.24.1 + channel mismatch + six issue-closure
re-classifications). **Last freshened 2026-08-11**: rebased to **v0.26.0**,
recorded its two breaking changes (LTX registry renames #5148, GGUF moved out
of tree #4769), and closed three long-standing open questions against primary
sources —

- the **`guidance_scale=0` sentinel** was a real bug, fixed by #4999 in
  v0.26.0, not a design choice to document forever;
- the **GLM-Image `transformers>=5.0`** hedge is retired: vllm-omni v0.26.0's
  own `requirements/common.txt` floors transformers at `>= 5.5.3`;
- the **`flashinfer<0.6.7`** pin traces to upstream vLLM issue #38729 (SM103
  only, fixed in-tree by #38730 on 2026-04-01) and is now unsatisfiable
  against vLLM 0.26.0's `flashinfer-python==0.6.14`.

Runtime pins for the current line (checked 2026-11-24): vllm-omni v0.34.0 rides
vLLM 0.34.0 — **PyTorch 2.14.0 / FlashInfer 0.7.3 / torchvision 0.29.0**
(vLLM v0.34.0 `requirements/cuda.txt`) plus `transformers >= 5.16.1, < 5.23.0`
and `diffusers==0.42.0` (vllm-omni v0.34.0 `requirements/common.txt`).

`references/models.md` tables were synced row-for-row (125 rows, platform
columns included) from `docs/models/supported_models.md` at tag v0.34.0 on
2026-11-24 (105 rows at v0.32.0: 21 added, `JoyImageEditPipeline` removed by
#10393, `QwenImage21Pipeline` text now "up to 10 condition images",
`SeedVR2Pipeline`, `Magi2Pipeline` and `BooguImageTurboPipeline` gained NPU,
`Magi2Pipeline` also XPU); the new top-of-table note says profiles that need
Model Runner V1 are unavailable on vLLM 0.34.0 (Drama 3 / Fish-Omni, LFM3-Omni).
LTX DMD2 rows from `vllm_omni/diffusion/registry.py` (`LTX2T2VDMD2Pipeline` 132,
`LTX2I2VDMD2Pipeline` 137) at v0.34.0, still registered and not in the list;
`Pi05Pipeline` (registry 277) was restored by #9080 after #9065 removed it
(v0.32.0 rc changelog) and is in the v0.34.0 list; `HiDreamImagePipeline`
(HiDream-I1-Full) is absent from the registry, `HiDreamO1ImagePipeline`
present. MUSA detection from `vllm_omni/platforms/__init__.py:107-131`
(unchanged); Qwen3-TTS Base size from
`examples/online_serving/text_to_speech/README.md` (1.7B-Base; the 0.6B-Base
checkpoint exists on HF but is not listed); #2562 title is
"gaps during audio generation via Qwen TTS". Open model requests #2593, #2462, #2319,
#2664, #2727 and #2612 all read OPEN on 2026-11-24.
