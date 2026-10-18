# Stage-config + OmniConnector

Load when an operator is writing or debugging a stage-config YAML, hitting "orchestrator failed to initialize", needing to understand disaggregated execution, or picking an OmniConnector. Source: `vllm_omni/config/stage_config.py`, `vllm_omni/config/model.py`, `vllm_omni/engine/*.py`, `vllm_omni/distributed/omni_connectors/`.

**Contents:** Mental model · Stage-config YAML grammar · Key fields · Pipeline topology validation · OmniConnector types · Disaggregated multi-node setup · Common stage-config mistakes · KV-transfer plumbing for DiT · Example stage configs.

## Mental model

A vllm-omni deployment is a **graph of stages**. Each stage:

- Runs its own engine (LLMEngine or DiffusionEngine).
- Has its own process + GPU allocation.
- Reads inputs from zero or more upstream stages and writes outputs to zero or more downstream stages.
- Communicates through an **OmniConnector** (shared memory for single-host, Mooncake/RDMA for multi-host).

For Qwen3-Omni: `Thinker → Talker → Code2Wav`. For Qwen-Image: `AR text encoder → DiT image generator`. For Qwen3-TTS: `AR code predictor → Code2Wav codec`. The stage config YAML defines the topology.

The paper's central claim: disaggregation enables per-stage scaling independently — e.g., more GPUs on decode-heavy Code2Wav without paying for idle Thinker capacity. Up to 91.4% JCT reduction vs unspecified baseline (arXiv:2602.02204).

## Stage config YAML grammar

Deploy-YAML format since v0.28.0 (the `stage_args:` / `runtime:` / `engine_args:` nesting and `--stage-configs-path` were removed). Topology — `model_stage`, `input_sources`, `engine_output_type`, `final_output`, input-processor funcs — comes from the model's registered pipeline; the deploy YAML carries placement and engine args, flat per stage. Excerpt of `vllm_omni/deploy/qwen3_omni_moe.yaml` at v0.30.0:

```yaml
async_chunk: true              # deploy-wide; --async-chunk / --no-async-chunk override
connectors:
  connector_of_shared_memory:
    name: SharedMemoryConnector
stages:
  - stage_id: 0                # thinker
    devices: "0"
    gpu_memory_utilization: 0.9
    enable_prefix_caching: false
    default_sampling_params: {temperature: 0.0, max_tokens: 2048}
  - stage_id: 1                # talker, shares cuda:1 with stage 2
    devices: "1"
    gpu_memory_utilization: 0.6
    input_connectors: {from_stage_0: connector_of_shared_memory}
platforms:                     # per-platform deltas merged over the stages
  npu: {stages: [{stage_id: 0, tensor_parallel_size: 2, devices: "0,1"}]}
```

Other deploy-level keys: `pipeline` (pick a registered pipeline variant), `session_mode` (`turn` | `duplex`), `model_runner` (`v1` | `v2`), `trust_remote_code`, `edges`.

## Key fields (OmniModelConfig + StageConfig)

| Field | Values | Purpose |
|---|---|---|
| `stage_id` | int | Unique id within pipeline |
| `model_stage` | `thinker`/`talker`/`code2wav`/`ar`/`dit` | Logical role, used by input processors |
| `model_arch` | class name | Registered model class in `vllm_omni/model_executor/models/` |
| `worker_type` | `ar` / `generation` | AR uses LLMEngine; generation uses DiffusionEngine |
| `engine_output_type` | `latent`/`audio`/`image`/`text` | What the stage emits; routes to output processors |
| `hf_config_name` | string \| null | Sub-key in multi-stage HF config for per-stage quant settings |
| `async_chunk` | bool (deploy-level default `true` at v0.30.0) | Chunk-level pipeline overlap. Blocked `/v1/realtime` only on v0.20.x and older |
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

`PipelineConfig.get_validation_errors()` (`stage_config.py:358-382` at v0.30.0, run from `__post_init__`) rejects at load:

- No stages, or duplicate `stage_id`s.
- An `input_sources` entry naming a missing stage, or the stage itself.
- No entry point (stage with empty `input_sources`).
- No terminal stage (`final_output: true`) — without one every request would hang.

Multi-stage cycles beyond self-reference are **not** checked.

If validation fails, the orchestrator raises at init — **before any GPU work** — with a descriptive error. Copy-paste validation errors into issue reports.

## OmniConnector types

Source: `vllm_omni/distributed/omni_connectors/connectors/`.

