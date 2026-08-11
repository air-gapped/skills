# YAML config file — full schema

Load when building or debugging a `--config` file. vLLM parses YAML via `FlexibleArgumentParser.load_config_file` (in `vllm/utils/argparse_utils.py`). Every CLI flag has a YAML equivalent; the parser converts YAML keys to `--kebab-case` CLI args internally.

## How parsing works

- **Scalar** (`port: 8000`) → appended as `--port 8000`
- **Boolean** (`enable-prefix-caching: true`) → appended as `--enable-prefix-caching` (true) or omitted (false)
- **List** (`allowed-origins: ["a", "b"]`) → `--allowed-origins a --allowed-origins b`
- **Dict / nested map** (`speculative-config: {model: ..., num_speculative_tokens: 3}`) → JSON-serialized: `--speculative-config '{"model":"...","num_speculative_tokens":3}'`

Keys accept either `hyphen-case` or `snake_case` — matches whichever argparse exposes.

## Precedence

**CLI args > YAML > library defaults.** Env vars (`VLLM_*`) are read separately and do not participate directly in this chain; they gate behaviour at the library layer.

Positional args beat YAML keys of the same name:
```bash
vllm serve /local/path --config prod.yaml
# uses /local/path, NOT whatever `model:` says in prod.yaml
```

## Section catalog

Config groups under the engine are:

### ModelConfig
```yaml
model: meta-llama/Llama-3.1-70B-Instruct
tokenizer: null                     # defaults to model
tokenizer-mode: auto                # auto | slow | mistral
revision: null                      # or a commit SHA / tag
tokenizer-revision: null
code-revision: null                 # for trust-remote-code modules
trust-remote-code: false
dtype: auto                         # auto | half | bfloat16 | float | float32 | ...
max-model-len: null                 # overrides config.json max_position_embeddings
quantization: null                  # awq | gptq | squeezellm | fp8 | bitsandbytes | ...
served-model-name: null             # name surfaced at /v1/models
chat-template: null
allowed-local-media-path: null      # required for file:// image URIs
```

### LoadConfig
```yaml
load-format: auto                   # auto | safetensors | pt | dummy | runai_streamer | tensorizer
download-dir: null                  # where HF cache lands
ignore-patterns: []                 # glob patterns to skip in snapshot_download
model-loader-extra-config: null     # backend-specific dict (runai-streamer tuning)
```

### CacheConfig
```yaml
block-size: null                    # auto-resolved per platform/backend; only set to pin it
gpu-memory-utilization: 0.92        # fraction of free HBM per rank
cpu-offload-gb: 0                   # GiB for weights CPU offload (NOT KV); lives on UVAOffloadConfig
kv-cache-dtype: auto                # auto | fp8 | fp8_e4m3 | fp8_e5m2
enable-prefix-caching: true         # default ON
prefix-caching-hash-algo: sha256    # builtin | sha256
num-gpu-blocks-override: null       # force exact block count
```

### ParallelConfig
```yaml
tensor-parallel-size: 1
pipeline-parallel-size: 1
data-parallel-size: 1
distributed-executor-backend: null  # mp | ray | external_launcher
ray-workers-use-nsight: false
```

### SchedulerConfig
```yaml
max-num-batched-tokens: null        # unset → usage-context default (see note)
max-num-seqs: null                  # unset → usage-context default (see note)
max-num-scheduled-tokens: null      # ≤ max-num-batched-tokens; spec-dec appends beyond it
long-prefill-token-threshold: 0     # 0 disables the long-prompt cap
enable-chunked-prefill: null        # auto-enabled where the model supports it
scheduler-reserve-full-isl: true    # admit only if the full ISL fits in KV — anti-thrash
watermark: 0.0                      # fraction of KV blocks kept free on admission
prefill-schedule-interval: 1        # DP: admit prefills every N steps, aligned across ranks
stream-interval: 1                  # SSE token batching; also a per-request sampling param
scheduling-policy: fcfs             # fcfs | priority
```

**Unset does not mean a fixed number.** `max-num-batched-tokens` / `max-num-seqs`
are filled in by `EngineArgs` from the *usage context* and the device: on a GPU
with ≥70 GiB that is not an A100, `vllm serve` defaults to **8192 / 1024**;
below that threshold, **2048 / 256**. The `SchedulerConfig` class defaults
(2048 / 128) are test conveniences and are not what a server runs with.

### LoRAConfig
```yaml
enable-lora: false
max-loras: 1
max-lora-rank: 16
max-cpu-loras: null
lora-dtype: auto
fully-sharded-loras: false
lora-modules:
  - name: sql-adapter
    path: /models/lora/sql
  - name: summarization
    path: /models/lora/summary
```

### SpeculativeConfig (nested dict)
```yaml
speculative-config:
  model: nvidia/Llama-3.1-70B-Instruct-Eagle3
  num_speculative_tokens: 3
  draft_tensor_parallel_size: 1
  speculative_model_quantization: null
  disable_by_batch_size: null
```

### ObservabilityConfig
```yaml
otlp-traces-endpoint: null          # OTLP/HTTP endpoint for traces
collect-detailed-traces: null       # model | worker | all
disable-log-stats: false
```

Request logging is opt-**in** now: use `enable-log-requests: true` on the
frontend. The old `disable-log-requests` key no longer exists.

