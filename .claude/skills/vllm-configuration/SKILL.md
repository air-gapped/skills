---
name: vllm-configuration
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Configure vLLM completely — YAML config file format, CLI arg precedence, full VLLM_*/HF_*/TRANSFORMERS_* env-var catalog, end-to-end recipe for air-gapped environments (internal HF mirrors, hf-mirror.com, ModelScope, HF_HUB_OFFLINE with pre-seeded cache, gated models offline, trust_remote_code supply-chain implications). VLLM_HOST_IP vs API-host confusion, Kubernetes-service-named-`vllm` env-var poisoning, usage-stats triple opt-out, YAML precedence surprises.
when_to_use: |-
  Trigger on "vllm config", "vllm yaml config", "vllm env vars", "env vars for vllm", "env catalog", "VLLM_USE_MODELSCOPE", "VLLM_HOST_IP", "HF_HUB_OFFLINE", "HF_ENDPOINT", "TRANSFORMERS_OFFLINE", "vllm air-gapped", "vllm offline", "hf-mirror", "ModelScope", "pre-seed HF cache", "vllm trust remote code", "stats.vllm.ai", "--config yaml", "gated model offline", "HF_TOKEN offline". Where settings live (CLI flag vs YAML vs env var), precedence, pinning model revisions, internal HF reverse proxy / Artifactory mirror. Also first-boot network errors, mirror setup, "why does vLLM hit huggingface.co when I gave it a local path". Also implicit-vllm contexts — "audit model X", "audit open-weight", "deploy-memo", "serve args", "serve_args", "`vllm serve` args", "required_deploy", "check prior configs", "cross-check flags", "flag drift", "env config for {model}", "spec-study vllm" — authoring/reviewing per-model deploy recipes whose fields map to vLLM flags/env vars.
---

# vLLM configuration

Target audience: operators deploying vLLM in production — datacenter GPUs, containerized, often inside networks that can't reach `huggingface.co` directly and need to use internal mirrors or fully offline caches.

## Why this matters

vLLM's config surface is deceptively layered: CLI flags, a YAML `--config` file, `VLLM_*` env vars, and the HuggingFace / Transformers env vars it inherits transparently. The same setting can exist in three places, and the precedence ordering is not intuitive. Getting this wrong produces three classic failure modes:

1. **First-boot network errors** — operator pre-downloaded weights to a local path, but vLLM still hits `huggingface.co` for a revision check, a missing tokenizer file, or usage stats. The "local path" illusion is incomplete.
2. **Env-var namespace collisions** — a Kubernetes Service named `vllm` injects `VLLM_SERVICE_HOST` / `VLLM_SERVICE_PORT` into every pod, which silently overrides `VLLM_HOST_IP` / `VLLM_PORT`. vLLM's *internal distributed* init then uses the k8s cluster IP and breaks.
3. **`VLLM_HOST_IP` as an API host** — operators alias `--host $VLLM_HOST_IP` assuming symmetry with the API server. `VLLM_HOST_IP` is the **internal inter-worker bind address**, not the OpenAI-compat server host. Using it as the API host breaks TP/PP distributed init.

The fix in every case is understanding the layering. This skill teaches that layering, then gives the operator-facing knobs, then the air-gapped recipe.

## Precedence, in one sentence

**CLI arg > `--config FILE.yaml` > `VLLM_*` env var > library default.**

So `vllm serve /models/llama --config prod.yaml` uses `/models/llama` even if `prod.yaml` sets `model: meta-llama/Llama-3.1-8B`. And `VLLM_LOGGING_LEVEL=DEBUG` is overridden by `--log-level=INFO`.

One non-obvious case: env vars that *vLLM reads directly* (like `HF_HUB_OFFLINE`) are consumed by the library layer, not the arg parser, so they aren't subject to this precedence — they gate behaviour unconditionally.

## The YAML config file

