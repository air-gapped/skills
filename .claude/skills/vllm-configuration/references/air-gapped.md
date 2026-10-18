# Air-gapped vLLM operation — full recipe

Load when the deployment can't reach `huggingface.co` directly. Covers the three working patterns (fully offline, internal mirror, ModelScope), the staging workflow, gated-model handling, and the failure modes specific to offline operation.

## The three patterns

### Pattern A — fully offline with pre-seeded cache

Best for: regulated environments, physically isolated networks, zero-egress clusters.

1. **Stage on a connected host:**
   ```bash
   export HF_HOME=/export/hf-cache
   hf download meta-llama/Llama-3.1-70B-Instruct
   # OR, for a model-as-directory layout:
   python -c "from huggingface_hub import snapshot_download; \
     snapshot_download('meta-llama/Llama-3.1-70B-Instruct', \
                       local_dir='/export/models/llama-70b', \
                       local_dir_use_symlinks=False)"
   ```

2. **Transfer** `/export/hf-cache` or `/export/models/llama-70b` into the enclave (rsync, physical media, MinIO replication, etc.).

3. **Run with offline flags:**
   ```bash
   export HF_HOME=/mnt/hf-cache
   export HF_HUB_OFFLINE=1
   export TRANSFORMERS_OFFLINE=1
   export VLLM_NO_USAGE_STATS=1
   export VLLM_DO_NOT_TRACK=1
   vllm serve /mnt/models/llama-70b --tensor-parallel-size 8
   ```

### Pattern B — internal HF mirror (reverse proxy)

