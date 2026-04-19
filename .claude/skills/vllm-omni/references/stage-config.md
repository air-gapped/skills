# Stage-config + OmniConnector

Load when an operator is writing or debugging a stage-config YAML, hitting "orchestrator failed to initialize", needing to understand disaggregated execution, or picking an OmniConnector. Source: `vllm_omni/config/stage_config.py`, `vllm_omni/config/model.py`, `vllm_omni/engine/*.py`, `vllm_omni/distributed/omni_connectors/`.

## Mental model

A vllm-omni deployment is a **graph of stages**. Each stage:

- Runs its own engine (LLMEngine or DiffusionEngine).
- Has its own process + GPU allocation.
- Reads inputs from zero or more upstream stages and writes outputs to zero or more downstream stages.
- Communicates through an **OmniConnector** (shared memory for single-host, Mooncake/RDMA for multi-host).

For Qwen3-Omni: `Thinker → Talker → Code2Wav`. For Qwen-Image: `AR text encoder → DiT image generator`. For Qwen3-TTS: `AR code predictor → Code2Wav codec`. The stage config YAML defines the topology.

The paper's central claim: disaggregation enables per-stage scaling independently — e.g., more GPUs on decode-heavy Code2Wav without paying for idle Thinker capacity. Up to 91.4% JCT reduction vs unspecified baseline (arXiv:2602.02204).

## Stage config YAML grammar

Canonical layout from `vllm_omni/model_executor/stage_configs/qwen3_omni_moe.yaml`:

```yaml
stage_args:
  - stage_id: 0
    runtime:
      process: true
      devices: "0"            # CUDA_VISIBLE_DEVICES for this stage
    engine_args:
      model_stage: thinker    # Logical role: thinker|talker|code2wav|ar|dit
      model_arch: Qwen3OmniMoeForConditionalGeneration
      worker_type: ar          # ar (autoregressive) | generation (diffusion)
      scheduler_cls: vllm_omni.core.sched.omni_ar_scheduler.OmniARScheduler
      gpu_memory_utilization: 0.8
      enforce_eager: true
      trust_remote_code: true
      engine_output_type: latent  # latent | audio | image | text
      enable_prefix_caching: false  # MUST be false when output is latent
    is_comprehension: true     # true → tokenizer will be loaded for this stage
    final_output: true         # part of the user-visible response
    final_output_type: text
    default_sampling_params:
      temperature: 0.0
      top_p: 1.0
      max_tokens: 2048
      seed: 42

  - stage_id: 1
    engine_input_source: [0]   # input comes from stage 0
    custom_process_input_func: vllm_omni.model_executor.stage_input_processors.qwen3_omni.prepare_talker_input
    runtime:
      process: true
      devices: "1"
    engine_args:
      model_stage: talker
      model_arch: Qwen3OmniMoeForConditionalGeneration
      worker_type: ar
      engine_output_type: latent

runtime:
  enabled: true
  edges:                       # explicit dependency: stage 1 waits on stage 0
    - from: 0
      to: 1
```

## Key fields (OmniModelConfig + StageConfig)

| Field | Values | Purpose |
|---|---|---|
| `stage_id` | int | Unique id within pipeline |
| `model_stage` | `thinker`/`talker`/`code2wav`/`ar`/`dit` | Logical role, used by input processors |
| `model_arch` | class name | Registered model class in `vllm_omni/model_executor/models/` |
| `worker_type` | `ar` / `generation` | AR uses LLMEngine; generation uses DiffusionEngine |
| `engine_output_type` | `latent`/`audio`/`image`/`text` | What the stage emits; routes to output processors |
| `hf_config_name` | string \| null | Sub-key in multi-stage HF config for per-stage quant settings |
| `async_chunk` | bool (default `false`) | Enable chunk-level pipeline overlap. **`true` breaks `/v1/realtime`.** |
| `task_type` | `CustomVoice`/`VoiceDesign`/`Base` | Qwen3-TTS mode |
| `codec_frame_rate_hz` | float | Audio codec sample rate |
| `stage_connector_config` | dict | Connector choice + extras |
| `is_comprehension` | bool | Whether this stage loads a tokenizer |
| `final_output` | bool | Stage's output is user-visible |
| `final_output_type` | `text`/`audio`/`image`/`video` | Output modality |
| `input_sources` | list[int] | Upstream stage IDs (empty list = entry point) |
| `custom_process_input_func` | string | Python path to input transform (e.g. tokenize talker input from thinker latents) |
| `custom_process_next_stage_input_func` | string | Output-side hook |
| `yaml_engine_args` | dict | Forwarded to LLMEngine (`gpu_memory_utilization`, `enforce_eager`, `tensor_parallel_size`, etc.) |
| `yaml_runtime` | dict | `process`, `devices` |
| `yaml_extras` | dict | `default_sampling_params`, output/input connectors, `tts_args` |
| `runtime_overrides` | dict | CLI overrides (merged at load time) |