Every CLI flag has a YAML equivalent. Keys use the same name, hyphens allowed or underscored. Booleans must be explicit (`true`/`false`, not YAML's loose `yes`/`on`).

```yaml
# prod.yaml
model: /mnt/models/Llama-3.1-70B-Instruct
tensor-parallel-size: 4
gpu-memory-utilization: 0.9
max-model-len: 32768
dtype: bfloat16
enable-prefix-caching: true
served-model-name: llama-70b

# Nested composite configs — YAML dict becomes a JSON string on the CLI
speculative-config:
  model: nvidia/Llama-3.1-70B-Instruct-Eagle3
  num_speculative_tokens: 3
compilation-config:
  pass_config:
    fuse_allreduce_rms: true
```

```bash
vllm serve --config prod.yaml
```

**Gotchas:**
- `list` args become YAML sequences (`allowed-origins: ["http://a", "http://b"]`).
- Dict args (`--kv-transfer-config`, `--speculative-config`, `--compilation-config`) can be written as YAML dicts; the parser serializes to JSON before handing to the CLI layer.
- Older versions had a key-order bug (issue #8947) where `served-model-name` placed last could break parsing. Fixed on current main, but still seen on v0.10–v0.11 images.
- `trust_remote_code` in YAML: `trust-remote-code: true` (explicit boolean).

For the full per-section catalog (ModelConfig, CacheConfig, ParallelConfig, SchedulerConfig, LoadConfig, LoRAConfig, SpeculativeConfig, ObservabilityConfig, FrontendArgs), see `references/config-file.md`.

## Environment variables — the operator-facing subset

Full catalog in `references/env-vars.md`. The ones that matter most in production:

**Storage / cache (persist these):**
- `VLLM_CACHE_ROOT` (default `~/.cache/vllm`) — Torch compile, Triton, XLA, assets. Mount on PVC; otherwise the compile tax is paid every pod restart.
- `HF_HOME` (default `~/.cache/huggingface`) — HuggingFace hub cache. Preferred over the deprecated `TRANSFORMERS_CACHE`.
- `HF_HUB_CACHE` — subdir under `HF_HOME`, rarely set directly.

**Air-gap control:**
- `HF_HUB_OFFLINE=1` — **required** in air-gapped mode. Without it, vLLM hits HF on every startup to check for newer revisions, even with a warm cache. (vLLM CI itself adopted `HF_HUB_OFFLINE=1` to avoid this — issue #23451, closed 2025-11-26.)
- `TRANSFORMERS_OFFLINE=1` — set both; some transformers-layer code paths honour only this one.
- `HF_ENDPOINT=https://hf-mirror.com` — redirect all HF traffic to a mirror. **No trailing slash** or it breaks.
- `VLLM_USE_MODELSCOPE=true` — route base-model downloads to ModelScope. Known gap: LoRA adapters still try HuggingFace. PR #13220 attempted the fix but was closed unmerged (2025-06-20); no upstream fix has landed. Workaround: download LoRA adapters manually, pass `--lora-modules name=/local/path`.
- `HF_TOKEN` — **still required offline for gated repos** (meta-llama/*, google/gemma*). vLLM validates access through the hub config layer before weight loading even when weights are local (issue #9255).

**Telemetry (disable in air-gap):**
- `VLLM_NO_USAGE_STATS=1` **or** `VLLM_DO_NOT_TRACK=1` **or** `DO_NOT_TRACK=1` **or** touch `$HOME/.config/vllm/do_not_track`. Default endpoint is `https://stats.vllm.ai`. In air-gap, connection errors in logs result otherwise.

**Networking (internal — read the warning below):**
- `VLLM_HOST_IP` — **internal inter-worker bind IP for distributed (TP/PP/DP) init**. NOT the API server host. Use `--host` on the CLI for the API server.
- `VLLM_PORT` — internal base port for distributed; auto-increments for each worker. NOT the API server port. Use `--port`.

**Server auth:**
- `VLLM_API_KEY` — Bearer token for the OpenAI-compat server. Equivalent to `--api-key` on the CLI.

**Long-context / safety overrides:**
- `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` — bypasses the model's `max_position_embeddings` sanity check. Footgun — usually means the rope scaling config doesn't match the served weights.
- `VLLM_ALLOW_INSECURE_SERIALIZATION=1` — permits unsafe serialization formats over the wire. Never enable on multi-tenant.

**Logging:**
- `VLLM_LOGGING_LEVEL=DEBUG|INFO|WARN|ERROR`, `VLLM_LOGGING_PREFIX="rank0: "`, `VLLM_CONFIGURE_LOGGING=0` (let the host app own config).

## Air-gapped operation — the short recipe

Full recipe in `references/air-gapped.md`. The essentials:

1. **Pre-stage on a connected host:**
   ```bash
   # new hf CLI
   HF_HOME=/export/hf hf download meta-llama/Llama-3.1-70B-Instruct
   # or python
   python -c "from huggingface_hub import snapshot_download; \
     snapshot_download('meta-llama/Llama-3.1-70B-Instruct', local_dir='/export/models/llama-70b')"
   ```

2. **Transfer** the directory into the enclave (rsync, physical media, MinIO, whatever the security posture allows).

3. **Pick one of three patterns:**

   **A. Fully offline with local path (simplest, recommended):**
   ```bash
   export HF_HOME=/mnt/hf-cache
   export HF_HUB_OFFLINE=1
   export TRANSFORMERS_OFFLINE=1
   export VLLM_NO_USAGE_STATS=1
   vllm serve /mnt/models/llama-70b --tensor-parallel-size 8
   ```

   **B. Internal HF mirror (reverse proxy):**
   ```bash
   export HF_ENDPOINT=https://hf.internal.example.com   # NO trailing slash
   export HF_TOKEN=<internal-bot-token>                  # mirror may still gate
   vllm serve meta-llama/Llama-3.1-70B-Instruct --tensor-parallel-size 8
   ```

   **C. ModelScope (Chinese / restricted networks):**
   ```bash
   export VLLM_USE_MODELSCOPE=true
   vllm serve qwen/Qwen2-72B-Instruct --trust-remote-code --tensor-parallel-size 8
   ```
   Caveat: LoRA adapters historically still fetched from HF even with this flag.

4. **For gated models**, `HF_TOKEN` must be in the pod environment even when weights are local — it gates the config-validation path.

## Critical pitfalls

1. **Kubernetes Service named `vllm` poisons env vars.** Kubernetes injects `<SERVICE>_SERVICE_HOST` / `<SERVICE>_SERVICE_PORT` into every pod in the namespace. A Service named `vllm` collides with vLLM's `VLLM_` namespace and in some versions interferes. The vLLM docs explicitly warn against naming the service `vllm`. Name it `vllm-api` or `inference` instead.

2. **`VLLM_HOST_IP` is not the API host.** It's the internal distributed bind address. Aliasing `--host $VLLM_HOST_IP` on the CLI breaks inter-worker init. API server host goes on `--host`; internal goes on the env var.

3. **`HF_HUB_OFFLINE=1` needs the cache fully populated or first-request fails.** Include `config.json`, `tokenizer*`, `special_tokens_map.json`, `generation_config.json`, and any `modeling_*.py` referenced by `auto_map` — not just weights.

4. **Gated models offline still need `HF_TOKEN`.** The token is consulted during hub-config validation before weight load. Putting it only on the staging host isn't enough; bake it into the runtime env.

5. **`trust_remote_code` executes arbitrary Python from the model repo.** Any model not in vLLM's hard-coded architecture registry falls through to `AutoConfig` + `auto_map`, which only runs with the flag. In air-gap this runs pre-staged code — treat model directory provenance as equivalent to running arbitrary binaries. Verify checksums.

6. **`TRANSFORMERS_CACHE` is deprecated.** Rename legacy scripts to use `HF_HOME` (and let `HF_HUB_CACHE` default). Setting the old var still works but emits `FutureWarning`.

7. **YAML CLI positional beats config `model:`.** `vllm serve /local/path --config prod.yaml` uses `/local/path` regardless of what `prod.yaml` says. Intentional but surprising.

8. **Revision pinning: `--revision` applies to model weights; `--tokenizer-revision` is separate.** Pinning the model to a commit but leaving the tokenizer floating lets it drift, and token counts change subtly. Pin both.

9. **`load-format dummy` for profiling.** Skips weight download entirely, materializes random weights. Useful for measuring startup / attention kernel perf in air-gap before weights arrive. Don't ship with this. Sibling flag `--load-format fastsafetensors` accelerates safetensors load via batched pread + NUMA-aware buffers (requires `fastsafetensors>=0.2.2` + `libnuma-dev`; no env-var toggle exists in vLLM source).

10. **Torch compile cache misses cost minutes per startup.** Persist `VLLM_CACHE_ROOT` across pod restarts (PVC, hostPath, or a shared NFS mount). First warmup of a new model config rebuilds CUDA graphs and torch.compile artifacts; subsequent starts hit cache.

For more failure modes and the fuller troubleshooting flow (first-boot hang, revision-check failure detection, tokenizer mismatch diagnosis), see `references/troubleshooting.md`.

## Verifying a configuration

Before shipping, sanity-check the effective config:

```bash
# Grep the startup log — vLLM prints the resolved EngineConfig in the first 200 lines
kubectl logs <pod> --tail=400 | grep -A 40 'EngineConfig\|EngineArgs'

# Hit /metrics to confirm prefix caching, block size, KV dtype are live
curl -s http://localhost:8000/metrics | grep -E 'prefix_cache|gpu_cache|kv_cache'

# Confirm the model path that was actually loaded
curl -s http://localhost:8000/v1/models | jq '.data[].id'
```

`${CLAUDE_SKILL_DIR}/scripts/check-config.sh` bundles these checks — run it against a staged server to verify the config landed as intended.

## External references

- Env vars (authoritative): https://docs.vllm.ai/en/stable/configuration/env_vars/
- Engine args: https://docs.vllm.ai/en/latest/configuration/engine_args/
- Serve args + YAML config: https://docs.vllm.ai/en/latest/configuration/serve_args/
- CLI: https://docs.vllm.ai/en/stable/cli/
- HF integration design: https://github.com/vllm-project/vllm/blob/main/docs/design/huggingface_integration.md
- Air-gapped thread: https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916
- Offline discussion: https://github.com/vllm-project/vllm/discussions/1405
- Blog — Anatomy of vLLM: https://vllm.ai/blog/anatomy-of-vllm
- Sibling skills: `vllm-caching` (KV tiering + offload config), `vllm-benchmarking` (bench methodology + output JSON)