Best for: orgs that can run an internal HF mirror (nginx proxy_pass to `huggingface.co`, or a commercial solution like Artifactory's HuggingFace repository, or Squid caching proxy).

```bash
export HF_ENDPOINT=https://hf.internal.example.com    # NO trailing slash
export HF_TOKEN=<internal-bot-token>                   # mirror may still gate
unset HF_HUB_OFFLINE
vllm serve meta-llama/Llama-3.1-70B-Instruct --tensor-parallel-size 8
```

**How it works:** `huggingface_hub` treats `HF_ENDPOINT` as the base URL for every API call and download — transparently. vLLM does not see the mirror at all; the redirection happens one layer below.

**Public alternative:** `HF_ENDPOINT=https://hf-mirror.com` is a community-run mirror with a copy of most public models. No auth, no SLA.

### Pattern C — ModelScope

Best for: China-facing deployments, where `modelscope.cn` is reachable and `huggingface.co` is not.

```bash
export VLLM_USE_MODELSCOPE=true
vllm serve qwen/Qwen2-72B-Instruct --trust-remote-code --tensor-parallel-size 8
```

**Caveats:**
- Most Meta/Mistral/Google models are **not** mirrored on ModelScope. Stick to Qwen / DeepSeek / Yi / GLM families.
- `trust_remote_code=True` is usually required — ModelScope-native models rely on custom `modeling_*.py`.
- **LoRA adapters still fetch from HuggingFace** even with this flag set. PR #13220 attempted a fix but was closed without merge (2025-06-20); no upstream fix has landed. Workaround: download adapters manually and pass `--lora-modules name=/local/path`. Verify against the installed version with `grep -r VLLM_USE_MODELSCOPE vllm/lora/`.

## Staging workflow — what files must be in the cache

For `HF_HUB_OFFLINE=1` to work without first-request failures, the local directory must contain:

**Model weights:**
- `*.safetensors` or `*.bin` (whichever `load-format` expects)
- `*.safetensors.index.json` / `pytorch_model.bin.index.json` (for sharded models)

**Config & metadata:**
- `config.json` — required
- `generation_config.json` — required for most post-training recipes
- `tokenizer.json` / `tokenizer.model` / `tokenizer_config.json` / `special_tokens_map.json` — required
- `chat_template.jinja` (newer models) or chat template inside `tokenizer_config.json`

**Custom model code (if applicable):**
- `modeling_*.py` / `configuration_*.py` — required whenever `config.json` has an `auto_map` field
- Run `jq '.auto_map' config.json` to check

**Verification:** `snapshot_download(...)` returns the dir; `hf download` prints the path. Compare against a fresh clone on the connected host to confirm nothing was missed.

## Gated models offline

Even with weights locally cached and `HF_HUB_OFFLINE=1`, gated repos (meta-llama/*, google/gemma*) require `HF_TOKEN` in the runtime environment. The hub-config validation path consults it before weight load (issue #9255).

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxx
export HF_HUB_OFFLINE=1
vllm serve /mnt/models/llama-70b ...
```

On Kubernetes, mount the token as a Secret:
```yaml
env:
  - name: HF_TOKEN
    valueFrom:
      secretKeyRef:
        name: hf-access
        key: token
```

## Disabling every phone-home

Belt-and-braces — set all four:

```bash
export VLLM_NO_USAGE_STATS=1
export VLLM_DO_NOT_TRACK=1
export DO_NOT_TRACK=1
mkdir -p "$HOME/.config/vllm" && touch "$HOME/.config/vllm/do_not_track"
```

Plus verify network egress is actually blocked (airtight networks do this at firewall; confirm with `curl -m 2 https://stats.vllm.ai` returning a connection error).

## Benchmark datasets offline

Separate from models — benchmark datasets have their own staging:

- `sharegpt` — pre-stage JSON: `wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json` on connected host, rsync in
- `sonnet` — **removed at v0.32.0** (#60129); on older images it is in-tree at `vllm/benchmarks/sonnet.txt` and never downloads
- `random` — synthetic, never downloads
- `hf` — requires `HF_HUB_OFFLINE=1` + pre-cached dataset in `$HF_HOME/datasets/`

See the sibling `vllm-benchmarking` skill's `air-gapped.md` reference for full dataset staging recipes.

## Common failure modes

### "Can't load model/config.json from HF" at startup

The cache is incomplete. Missing files are usually:
- `generation_config.json`
- `chat_template.jinja`
- Custom `modeling_*.py` referenced by `auto_map`

Diagnose on the staging host: `ls -la /export/hf-cache/hub/models--<org>--<model>/snapshots/<ref>/`

### Hang during warmup

vLLM is attempting an HF API call and waiting for a connection timeout. Diagnose:
```bash
sudo strace -p $(pgrep -f 'vllm serve') -e trace=network 2>&1 | head -20
# A connect() to 3.x or HF IPs means HF_HUB_OFFLINE is not being honoured
```

Fix:
- Verify both `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are exported
- Confirm env made it into the pod: `kubectl exec <pod> -- env | grep -E 'HF_|TRANSFORMERS_'`

### "Connection error: stats.vllm.ai" in logs

Usage stats opt-out wasn't applied. Set `VLLM_NO_USAGE_STATS=1` or the alternatives above.

### `HF_ENDPOINT` redirect not working

- Trailing slash: `https://mirror.example.com/` breaks. Remove it.
- Mirror doesn't proxy the repo correctly: test with `curl -s ${HF_ENDPOINT}/api/models/meta-llama/Llama-3.1-8B-Instruct | jq .modelId`
- Some endpoints need auth headers the mirror doesn't forward. Inspect the mirror's proxy config.

### ModelScope hub errors but weights download fine

`trust_remote_code` is required for most MS models. Add `--trust-remote-code`. If weights download but server still errors, check that tokenizer files are under the same snapshot directory — MS layout differs slightly from HF.

### Gated model fails with `403` even with `HF_TOKEN` set

- Token doesn't have repo access (user accepted license in browser but token is from a different account)
- Token expired (refresh on https://huggingface.co/settings/tokens)
- Offline mode is caching the failure — clear `$HF_HOME/hub/.locks`

## Mirror dependency floors (v0.27 – v0.32)

Stage these in the mirror before the image bump, not after. Read every range
from `requirements/common.txt` at the target tag — release-note "bumps" (#51668
→ 5.15.0, #53905 → 5.16.1) touch only the CI pins in `requirements/test/*`.

| Dependency | v0.32.0 | Earlier |
|---|---|---|
| Python | `>= 3.11, < 3.15` (#60402) — drop 3.10 wheels; a 3.10 base image cannot install it | 3.10 allowed |
| `transformers` | `>= 5.16.1, < 5.20.0` (#57387, #59762) | `>= 5.10.4, < 5.18.0` v0.31.0 (upper bound new, #59614); `>= 5.10.4` v0.29–v0.30; `>= 5.5.3` v0.27–v0.28 |
| `tokenizers` | `>= 0.23.2` (#59796) | `>= 0.21.1` v0.31.0 |
| `huggingface_hub` | `>= 1.31.0` (#56460, from v0.30.0) | `>= 1.28.0` v0.29.0 (#52797) |
| FlashInfer / NIXL | — | v0.29.0 floors 0.6.18 (#54313) / 1.3.2 (#51777) |
| Runtime image | Ubuntu 24.04 (#51058, from v0.28.0) | — |

- **The `transformers` upper bound is the trap:** a mirror holding only the
  newest release no longer satisfies the engine.
- **Only the v0.32.0 floor clears the 5.10.1 / 5.13.0 / 5.15.0 CVE fixes** the
  `transformers-config-tokenizers-expert` skill lists; earlier floors did not
  clear them all. Do not record a CI pin as the runtime floor — it reads those
  exposures as patched.
- **The build fails closed when the selected precompiled CUDA variant is
  missing** (#52545, v0.29.0), where it used to fall back silently. Expect a
  hard stop on the first air-gapped build that lacks a variant.

## Container image considerations

- **vLLM official images** include `huggingface_hub` and `transformers`, so all HF env vars work out of the box
- For `hf` CLI inside containers: `pip install -U huggingface_hub[cli]` (newer images ship this)
- **Wheel installs lack FlashInfer's precompiled kernels** (the official CUDA image ships them). Without `flashinfer-cubin`, startup JIT-builds them (minutes, needs `nvcc` + `ninja`); with neither present, FlashInfer is **disabled** and only a warning says so. On v0.32.0+, run `vllm download-kernels` on the connected build host and bake the result into the image.
- For full offline images, bake the model into the image or mount via PVC — see the sibling `vllm-caching` skill for image-inspection recipes

## References

- Canonical discussion thread: https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916
- Offline offline discussion: https://github.com/vllm-project/vllm/discussions/1405
- Gated-model offline bug: https://github.com/vllm-project/vllm/issues/9255
- Revision-check on startup: https://github.com/vllm-project/vllm/issues/23451
- ModelScope LoRA gap: https://github.com/vllm-project/vllm/pull/13220
- `huggingface_hub` environment docs: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
