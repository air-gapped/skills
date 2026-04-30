# Air-gapped sgl-model-gateway — local mirror recipes

This file covers the gateway-specific air-gapped story. For vLLM/SGLang-side env vars and HF mirror config, see the `vllm-configuration` skill (it owns the full env-var catalog).

## TL;DR

The Rust gateway **does not honour `HF_ENDPOINT`** the way Python `transformers` does. Always pass a **local directory path** to `--model-path` or `--tokenizer-path`. Set `HF_HOME` and `HF_HUB_CACHE` env vars in the gateway pod so any side-files the gateway caches go to a writable location — never to a read-only PVC mount.

## When the gateway needs a tokenizer

The gateway needs to load a tokenizer in three situations:

1. **gRPC mode (always)** — the gateway tokenizes locally before sending token IDs to the worker. No way around it.
2. **HTTP mode + cache-aware policy** — the policy hashes prompt text via the radix tree; for the prefix-hash-on-tokens variant the tokenizer is required.
3. **`/v1/tokenize`, `/v1/detokenize` endpoints** — gateway-side tokenization for clients.

In HTTP-pass-through mode without cache-aware (e.g. `--policy random`, `--policy round_robin`), the tokenizer is optional and the gateway is a near-transparent proxy.

## What the snapshot directory needs

When you point `--model-path /local/dir/`, the gateway reads HF-style files from that directory. Required and optional files:

| File | Required? | Used for |
|---|---|---|
| `tokenizer.json` | **Yes** (when tokenizer is needed) | Tokenization. Primary file. |
| `tokenizer_config.json` | Recommended | Special tokens, chat template (if embedded), tokenizer-class taxonomy. |
| `chat_template.jinja` | Yes for OpenAI chat-completions | Chat-completions endpoint. May also live inside `tokenizer_config.json["chat_template"]`. |
| `config.json` | Yes for some operations | Model architecture metadata. |
| `special_tokens_map.json` | Sometimes | Some tokenizer classes. |
| `tokenizer.model` (SentencePiece) | Per model | Models like Llama-1/2 used SP; Llama-3+ use BPE in `tokenizer.json`. |
| `*.safetensors` (weights) | **No, gateway never loads weights** | Workers load weights — keep weight files on the *worker* PVC, not the gateway. |

The companion `transformers-config-tokenizers-expert` skill has the full catalog of what each combination of files implies for runtime behaviour. Read that if your tokenizer load fails with a non-obvious error.

## Standard HF cache layout

If you snapshot via `huggingface-cli download` or `hf snapshot`, the on-disk layout looks like:

```
/models/huggingface/
├── hub/
│   └── models--meta-llama--Llama-3.1-8B-Instruct/
│       ├── blobs/
│       │   ├── <sha256>...
│       │   └── ...
│       ├── refs/
│       │   └── main           # contains the snapshot SHA
│       └── snapshots/
│           └── <commit-sha>/
│               ├── tokenizer.json -> ../../blobs/<sha>
│               ├── tokenizer_config.json -> ../../blobs/<sha>
│               ├── config.json -> ../../blobs/<sha>
│               └── ...
└── token                       # HF auth token (not needed offline)
```

Pass either:

- **The snapshot directory** (recommended): `--model-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/`
- **The repo root**: `--model-path meta-llama/Llama-3.1-8B-Instruct` with `HF_HOME=/models/huggingface` and `HF_HUB_CACHE=/models/huggingface/hub` set. This works **only if the gateway's HF resolver finds the cache** — and the Rust resolver may behave differently from Python `huggingface_hub`. **Prefer the snapshot directory; fewer moving parts.**

## Why `HF_ENDPOINT` doesn't help the gateway

The `vllm-configuration` skill documents `HF_ENDPOINT=https://internal-mirror.example.com` as the way to point Python `huggingface_hub` at an internal mirror. The Python library reads this env var and rewrites `https://huggingface.co/` URLs accordingly.

The Rust gateway uses the `hf-hub` crate, which **does not honour `HF_ENDPOINT`** as of the v0.3.x gateway releases. Searching the gateway source for `HF_ENDPOINT` returns no hits. Result: an air-gapped cluster that has only an HF mirror but uses `--model-path meta-llama/Llama-3.1-8B-Instruct` will fail when the gateway tries to reach `huggingface.co`.

**The fix is structural, not a flag:** mount the snapshot on a PVC and pass the local path. The gateway never touches the network.

## Gateway pod env vars — air-gapped recipe

```yaml
env:
  # Point HF caches at the read-mostly model store
  - {name: HF_HOME,       value: /models/huggingface}
  - {name: HF_HUB_CACHE,  value: /models/huggingface/hub}

  # Belt-and-suspenders: tell any underlying HF library not to phone home
  - {name: HF_HUB_OFFLINE,        value: "1"}
  - {name: TRANSFORMERS_OFFLINE,  value: "1"}

  # Disable telemetry
  - {name: HF_HUB_DISABLE_TELEMETRY, value: "1"}
  - {name: DO_NOT_TRACK,             value: "1"}

  # If your model store is read-only (recommended), give the process a writable
  # cache for any runtime-generated side files:
  # NB: don't reuse HF_HOME for this — keep them separate.
  - {name: TMPDIR, value: /tmp}
```

