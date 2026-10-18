# Upgrading a deployment through v0.32.0

Upstream is at **v0.32.0** (2026-10-18), via v0.31.0 (2026-10-05), v0.30.0
(2026-09-22), v0.29.0 and v0.28.0. Changes that affect a deployment manifest or
its rollout plan:

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
  setting it silently does nothing (#54579, #55176, v0.30.0). `vllm launch
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
- **Model Runner V2 is the default for all models** (#53183, v0.29.0). MRV1 is
  deprecated but **still ships in v0.32.0** despite the earlier v0.32 removal
  target, and vLLM still falls back to it for features MRV2 does not cover yet
  (log line: `Model Runner V2 does not yet support …; using the V1 model runner
  instead`; e.g. `--enable-dbo` unless `VLLM_USE_V2_MODEL_RUNNER=1`). v0.32.0
  removed the model-specific ROCm MRV1 exceptions (#56360). A fleet can be split
  across both runners without anyone choosing that; pin `VLLM_USE_V2_MODEL_RUNNER`
  if it matters.
- **FlashInfer all-reduce is on by default** for TP CUDA groups (#52998,
  v0.29.0). Opt out with `VLLM_ALLREDUCE_USE_FLASHINFER=0` if you are pinning
  collective behaviour.
- **New admission-control flags** `--max-num-queued-reqs` and
  `--max-num-queued-tokens` (#49445, v0.29.0) give queue-depth limits that
  previously had to be approximated with autoscaling thresholds.

Do not read v0.28.0's "`max_num_batched_tokens` raised from 8192 to 16384" as a
change to your serving default — it is not. See `vllm-performance-tuning` for
the entrypoint-gated table; on H100/H200 `vllm serve` still starts at 8192.