### FrontendArgs (server-only, `vllm serve` layer)
```yaml
host: 0.0.0.0
port: 8000
uds: null                           # Unix domain socket path
api-key: null                       # or a list
allow-credentials: false
allowed-origins: ["*"]
allowed-methods: ["*"]
allowed-headers: ["*"]
ssl-keyfile: null
ssl-certfile: null
ssl-ca-certs: null
ssl-cert-reqs: 0
root-path: null                     # for reverse-proxy URL prefix
middleware: []
uvicorn-log-level: info
enable-log-requests: false          # opt-in per-request logging
enable-auto-tool-choice: false
tool-call-parser: null              # hermes | mistral | llama3_json | pythonic | ...
reasoning-parser: null              # deepseek_r1 | qwen3 | granite | ...
enable-offline-docs: false          # serve docs locally (air-gap friendly)
```

### KV transfer / offload (composite config)
```yaml
# Single backend
kv-transfer-config:
  kv_connector: NixlConnector
  kv_role: kv_producer
  kv_buffer_device: cuda

# Multi-backend via MultiConnector
kv-transfer-config:
  kv_connector: MultiConnector
  kv_connector_extra_config:
    connectors:
      - kv_connector: NixlConnector
        kv_role: kv_producer
      - kv_connector: LMCacheConnectorV1
        kv_role: kv_both

# Native CPU offload (v0.11.1+)
kv-offloading-backend: native
kv-offloading-size: 800            # TOTAL across all TP ranks, in GiB
```

See the sibling `vllm-caching` skill for the full KV offload / tiered caching configuration.

## Full production example

```yaml
# prod-llama70b.yaml
# 8x H200, TP=8, prefix caching, CPU offload KV, usage stats disabled

model: /mnt/models/Llama-3.1-70B-Instruct
served-model-name: llama-70b
dtype: bfloat16
tensor-parallel-size: 8
max-model-len: 32768
trust-remote-code: false

# Memory
gpu-memory-utilization: 0.9
kv-cache-dtype: auto
enable-prefix-caching: true
kv-offloading-backend: native
kv-offloading-size: 1600            # 1.6 TB total across TP=8 ranks

# Scheduler
max-num-batched-tokens: 32768
max-num-seqs: 512
enable-chunked-prefill: true

# Server
host: 0.0.0.0
port: 8000
api-key: "${VLLM_API_KEY}"          # env var substitution NOT supported; see note
allowed-origins: ["*"]
uvicorn-log-level: info
enable-auto-tool-choice: true
tool-call-parser: llama3_json
```

**Note on env substitution:** vLLM's YAML parser does not do `${VAR}` substitution. For secrets, set them via env (`VLLM_API_KEY=... vllm serve --config prod.yaml`) rather than inlining in YAML.

## Composition patterns

- **Shared base + per-model overlay:** not natively supported (no `include` mechanism). Use `yq merge` or Helm templating upstream of vLLM.
- **Kustomize / Helm charts** often generate the YAML into a ConfigMap, mount it read-only, and pass `--config /etc/vllm/config.yaml`.
- **Precedence escape:** to override one YAML value at runtime, pass the corresponding CLI flag after `--config`: `vllm serve --config prod.yaml --max-num-seqs 1024`.

## Keys that no longer exist (verified against the v0.27.0 tree)

A YAML key that vLLM no longer recognises is not ignored — argparse rejects it
and the server refuses to start. Every row below was confirmed absent from
`vllm/config/*.py` + `vllm/engine/arg_utils.py` at tag `v0.27.0`.

| Removed key | Removed in | Do this instead |
|---|---|---|
| `max-num-partial-prefills`, `max-long-partial-prefills` | v0.27.0, [PR #49244](https://github.com/vllm-project/vllm/pull/49244) | Nothing — these were V0 fields the V1 oracle already rejected, so they could *only* raise `UnsupportedFeatureError`. Use `long-prefill-token-threshold` alone. |
| `preemption-mode`, `scheduler-delay-factor` | [PR #25334](https://github.com/vllm-project/vllm/pull/25334) (merged 2025-09-21) | V1 always recomputes. For KV pressure use `watermark` / `scheduler-reserve-full-isl`. |
| `swap-space` | [PR #36216](https://github.com/vllm-project/vllm/pull/36216) (merged 2026-03-07); warning cleaned up by [#48549](https://github.com/vllm-project/vllm/pull/48549) | Never allocated in V1 (`num_cpu_blocks` is hardcoded 0) — it only ever backed `best_of`. For real CPU KV tiering see `vllm-caching`. |
| `num-scheduler-steps` | V0 removal | V1 has no multi-step scheduling; use `--async-scheduling`. |
| `worker-use-ray` | V0 removal | `distributed-executor-backend: ray` |
| `lora-extra-vocab-size` | V0 removal | Nothing — LoRA vocab extension is gone. |
| `disable-log-requests` | inverted | `enable-log-requests: true` |
| `disable-frontend-multiprocessing` | V0 removal | Nothing — V1 always runs the frontend out-of-process. |

## Version notes

- Section catalog above re-read key-by-key against tag `v0.27.0` on 2026-08-11
- YAML config support: stable since v0.5.0
- Nested dict-to-JSON conversion: enhanced in v0.11 to handle `compilation-config`, `speculative-config`, `kv-transfer-config` reliably
- Boolean handling: pre-v0.10 was inconsistent; current parser requires explicit `true`/`false`
- Issue #8947 (key-order bug): fixed in v0.10.1

## References

- Parser: `vllm/utils/argparse_utils.py`, `FlexibleArgumentParser.load_config_file`
- Docs: https://docs.vllm.ai/en/latest/configuration/serve_args/
- Upstream example: `examples/online_serving/openai_api_server.yaml` (if present in the checkout)
