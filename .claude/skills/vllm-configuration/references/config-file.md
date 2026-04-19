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
block-size: 16                      # KV block size in tokens
gpu-memory-utilization: 0.9         # fraction of free HBM per rank
swap-space: 4                       # GiB per rank for CPU swap (legacy)
cpu-offload-gb: 0                   # GiB for weights CPU offload (NOT KV)
kv-cache-dtype: auto                # auto | fp8 | fp8_e4m3 | fp8_e5m2
enable-prefix-caching: false
prefix-caching-hash-algo: builtin   # builtin | sha256
num-gpu-blocks-override: null       # force exact block count
```

### ParallelConfig
```yaml
tensor-parallel-size: 1
pipeline-parallel-size: 1
data-parallel-size: 1
distributed-executor-backend: null  # mp | ray | external_launcher
worker-use-ray: false
ray-workers-use-nsight: false
```

### SchedulerConfig
```yaml
max-num-batched-tokens: null        # auto-sized from max-model-len if unset
max-num-seqs: 256
max-num-partial-prefills: 1
max-long-partial-prefills: 1
long-prefill-token-threshold: 0
scheduler-delay-factor: 0.0
enable-chunked-prefill: null        # auto-enabled for long contexts
preemption-mode: null               # recompute | swap
```

### LoRAConfig
```yaml
enable-lora: false
max-loras: 1
max-lora-rank: 16
max-cpu-loras: null
lora-extra-vocab-size: 256
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
disable-log-requests: false
disable-log-stats: false
```

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
disable-frontend-multiprocessing: false
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

## Version notes

- YAML config support: stable since v0.5.0
- Nested dict-to-JSON conversion: enhanced in v0.11 to handle `compilation-config`, `speculative-config`, `kv-transfer-config` reliably
- Boolean handling: pre-v0.10 was inconsistent; current parser requires explicit `true`/`false`
- Issue #8947 (key-order bug): fixed in v0.10.1

## References

- Parser: `vllm/utils/argparse_utils.py`, `FlexibleArgumentParser.load_config_file`
- Docs: https://docs.vllm.ai/en/latest/configuration/serve_args/
- Upstream example: `examples/online_serving/openai_api_server.yaml` (if present in the checkout)