## Worker pod env vars — air-gapped recipe (for completeness)

These are vLLM/SGLang side and overlap with the `vllm-configuration` skill, but listed here because most setups need both:

```yaml
env:
  - {name: HF_HUB_OFFLINE,         value: "1"}
  - {name: TRANSFORMERS_OFFLINE,   value: "1"}
  - {name: HF_HOME,                value: /models/huggingface}
  - {name: HF_HUB_CACHE,           value: /models/huggingface/hub}
  - {name: VLLM_NO_USAGE_STATS,    value: "1"}
  - {name: VLLM_DO_NOT_TRACK,      value: "1"}
  - {name: HF_HUB_DISABLE_TELEMETRY, value: "1"}
  # Gated models: pass HF_TOKEN even offline — the cache layer revalidates.
  - name: HF_TOKEN
    valueFrom: {secretKeyRef: {name: hf-token, key: token, optional: true}}
```

The gated-model trap: even with `HF_HUB_OFFLINE=1`, if the cached snapshot was downloaded with a token, some HF cache code paths revalidate against the token on first read. Mount the secret optionally so the env var is set when needed and absent otherwise.

## ModelScope as fallback — when applicable

If your environment has a ModelScope mirror but no HF mirror at all (common in some China-region deployments), set on the **worker** side:

```yaml
- {name: VLLM_USE_MODELSCOPE, value: "true"}   # case-sensitive: "true", not "1"
```

The gateway side is unchanged — pass a local snapshot directory.

`VLLM_USE_MODELSCOPE` is read from `vllm/envs.py:588-590` as `os.environ.get("VLLM_USE_MODELSCOPE", "False").lower() == "true"`. ModelScope rewrites repo IDs via `convert_model_repo_to_path` (`vllm/transformers_utils/utils.py:117-123`).

## Verifying the gateway never tries the network

Smoke test on a fresh pod:

```bash
# In an air-gapped cluster, run the gateway with NO_PROXY catching everything:
NO_PROXY="*" \
HTTP_PROXY="http://nonexistent:1" \
HTTPS_PROXY="http://nonexistent:1" \
sgl-model-gateway \
  --worker-urls http://vllm:8000 \
  --tokenizer-path /models/huggingface/hub/.../snapshots/<sha>/ \
  --policy cache_aware \
  --port 8080
```

If startup completes and `curl http://localhost:8080/v1/models` returns the model list, you're network-clean. If it stalls or errors with a DNS/connection error, the resolver is still trying — your `--tokenizer-path` is probably an HF repo ID, not a local path.

## Snapshot dir — pre-warming on a PVC

Provision pattern for an internal HF mirror:

```bash
# On a build host with internet access
HF_ENDPOINT=https://your-internal-mirror.example.com \
  hf snapshot download meta-llama/Llama-3.1-8B-Instruct \
    --local-dir /shared-pvc/models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
    --local-dir-use-symlinks False
```

Then mount the PVC into both gateway and worker pods at `/models/huggingface`.

For a self-hosted truly-offline build, you can also `git lfs clone` from your internal mirror into the snapshot path. The directory layout matters more than the source.

## Common air-gapped failure modes

1. **"Connection refused trying to reach huggingface.co"** — `--model-path` is an HF repo ID, not a local path. The Rust resolver doesn't honour `HF_ENDPOINT`. Fix: pass the local snapshot directory.

2. **"Tokenizer file not found"** — wrong directory level. You probably pointed at `/models/huggingface/hub/models--org--repo/` (the repo dir), not `.../snapshots/<sha>/` (the snapshot dir). Symlinks resolve only inside the snapshot dir.

3. **"Permission denied writing to /models/huggingface/cache"** — `HF_HOME` is on a read-only mount. Either make a small writable subdir, or set `HF_HOME=/tmp/hf-cache` and rely on the snapshot path for read-only state.

4. **Gated model fails with a 401-ish error even offline** — set `HF_TOKEN` from a Secret, optional mount. Some HF cache paths revalidate.

5. **"Trust remote code" warning still appears** — `trust_remote_code` runs the `modeling_*.py` from the local snapshot. Functionally identical to online; the bytes are whatever you put on the PVC. The supply-chain question is "who populated this PVC", same as online.

## When `HF_ENDPOINT` *is* useful

The vLLM/SGLang **worker** does honour `HF_ENDPOINT` for fallback lookups (chat templates, generation config, occasional revalidation). Set it on the worker side to point at your internal mirror — but pre-warm the snapshot dir anyway. Belt-and-suspenders.

`HF_ENDPOINT` gotcha: **no trailing slash**. `https://hf-mirror.example.com` works; `https://hf-mirror.example.com/` breaks the URL composition. (Documented in the `vllm-configuration` skill.)
