# vLLM environment variables — full catalog

Load when the operator needs to look up a specific env var or survey what's configurable. Source of truth is `vllm/envs.py` (verify against the installed version — this table reflects v0.18–v0.20).

The docs page at https://docs.vllm.ai/en/stable/configuration/env_vars/ is literally generated from `vllm/envs.py` via an `--8<--` include, so both are the same list.

## Quick-grouping

- **Storage / cache** — where models, compile artifacts, assets live
- **Network / distributed** — internal worker-to-worker plumbing (NOT the API server)
- **Server auth / behaviour** — OpenAI-compat surface
- **Hugging Face integration** — inherited from `huggingface_hub` / `transformers`
- **Telemetry** — usage stats phone-home
- **Logging & debug**
- **Compile / kernel tuning**
- **Experimental / safety overrides** — footguns

## Storage / cache

| Variable | Default | Purpose | Set when |
|---|---|---|---|
| `VLLM_CACHE_ROOT` | `~/.cache/vllm` | Root for Torch compile cache, Triton, XLA, assets | Multi-user node; persist across pod restarts (PVC / hostPath) |
| `VLLM_ASSETS_CACHE` | `$VLLM_CACHE_ROOT/assets` | Cached datasets, benchmark fixtures | Offline MM workloads |
| `VLLM_XLA_CACHE_PATH` | `$VLLM_CACHE_ROOT/xla_cache` | TPU XLA compile cache | TPU deployments |
| `VLLM_MEDIA_CACHE` | `""` | MM input cache (images/video) | Offline MM serving; avoid re-downloading request media |
| `VLLM_MEDIA_CACHE_MAX_SIZE_MB` | `5120` | Media cache size cap | Disk-constrained deployments |

## Network / distributed (internal plumbing)

| Variable | Default | Purpose | Set when |
|---|---|---|---|
| `VLLM_HOST_IP` | `""` | **Internal** distributed bind IP (worker-to-worker TP/PP/DP) | Multi-node deployments where auto-detect picks the wrong interface |
| `VLLM_PORT` | unset (auto) | **Internal** base port; each worker takes an incremented port | Port conflicts / firewall rules |
| `VLLM_RPC_TIMEOUT` | `10000` (ms) | RPC call timeout between engine & workers | Slow networks / large TP groups |
| `VLLM_ENGINE_ITERATION_TIMEOUT_S` | `60` | Per-iteration timeout; over this, worker is deemed stuck | Very large batches; long prefill |
| `VLLM_ENGINE_READY_TIMEOUT_S` | `600` | Max time to wait for engine startup | Large models (70B+) on slow storage |
| `VLLM_HTTP_TIMEOUT_KEEP_ALIVE` | `5` (s) | API server keep-alive | Tuning |
| `VLLM_WORKER_MULTIPROC_METHOD` | `fork` | `fork` or `spawn` | Windows/macOS, Ray-controlled containers |

**Critical:** `VLLM_HOST_IP` / `VLLM_PORT` are **not** the API server host/port. Use `--host` / `--port` on the CLI for the OpenAI-compat server.

## Distributed (DP-specific)

| Variable | Default | Purpose | Set when |
|---|---|---|---|
| `VLLM_DP_RANK` | `0` | Data-parallel rank | Multi-replica DP |
| `VLLM_DP_RANK_LOCAL` | `-1` | Local DP rank within node | Debugging placement |
| `VLLM_DP_SIZE` | `1` | Total DP replicas | DP inference |
| `VLLM_DP_MASTER_IP` | `""` | DP coordinator IP | Multi-node DP |
| `VLLM_DP_MASTER_PORT` | `0` | DP coordinator port | Multi-node DP |
| `VLLM_RAY_DP_PACK_STRATEGY` | `strict` | `strict` / `fill` / `span` — how Ray packs DP workers onto nodes | Ray-based DP deployments |

