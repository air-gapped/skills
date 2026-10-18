# Sources

Freshened: 2026-10-18 — probed at omni v0.30.0 (current stable, vLLM 0.30.0) against vLLM v0.32.0: no omni release matches vLLM 0.31/0.32 (disjoint transformers ranges), realtime works under `async_chunk` since v0.22.0 (#3614), v0.30.0 renamed realtime audio events and removed `diffusion_batch_size` and Dynin-Omni/dots.tts; no `RDMAConnector` exists (NIXL/MORI connectors do); sync-video timeout is 600 s and Python 3.10–3.13 is declared.

Citation anchors backing every claim in this skill. Use to verify — or to feed follow-up searches when a claim looks stale.

## First-party

| Ref | URL | Last verified |
|---|---|---|
| Repo | <https://github.com/vllm-project/vllm-omni> | 2026-10-18 |
| Docs root (canonical — **not** `vllm-omni.readthedocs.io`, that subdomain 302s / 403s) | <https://docs.vllm.ai/projects/vllm-omni/en/latest/> | 2026-10-18 |
| Supported models | <https://github.com/vllm-project/vllm-omni/blob/main/docs/models/supported_models.md> | 2026-10-18 |
| Architecture overview | <https://github.com/vllm-project/vllm-omni/blob/main/docs/design/architecture_overview.md> | 2026-10-18 |
| Serving endpoint docs | <https://github.com/vllm-project/vllm-omni/tree/main/docs/serving> | 2026-10-18 |
| Contact / community | <https://github.com/vllm-project/vllm-omni/blob/main/docs/community/contact_us.md> | 2026-10-18 |
| Feature docs (ComfyUI, Sleep mode, verl) | <https://github.com/vllm-project/vllm-omni/tree/main/docs/features> | 2026-10-18 |
| PyPI (`info.version` = **0.30.0**, uploaded 2026-09-25; `requires_python <3.14,>=3.10`; 0.31.0rc1 present as pre-release; 0.24.1 never uploaded) | <https://pypi.org/project/vllm-omni/> | 2026-10-18 |
| Docker Hub (newest stable **v0.30.0** + `-x86_64`/`-aarch64`; `latest` manifest + per-arch digests = **v0.31.0rc1**; rolling `nightly*` and model tags `mosimage`, `flux-3-image-klein`, `qwen-image21`, `minimax-h3`) | <https://hub.docker.com/r/vllm/vllm-omni/tags> | 2026-10-18 |
| Docker Hub ROCm (newest stable **v0.28.0**; no v0.29/v0.30 tag; no `latest`) | <https://hub.docker.com/r/vllm/vllm-omni-rocm/tags> | 2026-10-18 |
| vLLM ROCm wheel index for 0.30.0 (200; `vllm-0.30.0+rocm723-cp312-cp312-manylinux_2_39_x86_64.whl` only) | <https://wheels.vllm.ai/rocm/0.30.0/rocm723/> | 2026-10-18 |

## Paper

- arXiv abstract: <https://arxiv.org/abs/2602.02204>
- HTML mirror: <https://arxiv.org/html/2602.02204v1>
- Submitted 2026-02-02. Title: "vLLM-Omni: Fully Disaggregated Serving for Any-to-Any Multimodal Models". Up to 91.4% JCT reduction claim (baseline unspecified in abstract).

## Releases

| Release | Date | Notes | URL | Last verified |
|---|---|---|---|---|
| Release index | — | — | <https://github.com/vllm-project/vllm-omni/releases> | 2026-10-18 |
| v0.11.0rc1 | 2025-12-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.11.0rc1> | 2026-10-18 |
| v0.12.0rc1 | 2026-01-05 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.12.0rc1> | 2026-10-18 |
| v0.14.0 | 2026-01-31 | **First stable** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.14.0> | 2026-10-18 |
| v0.16.0 | 2026-02-28 | **rebased on vLLM v0.16.0** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.16.0> | 2026-10-18 |
| v0.17.0rc1 | 2026-03-09 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.17.0rc1> | 2026-10-18 |
| v0.18.0rc1 | 2026-03-21 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0rc1> | 2026-10-18 |
| v0.18.0 | 2026-03-28 | rebased on vLLM v0.18.0 (former stable) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.18.0> | 2026-10-18 |
| v0.19.0rc1 | 2026-04-04 | **FLUX.1-dev regression present in tag artifacts (#2730); fix shipped in v0.20.0 (PR #2760) — avoid this specific tag** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.19.0rc1> | 2026-10-18 |
| v0.20.0rc1 | 2026-05-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0rc1> | 2026-10-18 |
| v0.20.0 | 2026-05-07 | **stable, rebased on upstream vLLM v0.20.0 (CUDA 13.0 / PyTorch 2.11); release notes: removal of old vLLM entrypoint hijack + 0.20.0 integration path (#3232/#3082/#3352/#3393/#2306), Transformers 5.x compat, TTS CUDA-graph capture (#2690/#2758/#2803), FLUX T5 fix (#2760)** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.20.0> | 2026-10-18 |
| v0.21.0rc1 | 2026-05-25 | **rc only — no v0.21.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.21.0rc1> | 2026-10-18 |
| v0.22.0rc1 | 2026-06-01 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0rc1> | 2026-10-18 |
| v0.22.0 | 2026-06-06 | stable, aligned to vLLM 0.22 line. 339 commits / 124 contributors. **Cosmos3 world-model day-0 support** (#3454, #4073, #4102), DreamZero + OpenPI robot serving (#2162, #3673), `OmniCoordinator` integrated into the stage engine pipeline (#3569), broad quantization expansion (W4A16 autoround, MXFP4/MXFP8, ModelOpt mixed FP8/NVFP4, ROCm AITER, XPU, Ascend NPU) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.22.0> | 2026-10-18 |
| v0.23.0rc1 | 2026-06-14 | **rc only — no v0.23.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.23.0rc1> | 2026-10-18 |
| v0.24.0rc1 | 2026-06-30 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0rc1> | 2026-10-18 |
| v0.24.0 | 2026-07-06 | stable, rebased on vLLM v0.23.0 + v0.24.0 (#4286, #4709). 285 commits / 112 contributors. **Newest version available as a wheel and as a container.** Omni stage runtime + distributed replica control-plane refactor (#3855), diffusion **request-level batching** (#4079), async output materialization (#4476), orchestrator output-path split (#4527), HF-config-based pipeline resolution (#3760), structured `VllmOmniConfig` (#4425). Speech hardening: SSE audio streaming, word-level timestamps, cross-request audio-corruption fix (#4034, #4490, #4706) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.0> | 2026-10-18 |
| **v0.24.1** | 2026-07-10 | GitHub tag only — never uploaded to PyPI, no image. Single PR #5017: restores `vllm_c` IR op priority and `torch.nn.RMSNorm` for Qwen-Image, fixing the perf regression in issue #4964 | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.24.1> | 2026-10-18 |
| v0.25.0rc1 | 2026-07-12 | **rc only — no v0.25.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.25.0rc1> | 2026-10-18 |
| v0.26.0rc1 | 2026-07-28 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.26.0rc1> | 2026-10-18 |
| **v0.26.0** | 2026-08-03 | Stable. Rebased on vLLM **0.26.0** (#5443). 252 changes / 96 contributors. Headline: MiniMax H3 joint video+audio via `/v1/videos` (#5691), experimental full-duplex realtime runtime for MiniCPM-o 4.5 (#3907), distributed layerwise diffusion offload with mmap-backed sharded weights + DP multi-concurrency (#5397, Ascend 910B3 Cosmos3-Nano DP4: 178 GB → 47 GB peak). **Two breaking changes** — LTX registry renames (#5148) and GGUF diffusion moved out of tree (#4769). Also: `guidance_scale=0` honored (#4999), composable parallel-strategy overlays phase 1 (#4281), TensorRT-LLM diffusion attention with Skip-Softmax (#5283) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.26.0> | 2026-10-18 |
| v0.27.0rc1 | 2026-08-11 | **rc only — no v0.27.0 stable was ever cut** | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.27.0rc1> | 2026-10-18 |
| v0.28.0rc1 | 2026-08-27 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.28.0rc1> | 2026-10-18 |
| v0.28.0 | 2026-08-31 | Stable. Removed `--stage-configs-path` + legacy `stage_args` loader (use `--deploy-config` + `--async-chunk`), `qwen3_omni_moe_async_chunk.yaml`, and DreamID-Omni / MagiHuman / SoulX-Singer / AudioX support. Newest ROCm image | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.28.0> | 2026-10-18 |
| v0.29.0rc1 | 2026-09-10 | **rc only — no v0.29.0 stable was ever cut**; rebase to vLLM 0.29.0 (#7230) landed in v0.30.0 | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.29.0rc1> | 2026-10-18 |
| v0.30.0rc1 | 2026-09-22 | — | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.30.0rc1> | 2026-10-18 |
| **v0.30.0** | 2026-09-25 | **Current stable** (GitHub Latest, PyPI, CUDA image; no ROCm image). Rebased on vLLM **0.30.0** (#7820, #8027). 504 changes / 183 contributors. Breaking: `diffusion_batch_size` removed → `max_num_seqs` (#6484); unknown diffusion config fields raise (#5172); duplex contract — `/v1/duplex` alias of `/v1/realtime?duplex=1`, `native_duplex` and `full_duplex` removed, use `auto_response` (#7413, #7647, #8024); realtime events renamed to non-beta OpenAI names (#7339, #7426); Dynin-Omni + dots.tts removed (#7655). Also: NIXL connectors (#6093, #6264), native Mooncake AR→DiT KV (#7166, opt-in), Qwen3-TTS default MRv2 + event-driven orchestration (#7930, #7088), `--api-server-count` (#6923, opt-in) | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.30.0> | 2026-10-18 |
| v0.31.0rc1 | 2026-10-06 | **Pre-release — not current.** Aligned to vLLM **0.31.0** (#8459, #8500). Own notes: reused nightly #16714 was 54 passed / 3 failed / 4 broken; MiniCPM-o long-form async_chunk test failing. Canonical output-type names enforced (#7843). Docker `latest` points here | <https://github.com/vllm-project/vllm-omni/releases/tag/v0.31.0rc1> | 2026-10-18 |

### Distribution channels — re-verified 2026-10-18

| Channel | Newest | Evidence |
|---|---|---|
| GitHub releases | **v0.30.0** (2026-09-25) `isLatest`; newest tag v0.31.0rc1 (2026-10-06, prerelease) | `gh release list -R vllm-project/vllm-omni --json tagName,isLatest` |
| PyPI | **0.30.0** default (uploaded 2026-09-25); 0.31.0rc1 present | `pypi.org/pypi/vllm-omni/json` |
| Docker `vllm/vllm-omni` | **v0.30.0** (2026-09-27, manifest `fc77cfaac7b1…`); **`latest` = v0.31.0rc1** — manifest `ea84abca067d…` and per-arch digests (amd64 `a3654da076b6`, arm64 `85124b352e03`) identical | Docker Hub v2 tags API |
| Docker `vllm/vllm-omni-rocm` | **v0.28.0** (2026-09-14); no v0.29/v0.30 tag, no `latest` | Docker Hub v2 tags API |

`latest` history: tracked `vtest-nightly` (2026-08-18), then v0.29.0rc1 (2026-09-22), now v0.31.0rc1 — it follows the newest tag, rc or not.

**vLLM v0.32.0 compatibility (checked 2026-10-18):** no omni release targets it. omni v0.30.0 and v0.31.0rc1 `requirements/common.txt`: `transformers >= 5.13.0, < 5.15`. vLLM `requirements/common.txt`: v0.30.0 `>= 5.10.4`; v0.31.0 `>= 5.10.4, < 5.18.0`; v0.32.0 `>= 5.16.1, < 5.20.0` — disjoint with omni. `vllm_omni/version.py` `warn_if_misaligned_vllm_version()` warns on any major.minor mismatch. No omni PR titled for a 0.32 rebase (`gh pr list --search "0.32 in:title"` empty); omni `main` `common.txt` still references vLLM 0.31.0. vLLM v0.30.0 `requirements/cuda.txt`: `torch==2.13.0`, `flashinfer-python==0.6.18.post1`, `torchvision==0.28.0`; v0.31.0 and v0.32.0: `flashinfer-python==0.7.0.post1`.

The v0.24.1 Qwen-Image fix reaches v0.26.0 **as a separate backport, not by descent** — PR #5017's merge commit is `diverged` from v0.26.0 (it *is* the v0.24.1 tag), while the re-landed PR #5009, whose title marks it "Same As #5017", is contained. Verified with `compare <tag>...<sha>` on both. Checking #5017's ancestry alone would say the fix never shipped, which is false. So the
`git+…@v0.24.1` install form is no longer needed.

- **Parity is not guaranteed to persist.** v0.22.0's notes listed "PyPI upload
  support" (#3667) as a *new* capability, so this plumbing is young. Re-check
  all three channels each pass rather than trusting this row.

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
| #4964 | Qwen-Image performance degradation (nightly CI) | **CLOSED — genuinely fixed**, originally by PR #5017 (v0.24.1-only, a GitHub tag with no wheel) and carried forward into v0.26.0+ by the re-landed **PR #5009**, not by descent from #5017 — that commit is not an ancestor of v0.26.0 | <https://github.com/vllm-project/vllm-omni/issues/4964> | 2026-10-18 |
| #4998 | `guidance_scale=0` silently overridden by the pipeline default | **CLOSED — genuinely fixed** by PR #4999 (merged 2026-08-01, v0.26.0). Sentinel collision in `OmniDiffusionSamplingParams`: `0.0` meant "unset", so an explicit `0` was replaced by the model default (HunyuanImage-3.0 substitutes `5.0`, enabling CFG). Fix makes `None` the sentinel and tests by identity | <https://github.com/vllm-project/vllm-omni/issues/4998> | 2026-10-18 |
| vllm#38729 | All models hang on GB300 (SM103) with FlashInfer 0.6.7 | **CLOSED/COMPLETED 2026-04-01 via workaround PR vllm#38730**, which restricts `supports_trtllm_attention()` to exact SM100 so SM103 falls back. **SM100/GB200 was never affected.** FlashInfer-side issue flashinfer-ai/flashinfer#2939 closed "as fixed" 2026-04-07. This is the origin of the `flashinfer<0.6.7` pin that `diffusion.md` used to recommend — now obsolete *and* unsatisfiable against vLLM 0.30.0's `flashinfer-python==0.6.18.post1` | <https://github.com/vllm-project/vllm/issues/38729> | 2026-10-18 |
| #2898 | NPU 910B install regression | **CLOSED 2026-04-20 — answered, not patched.** Resolution is a usage correction: `--dtype`, `--max-model-len`, `--served-model-name` etc. "can't be passed correctly currently, because omni is multi-stage deployment", so set them in the **YAML stage config** instead of on the CLI | <https://github.com/vllm-project/vllm-omni/issues/2898> | 2026-10-18 |
| #2880 | HunyuanVideo-1.5 flash-attn shape on NPU mindiesd | **CLOSED 2026-06-02**, `COMPLETED`. Last comment is a maintainer ping (`@gcanlin PTAL`, 2026-04-20) with no fix reference — **fix unconfirmed**, re-test before relying on it | <https://github.com/vllm-project/vllm-omni/issues/2880> | 2026-10-18 |
| #2866 | Qwen3-TTS code2wav crash when enforce_eager=false | **CLOSED 2026-04-29** (CUDA-graph capture shipped via PR #2690 in v0.20.0) | <https://github.com/vllm-project/vllm-omni/issues/2866> | 2026-10-18 |
| #2804 | Diffusion API accepts model mismatch silently | **CLOSED 2026-04-19** | <https://github.com/vllm-project/vllm-omni/issues/2804> | 2026-10-18 |
| #2777 | v0.18 Pydantic ChatCompletionResponse validation bug | **Treat as still open.** Shows CLOSED/COMPLETED 2026-07-30, but the closing comment is "no response over 1 month. I can reopen if needed" — an inactivity closure, not a fix | <https://github.com/vllm-project/vllm-omni/issues/2777> | 2026-10-18 |
| #2768 | Orphan procs after Wan2.2 crash | **CLOSED 2026-05-16 `COMPLETED` — but treat as UNRESOLVED.** The last comment (2026-05-12, four days before closure) is a **fresh reproduction by a different reporter** — *"When I kill the serve process … the same bug occurred."* No fix PR referenced. Keep the process-group mitigation | <https://github.com/vllm-project/vllm-omni/issues/2768> | 2026-10-18 |
| #2760 | [Bugfix] T5 text encoder to render correct text in FLUX.1-dev | **MERGED 2026-04-24** (closes #2730); shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/2760> | 2026-10-18 |
| #2730 | FLUX.1-dev regression on v0.19.0rc1 | **CLOSED 2026-04-24** via PR #2760 — **fixed in v0.20.0 stable** | <https://github.com/vllm-project/vllm-omni/issues/2730> | 2026-10-18 |
| #2690 | [Perf] Speedup VoxCPM2 TTS + PagedAttention | **MERGED 2026-04-13**; shipped in v0.20.0 (lifts the Qwen3-TTS enforce-eager requirement) | <https://github.com/vllm-project/vllm-omni/pull/2690> | 2026-10-18 |
| #3232 | [Rebase] Rebase to vllm 0.20.0 | **MERGED 2026-04-29**; shipped in v0.20.0 | <https://github.com/vllm-project/vllm-omni/pull/3232> | 2026-10-18 |
| #2683 | mimo_audio online_serving bug | **CLOSED 2026-04-20**, `COMPLETED`. Last comment root-causes it in the online input processor (`llm2code2wav` in `stage_input_processors/mimo_audio.py` flattens the full stage-0 talker output, ~36 ids per frame) — **root-caused, fix unconfirmed** | <https://github.com/vllm-project/vllm-omni/issues/2683> | 2026-10-18 |
| #2635 | BAGEL YAML / docs field name mismatch | **CLOSED 2026-04-26**, `COMPLETED`. Last comment traces the cause: `OmniDiffusionConfig.from_kwargs()` filters kwargs to valid dataclass fields, and `tensor_parallel_size` is not a field, so it is silently dropped — root-caused. **The silent drop is gone in v0.30.0**: PR #5172 (merged 2026-09-19, "Reject unknown diffusion config fields") makes unknown diffusion fields fail with field name + stage id; v0.30.0 `OmniDiffusionConfig.from_kwargs()` is `cls(**cls.normalize_init_kwargs(kwargs))` (`vllm_omni/diffusion/data.py:1762`) | <https://github.com/vllm-project/vllm-omni/issues/2635> | 2026-10-18 |
| #3614 | [Feat] audio streaming input for async chunk | **MERGED 2026-05-31**. Removes the `/v1/realtime` handshake rejection under `async_chunk` (the gate is in v0.20.0 `api_server.py:1378`, absent at v0.22.0, v0.24.0, v0.26.0, v0.28.0, v0.30.0) and the docs line "unsupported while `async_chunk` is enabled". v0.30.0 `qwen3_omni_moe.yaml` ships `async_chunk: true`; `DeployConfig.async_chunk` defaults `True` | <https://github.com/vllm-project/vllm-omni/pull/3614> | 2026-10-18 |
| #7339, #7426 | [Realtime] emit current (non-beta) OpenAI event names / fix leftovers | In v0.30.0 notes (breaking). v0.30.0 `realtime_connection.py:179,197` send `response.output_audio.delta` / `.done`; transcripts via upstream `TranscriptionDelta` / `TranscriptionDone` (`transcription.delta` / `transcription.done`, vLLM v0.30.0 `vllm/entrypoints/speech_to_text/realtime/protocol.py:48,55`) | <https://github.com/vllm-project/vllm-omni/pull/7339> | 2026-10-18 |
| #5172 | [Refactor] Reject unknown diffusion config fields | **MERGED 2026-09-19**; in v0.30.0 | <https://github.com/vllm-project/vllm-omni/pull/5172> | 2026-10-18 |
| #7820 | [Rebase] Rebase to vLLM 0.30.0 | In v0.30.0 notes; #8459 aligns v0.31.0rc1 to vLLM 0.31.0 | <https://github.com/vllm-project/vllm-omni/pull/7820> | 2026-10-18 |
| #2595 | Qwen3-TTS max_model_len validation error | **CLOSED 2026-04-28 on a workaround, not a fix**: set `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (see PR #2508). Expect it still to be needed | <https://github.com/vllm-project/vllm-omni/issues/2595> | 2026-10-18 |
| #2562 | Audio gaps on Qwen3-TTS streaming | **CLOSED 2026-07-04 for INACTIVITY, not fixed** — verbatim: *"close as no response over 1 month. I can reopen if needed."* Treat as still open | <https://github.com/vllm-project/vllm-omni/issues/2562> | 2026-10-18 |

**Reading the closures (freshen-patterns §3.0).** Six of this skill's tracked
issues flipped to `CLOSED` / `COMPLETED` between the 2026-05-28 and 2026-07-21
passes. Only **one** (#4964) closed against a named fix PR. The rest split into
*answered* (#2898 — use YAML, not CLI), *root-caused but unconfirmed* (#2683,
#2635, #2880), *closed on a workaround* (#2595), and *closed for inactivity*
(#2562, and #2768 whose last word is a reproduction). Reading the state field
alone would have retired five live caveats from this skill.

## Open RFCs (shape of roadmap)

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
- `vllm_omni/entrypoints/openai/api_server.py` — OpenAI-compat server (3056 lines at v0.30.0; `/v1/realtime` handler at 1752, `/v1/duplex` alias at 1799, `/health` near 1948)
- `vllm_omni/entrypoints/openai/realtime_connection.py` — `/v1/realtime` WebSocket; subclasses upstream `vllm.entrypoints.speech_to_text.realtime.connection.RealtimeConnection`
- `vllm_omni/entrypoints/openai/video/generation/helpers.py:100` — `VIDEO_SYNC_TIMEOUT_S = float(os.environ.get("VLLM_OMNI_VIDEO_SYNC_TIMEOUT", 600.0))` at v0.30.0 (env read since v0.24.0; plain `600.0` at v0.20.0 and v0.22.0 — the old "~1200 s" figure matched no tag checked)
- `vllm_omni/entrypoints/openai/serving_speech.py:879` — `MAX_FILE_SIZE = 10 * 1024 * 1024` voice-upload cap at v0.30.0
- `vllm_omni/entrypoints/openai/serving_speech.py` — `/v1/audio/speech`
- `vllm_omni/entrypoints/openai/serving_speech_stream.py` — `/v1/audio/speech/stream`
- `vllm_omni/distributed/omni_connectors/connectors/*.py` — connector implementations; registered names in `omni_connectors/factory.py:140-148` at v0.30.0 (SharedMemory, MooncakeStore + `MooncakeConnector` alias, MooncakeTransferEngine, Yuanrong, YuanrongTransferEngine, MoriTransferEngine, Nixl). No `rdma_connector.py` at v0.28.0 or v0.30.0
- `vllm_omni/config/stage_config.py` at v0.30.0 (1312 lines): `PipelineConfig.get_validation_errors()` 358-382; `StageDeployConfig` 385; `DeployConfig` 569 (`async_chunk: bool = True`, `session_mode`, `model_runner`)
- `vllm_omni/entrypoints/cli/serve.py` at v0.30.0: `--deploy-config` 390, `--stage-overrides`, `--async-chunk` (`BooleanOptionalAction`) 412, `--stage-init-timeout` default 300, `--init-timeout` default 600, `--cache-backend` 772 (`tea_cache|cache_dit|mag_cache|sea_cache|step_cache`)
- `vllm_omni/diffusion/` — DiT engine
- `vllm_omni/diffusion/cache/teacache/`, `cachedit/`, `magcache/`, `stepcache/`, `seacache/` — DiT activation caches at v0.30.0. `cache_dit/` was renamed to `cachedit/` by PR #5226 (2026-07-24); `seacache/` is absent at v0.28.0 and v0.29.0rc1, present at v0.30.0 (Cosmos3 SeaCache, #6922)
- `vllm_omni/inputs/data.py:204-422` — OmniDiffusionSamplingParams **at tag v0.30.0** (last class in the module, runs to EOF; 198-411 at v0.28.0). `guidance_scale`, `guidance_scale_2`, `true_cfg_scale`, `strength`, `num_inference_steps` default `None`; `need_kv_receive` `True`; `layers` 4
- `vllm_omni/quantization/factory.py:389` — `build_quant_config()` **at tag v0.30.0** (579 lines; 366 at v0.28.0). The once-cited 138-178 range was internal per-scheme helpers, not the factory
- `vllm_omni/platforms/__init__.py:20-170` — per-platform plugin probes (20-131) and `resolve_current_omni_platform_cls_qualname()` (132) at v0.30.0
- `pyproject.toml` at v0.30.0: `requires-python = ">=3.10,<3.14"` (same at v0.26.0 and v0.28.0 — the old "3.12 required" claim matched no checked tag); `vllm.general_plugins` entry point `vllm_omni_register_models`
- `requirements/common.txt` at v0.30.0: `transformers >= 5.13.0, < 5.15`, `diffusers==0.40.0`, `kernels==0.16.1`, `cache-dit==1.5.0`
- `docs/getting_started/installation/gpu/cuda.inc.md`, `rocm.inc.md`, `quickstart.md` at v0.30.0 — install commands for vLLM 0.30.0 (CUDA 13.0 default wheel; ROCm `+rocm723`); quickstart `uv venv --python 3.12`
- `vllm_omni/profiler/omni_torch_profiler.py` — profiler wrapper
- `vllm_omni/patch.py` — early-import patch registering OmniModelConfig (**removed in v0.20.0**; the old entrypoint hijack was dropped for the 0.20.0 integration path per release notes, rebase PR #3232)
- `vllm_omni/version.py` — version resolution + vLLM alignment check
- `vllm_omni/deploy/*.yaml` — reference deploy configs (111 files at v0.30.0). `qwen3_omni_moe.yaml` (`async_chunk: true`; stage 0 on cuda:0, stages 1+2 on cuda:1), `qwen3_omni_duplex.yaml` (`session_mode: duplex`), `qwen3_tts.yaml` (`model_runner: v2`, platform overrides to v1). Absent: `qwen3_omni_moe_async_chunk.yaml`, `qwen_image.yaml`, `wan2_2_t2v.yaml`
- `examples/online_serving/qwen3_omni/openai_realtime_client.py` — realtime client template; 16 kHz check at line 60, CLI flags `--url --model --input-wav --output-wav --output-text --chunk-ms --send-delay-ms --delta-dump-dir --server-vad --num-requests --concurrency` (v0.30.0)
- `examples/online_serving/qwen3_omni/README.md` — realtime deployment notes; at v0.30.0 states async chunk "enabled by default", `--no-async-chunk` override, and warns against global `--gpu-memory-utilization` on GPU-sharing stages
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

Runtime pins for the current line (checked 2026-10-18): vllm-omni v0.30.0 rides
vLLM 0.30.0 — **PyTorch 2.13.0 / FlashInfer 0.6.18.post1 / torchvision 0.28.0**
(vLLM v0.30.0 `requirements/cuda.txt`) plus `transformers >= 5.13.0, < 5.15`
and `diffusers==0.40.0` (vllm-omni v0.30.0 `requirements/common.txt`).

`references/models.md` tables were spot-checked against v0.30.0
`docs/models/supported_models.md` and `vllm_omni/diffusion/registry.py`
(removed models, LTX rows, pending list, additions banner); the per-row
platform columns were not re-synced.
