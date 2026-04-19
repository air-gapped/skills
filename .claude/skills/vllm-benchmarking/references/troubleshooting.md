# Troubleshooting vLLM benchmark runs

Load when a run completed but the numbers look wrong, or when `vllm bench` fails mid-run. Covers the failure modes that produce misleading output or hide real regressions.

## Table of contents
- [Numbers look wrong](#numbers-look-wrong)
- [Run crashes or hangs](#run-crashes-or-hangs)
- [Output JSON is missing fields](#output-json-is-missing-fields)
- [Environment / setup issues](#environment--setup-issues)

## Numbers look wrong

### Token/sec is 20–40% off from prior runs

**Most likely: tokenizer mismatch.** Check `tokenizer_id` in the output JSON — if it doesn't exactly match what the server loaded, every token count is fiction.

```bash
# verify on the client side:
python3 -c "from transformers import AutoTokenizer; t=AutoTokenizer.from_pretrained('<model-id>'); print(t.__class__.__name__, t.vocab_size)"

# then check server logs for the same class + vocab size
```

If the server loaded a local path but the benchmark used the HF id (or vice versa), token counts silently diverge. Pass `--tokenizer` explicitly matching what's actually on the server.

### Results look suspiciously fast

**Cold-cache contamination with `--num-prompts` too small.** `vllm bench serve` does not auto-warm (v0.11–v0.19). A 100-prompt run on a freshly-started server reports numbers dominated by the first cold 30 s, which can look *better* than steady state if the burst fits in KV before saturation.

Fix: either set `--num-warmups 50` or bump `--num-prompts` to ≥500 and visually check the first 10 ms of saved per-request latencies (via `--save-detailed`) aren't abnormally low.

### Prefix-cache hit rate stays at 0

Two causes:

1. `--enable-prefix-caching` missing on the server side. Offload/caching config has no effect without this flag.
2. Using `--dataset-name random` — random tokens share no prefix structure, so hit rate is legitimately 0. Switch to `prefix_repetition` or `custom` with real-traffic JSONL.

Verify on the server's `/metrics` endpoint:

```bash
curl -s http://<server>/metrics | grep prefix_cache
# expect: prefix_cache_hits_total and prefix_cache_queries_total
```

### Goodput reports 0.0 across the board

`--goodput ttft:500 itl:50` means **milliseconds**. Common error: passing seconds (`ttft:0.5`). Check the units. Also confirm the SLO thresholds are realistic — a P50 TTFT of 1200 ms with a goodput budget of 500 ms legitimately reports 0, that's not a bug.

### P99 latency is NaN or missing

Requires enough samples to compute. With `--num-prompts 50`, P99 is unstable and may be reported as null. Need ≥200 prompts for a trustworthy P99; ≥1000 for a stable one.

### Huge ITL variance between otherwise-identical runs

Usually environmental, not a regression:

- **Noisy neighbor** — check `nvidia-smi dmon` and `kubectl top node` during the run
- **Thermal throttling** — check `nvidia-smi --query-gpu=power.draw,temperature.gpu --format=csv -l 5`
- **Network jitter** — if benching across pods, check `ifstat` on both ends
- **CUDA graph recompiles** — happens if prompt length distribution spans multiple graph-compile thresholds; use `custom` dataset with stable length distribution for clean A/B

## Run crashes or hangs

### Hang during warmup or first request (air-gapped)

The server is trying to reach HuggingFace for a tokenizer/processor class it didn't pre-cache. Confirm:

```bash
# on the server, during hang:
sudo strace -p $(pgrep -f 'vllm serve') -e trace=network 2>&1 | head -20
# if it's trying to connect to huggingface.co, HF_HUB_OFFLINE is incomplete
```

Fix: set BOTH `HF_HUB_OFFLINE=1` AND `TRANSFORMERS_OFFLINE=1`, pre-populate `$HF_HOME` with the full model directory (not just weights — include `config.json`, `tokenizer*`, `special_tokens*`).

### Connection refused / reset mid-sweep

vLLM's HTTP layer (uvicorn default) has a backlog limit; at very high `--request-rate` with `--max-concurrency` unset, the client opens more sockets than the server accepts. Symptoms: bench reports truncated results, many `errors` in `--save-detailed`.

Fix: cap with `--max-concurrency`, or increase server `--disable-frontend-multiprocessing` / `--max-parallel-loading-workers`. For ingress-mediated deployments, check nginx/envoy connection limits — often the real bottleneck masquerades as a vLLM regression.

### `vllm bench serve` dies with `OPENAI_API_KEY` not set

Only matters if the server requires auth. If the target is an unauthenticated vLLM serve instance, set a dummy value:

```bash
OPENAI_API_KEY=dummy vllm bench serve --base-url http://...
```

The client unconditionally attaches the env var as a Bearer token; setting it to anything makes the header present.

### `trust_remote_code` needed (air-gapped + custom model)

Errors like "Cannot load model with a custom module without trust_remote_code=True" when the offline cache has all files but the `modeling_*.py` custom class.

Fix: re-download with `--include "*.py"` on the staging host, rsync in. Some models auto-download code at runtime which breaks offline mode even with a full snapshot. Inspect `config.json` for `auto_map` entries referring to classes not in the cache.

## Output JSON is missing fields

### No `output_throughput` field

Running a pooling/embedding model? Those emit `EmbedBenchmarkMetrics` which only has `request_throughput` and `total_token_throughput`. See `output-schema.md`.

### No `spec_decode_*` fields

Server isn't using speculative decoding. These fields only appear when the engine emits them. Absence isn't a bug.

### Field names look wrong

Check vLLM version. Pre-v0.10 used `requests_per_second` (renamed to `request_throughput`). See `output-schema.md` for version notes.

## Environment / setup issues

### Shared memory exhausted

vLLM uses `/dev/shm` heavily for tensor parallel communication. In containers without `--ipc=host` or with small `--shm-size`, benchmarks can stall or crash with obscure NCCL errors.

```bash
# docker:
--ipc=host  # or --shm-size=10g
# kubernetes:
volumes:
- name: shm
  emptyDir: {medium: Memory, sizeLimit: 10Gi}
volumeMounts:
- {name: shm, mountPath: /dev/shm}
```

### GPU visible but not usable

Container sees the GPU but kernels fail. Usually missing nvidia-container-toolkit or wrong driver version for CUDA 13 images on a host with CUDA 12 driver.

```bash
# inside container:
nvidia-smi  # if this fails, toolkit issue
python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"
```

### Benchmark client GPU interfering with server GPU

Running `vllm bench` inside the same pod as the server on an 8-GPU node: the benchmark process may grab a GPU it doesn't need for tokenization, causing contention. Pin with `CUDA_VISIBLE_DEVICES= vllm bench serve ...` (empty = no GPUs for the client).

## What to include in a bug report

If numbers look off and none of the above explain it:

1. Output JSON file (at least the top-level fields)
2. vLLM version (`pip show vllm`)
3. `nvidia-smi` output at start and end of run
4. Dataset name + path (or schema if custom)
5. Exact `vllm bench` invocation
6. Whether air-gapped (and which pattern from `air-gapped.md`)
7. If applicable: `--save-detailed` file excerpt showing per-request anomalies
