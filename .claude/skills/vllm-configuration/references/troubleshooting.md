# vLLM configuration troubleshooting

Load when a configuration doesn't behave as intended — values aren't being applied, startup fails with obscure errors, or runtime behaviour doesn't match the config file.

## Table of contents
- [My config values aren't being applied](#my-config-values-arent-being-applied)
- [Startup failures](#startup-failures)
- [Runtime behaviour mismatches](#runtime-behaviour-mismatches)
- [Kubernetes / containerized issues](#kubernetes--containerized-issues)
- [Verifying effective config](#verifying-effective-config)

## My config values aren't being applied

### CLI arg silently overrides the YAML

This is usually intentional but surprising. Precedence is **CLI > YAML > defaults**. Positional args also win.

```bash
vllm serve /local/path --config prod.yaml
# /local/path is used; prod.yaml's `model:` is ignored
```

Fix: either drop the positional, or remove `model:` from the YAML to make intent explicit.

### Env var set but YAML also sets the same key

The YAML wins over env vars for engine-arg-space variables (env vars here are `VLLM_*` that mirror engine args, which is rare). Library-layer env vars (`HF_HUB_OFFLINE`, `HF_ENDPOINT`) always apply regardless.

### Boolean flag not being parsed

YAML is strict: `true`/`false` only. Don't use `yes`/`no`/`on`/`off`. Missing key = default (usually false).

```yaml
# wrong
enable-prefix-caching: yes
# right
enable-prefix-caching: true
```

### Nested dict not reaching the target

`speculative-config`, `compilation-config`, `kv-transfer-config` take dict values that get JSON-serialized. On a parse error, try writing the dict explicitly:

```yaml
# easier to debug
kv-transfer-config: '{"kv_connector":"NixlConnector","kv_role":"kv_producer"}'
```

### Older vLLM versions

- Key-order bug (#8947) on v0.10–v0.11: if `served-model-name` is last in YAML, parsing fails. Move it up or upgrade.
- Pre-v0.10: boolean handling inconsistent; upgrade.

## Startup failures

### `ValueError: max_model_len (X) is greater than max_position_embeddings`

The model's `config.json` says one thing; the request is for more. Two cases:
1. **Rope scaling was applied post-training** but isn't declared in `config.json`. Fix: set `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` **if and only if** rope scaling has been verified to be baked into the checkpoint.
2. **You're just asking for more context than the model supports.** Reduce `--max-model-len`.

### `Cannot load model with a custom module without trust_remote_code=True`

The model's `config.json` has `auto_map` pointing at `modeling_*.py`. Two options:
1. Add `--trust-remote-code` (supply-chain decision — treats the model dir as executable code)
2. Use a model with a built-in vLLM architecture (check `vllm/model_executor/models/__init__.py`)

### `OSError: [Errno ...] Cannot connect to huggingface.co`

You're not fully offline. Set both:
```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```
If it still happens, `strace` to find the culprit (see `air-gapped.md`).

### OOM during model load with TP>1

- `gpu-memory-utilization` is **per-rank**, so setting 0.9 on 8 ranks uses 90% of each GPU — that's correct.
- Different footgun: `cpu-offload-gb` is total across TP, so setting too high can exhaust host RAM.
- Different footgun: `kv-offloading-size` is total across TP (opposite of SGLang which is per-rank).

### `AssertionError: <VAR> is not set` — distributed init

Usually `VLLM_HOST_IP` isn't set on a multi-node deployment and auto-detect picked a wrong interface. Set explicitly in the pod env; must be the IP on the interface that workers actually use (not the API-facing interface).

### Engine startup timeout (`VLLM_ENGINE_READY_TIMEOUT_S`)

Default is 600s. Large models (70B+) on slow storage (shared NFS, un-warmed OCI layers) can exceed this. Increase:
```bash
export VLLM_ENGINE_READY_TIMEOUT_S=1800
```
If the issue is torch.compile, persist `VLLM_CACHE_ROOT` to amortize across restarts.

## Runtime behaviour mismatches

### Prefix cache doesn't seem to hit

Verify three things:
1. `enable-prefix-caching: true` is set (it is **not** on by default pre-v0.19; is default on v1 engine)
2. Requests actually share prefixes — check with `curl -s http://localhost:8000/metrics | grep prefix_cache`
3. `block-size` is consistent across runs (default 16; changing it invalidates cache)

### Tokenizer mismatch silently returning wrong token counts

`--tokenizer` defaults to `--model`. If they differ — common when serving via a local path but benching with an HF ID — token counts diverge. Always pass both explicitly.

### Chat template behaviour unexpected

- Check `chat_template.jinja` file in the model dir
- Inspect via `curl -s http://localhost:8000/v1/chat/completions/playground` (dev-mode endpoint) or the raw `tokenizer_config.json`
- To override: `--chat-template /path/to/template.jinja`

### `--reasoning-parser` / `--tool-call-parser` not firing

Server args only, not engine args. Must be on the `vllm serve` CLI, not in engine-args YAML sections. Check `endpoint-type`-style FrontendArgs in the config file block.

### LoRA adapter loads from HF despite `VLLM_USE_MODELSCOPE=true`

Known gap — LoRA resolver historically didn't honour the flag. Workaround: download adapters manually, pass `--lora-modules name=/local/path`.

### `max-num-seqs` seems ignored

Check `max-num-batched-tokens` — it's often the actual constraint. If `max-num-batched-tokens` is too low (default auto-sizes from `max-model-len`), the scheduler won't pack as many sequences as `max-num-seqs` allows.

## Kubernetes / containerized issues

### Service name collision

Kubernetes injects `<SVC>_SERVICE_HOST` / `<SVC>_SERVICE_PORT` env vars into every pod in the namespace. A Service named `vllm` can collide with vLLM's `VLLM_` env var namespace in some versions. Rename to `vllm-api`, `inference`, etc.

Verify in the pod:
```bash
kubectl exec <pod> -- env | grep VLLM_ | sort
```
Anything surprising (like `VLLM_SERVICE_HOST` or `VLLM_PORT` pointing at a cluster IP) is probably k8s injection.

### Torch compile cache cold on every pod restart

`VLLM_CACHE_ROOT` defaults to `~/.cache/vllm`, which is ephemeral in most pod images. Mount a PVC or use a shared NFS path:

```yaml
volumeMounts:
  - name: vllm-cache
    mountPath: /root/.cache/vllm
volumes:
  - name: vllm-cache
    persistentVolumeClaim:
      claimName: vllm-compile-cache
```

Make sure the PVC has enough space — per-model-shape compile artifacts can add up to several GiB.

### `/dev/shm` too small

NCCL for TP communication uses `/dev/shm`. Default container `/dev/shm` is 64MB, which causes cryptic NCCL errors on large TP.

Docker: `--ipc=host` or `--shm-size=10g`
Kubernetes:
```yaml
volumes:
  - name: shm
    emptyDir: {medium: Memory, sizeLimit: 10Gi}
volumeMounts:
  - {name: shm, mountPath: /dev/shm}
```

### GPU visible but kernels fail

Usually nvidia-container-toolkit missing or driver/CUDA mismatch. Diagnose inside the container:
```bash
nvidia-smi  # should show GPUs
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"
```

### Secrets inlined into YAML ConfigMap

Don't do this. YAML config doesn't support env substitution; put secrets in env via Secret, not in the YAML. API keys, HF tokens, and ssl-keyfile paths should be env vars or mounted Secret paths.

## Verifying effective config

The only authoritative "what's the engine actually running with" signals:

```bash
# 1. Model ID the server loaded
curl -s http://localhost:8000/v1/models | jq '.data[].id'

# 2. Prometheus metrics — every engine knob that matters shows up here
curl -s http://localhost:8000/metrics | grep -E \
  'prefix_cache|block_size|max_model_len|gpu_cache|gpu_memory|kv_cache_dtype'

# 3. Startup log — grep the first 100 lines for "Engine config"
kubectl logs <pod> --tail=200 | grep -A 40 'EngineConfig\|EngineArgs'

# 4. Server dev endpoint (dangerous — don't enable in prod)
VLLM_SERVER_DEV_MODE=1 vllm serve ...
curl -s http://localhost:8000/v1/config  # if available in the installed version
```

For a more principled diff-against-config check, use `scripts/check-config.sh`.

## What to include in a bug report

If config behaviour is genuinely unexpected (not covered above):

1. vLLM version: `pip show vllm | grep Version`
2. Full `vllm serve` command
3. `--config FILE.yaml` contents
4. Full env vars dump (redact tokens): `env | grep -E '^(VLLM_|HF_|TRANSFORMERS_)' | sort`
5. First 200 lines of startup log
6. `curl -s http://localhost:8000/v1/models`
7. `uname -a` + GPU model
8. Whether air-gapped and which pattern (A/B/C from `air-gapped.md`)
