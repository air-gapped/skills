# Upgrading a deployment through v0.34.0

Upstream is at **v0.34.0** (2026-11-16). Changes since v0.28.0 that affect a
deployment manifest or its rollout plan:

- **Leave `--gpu-memory-utilization` unset** (#56492, v0.34.0). The KV cache is
  sized from the memory actually free after warmup (extensible KV cache, default
  on CUDA and ROCm) and the unset value resolves to 1.0. Set it only when
  something else shares the GPU, e.g. two engines on one device. Opt out of the
  sizing with `--no-enable-extensible-kv-cache`; the unset default is then 0.92.
  The feature turns itself off for some KV connectors (a connector that shares
  the cache over legacy CUDA IPC, such as LMCache MP, and NIXL, Mooncake or
  MoRI-IO on ROCm). Remove inherited `0.85`/`0.9` values from manifests.
- **Default `--block-size` is 64** (was 16; #63231, v0.34.0). ROCm paged
  attention keeps 16 and an explicit `--block-size` wins. Pass `--block-size 16` to
  keep the old layout (e.g. while prefill and decode pools run different tags).
- **Model Runner V1 is removed** (#63373, v0.34.0). `VLLM_USE_V2_MODEL_RUNNER`
  set to anything but `1` aborts startup (`1` only logs that it is redundant);
  delete it from manifests. Features that fell back to V1 (e.g. `--enable-dbo`)
  now run on V2.
- **A removed env var fails or does nothing.** `VLLM_MARLIN_INPUT_DTYPE` aborts
  startup (use `--quantization humming` with `VLLM_HUMMING_INPUT_QUANT_CONFIG`).
  Any other unknown `VLLM_*` variable, such as the Ray and scale-out names below,
  only logs `Unknown vLLM environment variable detected`.
- **No `-rocm72` images from v0.34.0** (#61939): ROCm images are ROCm 10.0 only
  (`vllm/vllm-openai-rocm:v0.34.0`, alias `vllm/vllm:v0.34.0-rocm`).
- **`huggingface_hub >= 2.0.0`** (with `tokenizers >= 0.23.3`) from v0.34.0
  (#64779): a derived image that pins `huggingface_hub<2` conflicts with it.
- **No CUDA 12.9 image from v0.33.0** (#62575): a manifest pinned to a `-cu129` or
  `-ubuntu2404` tag has no v0.33.0 or v0.34.0 tag to roll to and fails with
  `ImagePullBackOff`. Switch to the plain tag once the node driver supports
  CUDA 13.0; otherwise hold at `v0.32.0-cu129`.
- **Ray tuning env vars are removed** (#61712, #62228, v0.33.0):
  `VLLM_USE_RAY_COMPILED_DAG_CHANNEL_TYPE`, `VLLM_USE_RAY_COMPILED_DAG_OVERLAP_COMM`,
  `VLLM_USE_RAY_WRAPPED_PP_COMM` and `VLLM_USE_RAY_V2_EXECUTOR_BACKEND` went with
  the legacy compiled-graph executor. A manifest still setting them has no
  effect; `--distributed-executor-backend ray` always runs `RayExecutorV2`.
- **`NixlConnector` requires NIXL ≥ 1.5** from v0.33.0 — `references/disagg.md`.
- **CORS is closed by default** (#61009, v0.32.0): `--allowed-origins` now
  defaults to `[]`, so a browser front end calling vLLM directly gets CORS
  errors after the upgrade. Set `--allowed-origins '["https://ui.example"]'`;
  server-to-server clients are unaffected.
- **`--enforce-eager` also disables JIT kernel warmup** from v0.31.0 (#58197)
  unless fault tolerance is on — the first requests pay the kernel JIT instead
  of the boot. See `references/pod-shape.md` §Serve-args review.
- **Fast Start daemon is launched with `vllm preload`** and supports DP and PP
  from v0.31.0/v0.32.0 — `references/pod-shape.md` §Fast Start.
- **Scale-out endpoints (`/render`, `/derender`, `/inference/v1/generate`) are
  opt-in on plain `vllm serve`.** Pass `--enable-scale-out`; the old
  `VLLM_ENABLE_SCALE_OUT_ENDPOINTS` env var is removed, so a manifest still
  setting it has no effect (#54579, #55176, v0.30.0). `vllm launch
  render` and `vllm serve --tokens-only` still register their endpoints
  unconditionally.
- **`python -m vllm.entrypoints.grpc_server` is deprecated** in favour of
  `vllm serve --grpc` (#56746, v0.30.0) — same fix as the api_server line
  below if a container `command:` still spells the module form.
- **YaRN-scaled `max_model_len` can drop on upgrade.** vLLM stops
  re-multiplying an already-scaled `max_position_embeddings` by `factor` for
  yarn-family rope types (#56446, v0.30.0); a manifest with a hardcoded
  `--max-model-len` derived from the old (inflated) value needs recomputing,
  not carrying forward.
- **`python -m vllm.entrypoints.openai.api_server` is deprecated** in favour of
  `vllm serve` (#52131, v0.29.0). If a container `command:` still spells the
  module form, change it now rather than on the release that removes it.
- **FlashInfer all-reduce is on by default** for TP CUDA groups (#52998,
  v0.29.0). Opt out with `VLLM_ALLREDUCE_USE_FLASHINFER=0` to keep collective
  behaviour pinned across the upgrade.
- **New admission-control flags** `--max-num-queued-reqs` and
  `--max-num-queued-tokens` (#49445, v0.29.0) give queue-depth limits that
  previously had to be approximated with autoscaling thresholds.

Do not read v0.28.0's "`max_num_batched_tokens` raised from 8192 to 16384" as a
change to the `vllm serve` default — it is not. See `vllm-performance-tuning` for
the entrypoint-gated table; on H100/H200 `vllm serve` still starts at 8192.
