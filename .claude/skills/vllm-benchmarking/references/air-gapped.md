# Air-gapped vLLM benchmarking

Load when running benchmarks in an environment without access to `huggingface.co`. Covers the three working patterns and their gotchas.

## Table of contents
- [Pattern 1: HF_ENDPOINT redirect](#pattern-1-hf_endpoint-redirect)
- [Pattern 2: ModelScope substitution](#pattern-2-modelscope-substitution)
- [Pattern 3: Fully offline pre-seeded cache](#pattern-3-fully-offline-pre-seeded-cache)
- [Dataset sourcing air-gapped](#dataset-sourcing-air-gapped)
- [Gated models](#gated-models)
- [Internal HF proxy with MinIO or nginx](#internal-hf-proxy-with-minio-or-nginx)

## Pattern 1: HF_ENDPOINT redirect

**Simplest, least invasive.** Works when the enclave has HTTPS egress to *some* mirror but not to `huggingface.co` directly.

```bash
export HF_ENDPOINT=https://hf-mirror.com
# or an internal reverse-proxy:
export HF_ENDPOINT=https://hf.internal.example.com

vllm bench serve ...  # works transparently
```

All `huggingface_hub` calls reroute to the mirror. Works for model downloads, dataset loads, tokenizer fetches.

**Known mirrors:**
- `https://hf-mirror.com` — China-based non-profit, still operational in 2026, mirrors public models + datasets.
- Internal reverse-proxy — nginx in front of a locally-cached subset of the Hub. Requires a connected host to periodically refresh.

## Pattern 2: ModelScope substitution

`modelscope.cn` hosts many popular models. vLLM has a built-in bridge:

```bash
export VLLM_USE_MODELSCOPE=True
# plus in the vLLM serve args: --trust-remote-code
```

**Known gap:** LoRA adapter loading does not work through ModelScope (vLLM issue #32841). For LoRA testing, use Pattern 1 or 3.

Use this when the China-based mirror is faster than an internal mirror, or when ModelScope has a model that hf-mirror.com doesn't.

## Pattern 3: Fully offline pre-seeded cache

**No outbound network at all.** Pre-populate the HF cache on a connected host, transfer it into the enclave.

```bash
# On a connected staging host:
export HF_HOME=/staging/hf-cache
huggingface-cli download <model-id>
huggingface-cli download --repo-type dataset <dataset-id>

# rsync /staging/hf-cache into the enclave at /data/hf-cache

# In the enclave:
export HF_HOME=/data/hf-cache
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
vllm bench serve ...
```

**Both env vars are required.** `HF_HUB_OFFLINE=1` blocks `huggingface_hub` network calls; `TRANSFORMERS_OFFLINE=1` blocks the `transformers` library's own download attempts. Missing either causes intermittent hangs.

**Failure modes:**
- `config.json` references a remote processor class not in the cache — fix by pre-downloading the full model directory, not just weights.
- Code path calls `snapshot_download` without a specific revision — sometimes triggered by `trust_remote_code=True` loading custom model code. Prefer pinning a revision at launch.
- Tokenizer library attempts to download its config — usually resolved by `transformers>=4.45` with proper offline semantics.

## Dataset sourcing air-gapped

| Dataset | Air-gapped availability | Action |
|---|---|---|
| `random` | Always works | No action — synthetic |
| `sonnet` | Always works | Shipped in-tree at `vllm/benchmarks/sonnet.txt` |
| `prefix_repetition` | Always works | Synthetic |
| `random-mm`, `random-rerank` | Always works | Synthetic |
| `sharegpt` | Requires staging | `wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json` on a connected host, transfer, use `--dataset-path` |
| `burstgpt` | Requires staging | Same pattern — stage the JSON, point `--dataset-path` |
| `custom` | Always works | Local JSONL file |
| `hf` | Requires HF_ENDPOINT or cache | See patterns 1/3 |

## Gated models

Pattern 1 (hf-mirror.com) does NOT proxy auth for gated models. Workarounds:

1. Download on a connected host with a valid HF token, transfer model dir into enclave, point `--model` at the local path.
2. For enterprises: stand up an internal HF cache (Pattern "internal reverse-proxy" under Pattern 1) that the security team has authenticated once.

## Internal HF proxy with MinIO or nginx

For enterprise air-gapped setups:

- **Option A:** nginx reverse-proxy with aggressive caching, backed by a periodic rsync from a connected DMZ host. `HF_ENDPOINT` points at the nginx URL.
- **Option B:** MinIO/S3 as the underlying storage, with `hf_transfer` enabled. Requires custom HF Hub patches or the `hf-transfer` library pointing at S3-compatible endpoints.
- **Option C:** JuiceFS + S3 on a shared PVC — models live on the JuiceFS mount, `HF_HOME` points at `/mnt/juicefs/hf-cache`. K8s-native, works well with vLLM deployments that already use PVC-mounted model caches.

**For ongoing operation:** a connected DMZ host runs a nightly `huggingface-cli download` of the models the fleet uses, writes to the shared storage, air-gapped cluster consumes read-only. This is the pattern most enterprise vLLM deployments end up with.

## Quick sanity check

```bash
# Confirm HF access path is working before starting a long benchmark:
python3 -c "from huggingface_hub import HfApi; print(HfApi().whoami())"
# If this fails in offline mode, that's expected — check that the staged cache has the required artifacts instead:
ls $HF_HOME/hub/
```