## Server auth / OpenAI-compat surface

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_API_KEY` | unset | Bearer token the server requires; equivalent to CLI `--api-key` |
| `VLLM_SERVER_DEV_MODE` | `0` | Enables dev-only endpoints (`/reset_prefix_cache`, etc.). **Never set in production.** |
| `VLLM_ALLOW_RUNTIME_LORA_UPDATING` | `0` | Allows runtime `load_lora_adapter` via admin endpoint |

## Hugging Face integration (inherited)

| Variable | Default | Purpose |
|---|---|---|
| `HF_HOME` | `~/.cache/huggingface` | Canonical HF root. **Preferred pre-seed target.** |
| `HF_HUB_CACHE` | `$HF_HOME/hub` | Model cache subdir |
| `TRANSFORMERS_CACHE` | `$HF_HOME/hub` | **Deprecated alias** for `HF_HUB_CACHE`; emits FutureWarning |
| `HUGGINGFACE_HUB_CACHE` | unset | Explicit override; wins over `HF_HUB_CACHE` |
| `HF_ENDPOINT` | `https://huggingface.co` | Redirect target for all HF API calls. **No trailing slash.** |
| `HF_TOKEN` | unset | Gated-repo access token; required even offline for gated models (issue #9255) |
| `HUGGING_FACE_HUB_TOKEN` | unset | Older alias for `HF_TOKEN`; both read |
| `HF_HUB_OFFLINE` | `0` | Set `1` for fully offline operation |
| `TRANSFORMERS_OFFLINE` | `0` | Parallel flag; some transformers paths honor only this |

## vLLM-specific model source

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_USE_MODELSCOPE` | `false` | Route base-model downloads to ModelScope (`modelscope.cn`) |
| `VLLM_LORA_RESOLVER_CACHE_DIR` | `None` | Dir where resolved LoRA adapters are kept |
| `VLLM_LORA_RESOLVER_HF_REPO_LIST` | `None` | Comma-separated whitelist of HF repos for LoRA; air-gap hardening |

## Telemetry (disable in air-gap)

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_USAGE_STATS_SERVER` | `https://stats.vllm.ai` | Phone-home endpoint |
| `VLLM_NO_USAGE_STATS` | `0` | Set `1` to disable |
| `VLLM_DO_NOT_TRACK` | `false` | Set `true`/`1` to disable |
| `DO_NOT_TRACK` | `0` | `dnt.sh` standard; also honoured |
| `VLLM_USAGE_SOURCE` | `production` | Free-form tag in the payload |

Belt-and-braces: set **both** `VLLM_NO_USAGE_STATS=1` and `VLLM_DO_NOT_TRACK=1`, or simply `touch $HOME/.config/vllm/do_not_track`.

## Logging & debug

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_LOGGING_LEVEL` | `INFO` | Verbosity |
| `VLLM_LOGGING_PREFIX` | `""` | Prepended to every line — useful for multi-replica log grep |
| `VLLM_LOGGING_COLOR` | `auto` | Set `0` when piping to files |
| `VLLM_LOGGING_STREAM` | `ext://sys.stdout` | Target stream |
| `VLLM_LOGGING_CONFIG_PATH` | unset | Path to a JSON logging config |
| `VLLM_CONFIGURE_LOGGING` | `1` | Set `0` if the embedding host app owns logging config |
| `VLLM_LOG_STATS_INTERVAL` | `10.0` (s) | Perf-stats cadence; `-1` to disable |
| `VLLM_TRACE_FUNCTION` | `0` | Function-level tracing; very noisy, use only when debugging |

## Compile / kernel tuning

| Variable | Default | Purpose |
|---|---|---|
| `VLLM_DISABLE_COMPILE_CACHE` | `False` | Force rebuild of torch.compile artifacts |
| `VLLM_USE_AOT_COMPILE` | dynamic | Ahead-of-time compile path (Torch 2.10+) |
| `VLLM_USE_MEGA_AOT_ARTIFACT` | dynamic | Single-file precompiled bundle (Torch 2.12+) |
| `VLLM_TARGET_DEVICE` | `cuda` | `cuda` / `cpu` / `tpu` / `xpu` / `rocm` |
| `VLLM_MAIN_CUDA_VERSION` | `13.0` | CUDA version of precompiled wheels (bumped from 12.9 to 13.0 in 2026 wheels; follows PyTorch, overridable) |
| `VLLM_USE_DEEP_GEMM` | `1` on Hopper+ | Enable DeepGEMM FP8 kernel path. See `vllm-nvidia-hardware` → `gemm-backends.md` |
| `VLLM_USE_DEEP_GEMM_E8M0` | `0` | Pack FP8 scales as E8M0 (Hopper FP8 E4M3 only — faster, tiny accuracy cost) |
| `DG_JIT_CACHE_DIR` | `~/.cache/deep_gemm` | DeepGEMM JIT kernel cache. **Mount as PVC** — avoids per-pod warm-up tax (200-800 ms/shape) |

## Experimental / safety overrides (footguns)

| Variable | Default | Effect | Why it's dangerous |
|---|---|---|---|
| `VLLM_ALLOW_LONG_MAX_MODEL_LEN` | `0` | Set `1` to bypass `max_position_embeddings` sanity check | Usually indicates wrong rope scaling config; silent quality degradation |
| `VLLM_ALLOW_INSECURE_SERIALIZATION` | `0` | Permits unsafe serialization formats on RPC wire | Code execution risk; never in multi-tenant |
| `VLLM_SKIP_P2P_CHECK` | `0` | Skip peer-to-peer GPU access validation | May silently disable NVLink, performance cliff |

## Table lookup tips

- To dump the full current list from a running deployment: `python -c "import vllm.envs; print('\n'.join(v for v in dir(vllm.envs) if v.startswith('VLLM_')))"`
- To check the current *resolved* value: `python -c "import vllm.envs as e; print(e.VLLM_CACHE_ROOT)"`
- vLLM's env var introspection module: `vllm/envs.py` (~260 lines as of v0.19; direct grep is fastest)