## Pipeline topology validation

`stage_config.py:184-200` enforces at load:

- At least one stage with empty `input_sources` (entry point).
- All `input_sources` must reference valid `stage_id`s.
- No circular dependencies.

If validation fails, the orchestrator raises at init — **before any GPU work** — with a descriptive error. Copy-paste validation errors into issue reports.

## OmniConnector types

Source: `vllm_omni/distributed/omni_connectors/connectors/`.

| Connector | Use when | Source file |
|---|---|---|
| `SharedMemoryConnector` | Single host, multi-GPU (default) | `shm_connector.py` |
| `MooncakeStoreConnector` | Multi-host via Mooncake distributed KV store | `mooncake_store_connector.py` |
| `MooncakeTransferEngineConnector` | KV-only transfer via Mooncake | `mooncake_transfer_engine_connector.py` |
| `RDMAConnector` | RDMA between nodes (v0.16 #1019) | `rdma_connector.py` |
| `YuanrongConnector` | Alternative remote backend | `yuanrong_connector.py` |

Configuration lives under each stage's `stage_connector_config`:

```yaml
stage_connector_config:
  name: "SharedMemoryConnector"
  extra: {}
```

Or for multi-host:

```yaml
stage_connector_config:
  name: "MooncakeStoreConnector"
  extra:
    mooncake_master: "mooncake.internal:7777"
    buffer_size_gb: 32
```

## Disaggregated multi-node setup

Launch pattern:

```bash
# Node 0 (orchestrator + stage 0):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  --omni-master-address 0.0.0.0 --omni-master-port 29500 \
  --stage-id 0 --stage-configs-path production_stages.yaml

# Node 1 (stage 1 only):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  -oma node0.cluster.internal -omp 29500 \
  --stage-id 1 --stage-configs-path production_stages.yaml

# Node 2 (stage 2 only):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  -oma node0.cluster.internal -omp 29500 \
  --stage-id 2 --stage-configs-path production_stages.yaml
```

All nodes must see the same `--stage-configs-path` YAML. The `MooncakeStoreConnector` (or RDMA) must be configured or KV transfer between nodes will fall back to TCP.

## Common stage-config mistakes

1. **GPU over-allocation**: `gpu_memory_utilization: 0.8` per stage where multiple stages share a GPU → sum > 1.0 → OOM. Either isolate stages to separate GPUs, or shrink per-stage utilization.

2. **Prefix caching + latent output**: setting `enable_prefix_caching: true` on a stage with `engine_output_type: latent` silently corrupts subsequent requests. Always set `enable_prefix_caching: false` for latent stages.

3. **Wrong `hf_config_name` for quantized multi-stage**: when a checkpoint has per-stage quant (modelopt FP8 multi-stage), `hf_config_name` must name the specific sub-config for each stage — otherwise talker/code2wav inherit thinker's quant wrongly. Symptoms: silent accuracy drop on one stage.

4. **BAGEL YAML/docs mismatch (#2635)**: parallel-config field names in the official docs don't match the YAML shape that actually loads. Cross-check against an existing known-good config in `vllm_omni/model_executor/stage_configs/` before copy-paste.

5. **Swap between `qwen3_omni_moe.yaml` and `..._async_chunk.yaml`**: if realtime is required, do **not** use the async-chunk variant — `async_chunk: true` causes `/v1/realtime` to reject at connection.

## KV-transfer plumbing for DiT stages

DiT stages can receive KV from an upstream AR stage (e.g., text-encoder AR → DiT image), which is how `cfg_branch_past_key_values` works. Fields in `OmniDiffusionSamplingParams`:

- `past_key_values`, `kv_metadata` — incoming KV
- `cfg_text_past_key_values`, `cfg_img_past_key_values` — CFG companion KVs
- `need_kv_receive` — blocks until KV arrives

If `need_kv_receive: true` and transfer stalls (broken connector, mis-sized buffer), the DiT stage hangs. Timeout: `--stage-init-timeout` (default 300s per stage) and `--init-timeout` (default 600s overall).

## Example stage configs shipped with the repo

- `qwen3_omni_moe.yaml` — canonical realtime-compatible Qwen3-Omni (Thinker/Talker/Code2Wav)
- `qwen3_omni_moe_async_chunk.yaml` — high-throughput Qwen3-Omni, realtime-incompatible
- `qwen_image.yaml` — AR text encoder + DiT image stage
- `bagel.yaml` — BAGEL DiT-only (v0.14 layout)
- `wan2_2_t2v.yaml` — Wan2.2 T2V disagg

Check `ls vllm_omni/model_executor/stage_configs/` in the cloned repo for the current list.