| Connector | Use when | Source file |
|---|---|---|
| `SharedMemoryConnector` | Single host, multi-GPU (default) | `shm_connector.py` |
| `MooncakeStoreConnector` (alias `MooncakeConnector`) | Multi-host via Mooncake distributed store | `mooncake_store_connector.py` |
| `MooncakeTransferEngineConnector` | RDMA transfer via Mooncake transfer engine | `mooncake_transfer_engine_connector.py` |
| `MoriTransferEngineConnector` | RDMA transfer via MORI | `mori_transfer_engine_connector.py` |
| `NixlConnector` | NIXL transport for full AR/encoder→DiT conditioning payloads (v0.30.0, #6093/#6264) | `nixl_connector.py` |
| `YuanrongConnector`, `YuanrongTransferEngineConnector` | Alternative remote backend | `yuanrong_connector.py`, `yuanrong_transfer_engine_connector.py` |

There is no `RDMAConnector` at v0.28.0+ — RDMA goes through the Mooncake or MORI transfer-engine connectors. Registered names: `vllm_omni/distributed/omni_connectors/factory.py`.

Declare connectors once at deploy level, then wire them per stage:

```yaml
connectors:
  store:
    name: MooncakeStoreConnector
    extra: {host: "<this-node-ip>", master: "<mooncake-master>:50051", metadata_server: "http://<meta>:8080/metadata", proto: tcp}
stages:
  - stage_id: 1
    input_connectors: {from_stage_0: store}   # or output_connectors: {to_stage_1: <name>} on the producer
```

`MooncakeStoreConnector` extras and defaults: `host` 127.0.0.1, `master` 127.0.0.1:50051, `metadata_server`, `segment` 512 MiB, `localbuf` 64 MiB, `proto` tcp, `rdma` device. Native Mooncake **KV** handoff AR→DiT (v0.30.0, #7166) is separate and opt-in: a per-stage `kv_transfer_config` (`kv_connector: MooncakeConnector`, `kv_role`); see `vllm_omni/deploy/hunyuan-image-3-mooncakeconnector.yaml`.

## Disaggregated multi-node setup

Launch pattern:

```bash
# Node 0 (orchestrator + stage 0):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  --omni-master-address 0.0.0.0 --omni-master-port 29500 \
  --stage-id 0 --deploy-config production_stages.yaml

# Node 1 (stage 1 only):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  -oma node0.cluster.internal -omp 29500 \
  --stage-id 1 --deploy-config production_stages.yaml

# Node 2 (stage 2 only):
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --omni \
  -oma node0.cluster.internal -omp 29500 \
  --stage-id 2 --deploy-config production_stages.yaml
```

All nodes must see the same `--deploy-config` YAML (`--stage-configs-path` was removed at v0.28.0). `--replica-id` is deprecated and ignored — the master assigns replica ids. The `MooncakeStoreConnector` (or RDMA) must be configured or KV transfer between nodes will fall back to TCP.

## Common stage-config mistakes

1. **GPU over-allocation**: `gpu_memory_utilization: 0.8` per stage where multiple stages share a GPU → sum > 1.0 → OOM. Either isolate stages to separate GPUs, or shrink per-stage utilization.

2. **Prefix caching + latent output**: setting `enable_prefix_caching: true` on a stage with `engine_output_type: latent` silently corrupts subsequent requests. Always set `enable_prefix_caching: false` for latent stages.

3. **Wrong `hf_config_name` for quantized multi-stage**: when a checkpoint has per-stage quant (modelopt FP8 multi-stage), `hf_config_name` must name the specific sub-config for each stage — otherwise talker/code2wav inherit thinker's quant wrongly. Symptoms: silent accuracy drop on one stage.

4. **BAGEL YAML/docs mismatch (#2635)**: parallel-config field names in the official docs don't match the YAML shape that actually loads. Below v0.30.0 a wrong diffusion field (e.g. `tensor_parallel_size`) was silently dropped by `OmniDiffusionConfig.from_kwargs()`; on v0.30.0+ unknown diffusion fields raise with the field name and stage id (#5172). Cross-check against an existing known-good config in `vllm_omni/deploy/` before copy-paste.

5. **Global engine flags on GPU-sharing stages**: `--gpu-memory-utilization 0.85` on the CLI applies to every stage and oversubscribes a device that two stages share (Qwen3-Omni stages 1+2 on cuda:1). Use `--stage-overrides '{"1": {...}}'` or the YAML.

## KV-transfer plumbing for DiT stages

DiT stages can receive KV from an upstream AR stage (e.g., text-encoder AR → DiT image), which is how `cfg_branch_past_key_values` works. Fields in `OmniDiffusionSamplingParams`:

- `past_key_values`, `kv_metadata` — incoming KV
- `cfg_text_past_key_values`, `cfg_img_past_key_values` — CFG companion KVs
- `need_kv_receive` — blocks until KV arrives

If `need_kv_receive: true` and transfer stalls (broken connector, mis-sized buffer), the DiT stage hangs. Timeout: `--stage-init-timeout` (default 300s per stage) and `--init-timeout` (default 600s overall).

## Example stage configs shipped with the repo

At v0.30.0:

- `qwen3_omni_moe.yaml` — canonical Qwen3-Omni turn deployment (Thinker/Talker/Code2Wav), `async_chunk: true`, serves `/v1/realtime`
- `qwen3_omni_duplex.yaml` — Qwen3-Omni duplex (`session_mode: duplex`); `qwen3_omni_moe_thinking.yaml` — thinker-only
- `qwen3_tts.yaml` (+ `_mrv2`, `_high_concurrency*` variants) — Qwen3-TTS
- `bagel.yaml`, `bagel_single_stage.yaml`, `bagel_think.yaml` — BAGEL
- `wan2_2_ti2v.yaml` — Wan2.2 TI2V

`qwen3_omni_moe_async_chunk.yaml`, `qwen_image.yaml` and `wan2_2_t2v.yaml` do not exist at v0.30.0; single-stage diffusion models need no deploy YAML.

Check `ls vllm_omni/deploy/` in the cloned repo for the current list.
