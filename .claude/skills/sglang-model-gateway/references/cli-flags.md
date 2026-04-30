# sgl-model-gateway CLI flag reference

Grouped by category. Defaults sourced from `sgl-model-gateway/src/main.rs` and `src/config/types.rs` on `main` (April 2026, gateway v0.3.x). For canonical answers, run:

```bash
docker run --rm lmsysorg/sgl-model-gateway:v0.3.1 --help
```

If `--help` and this document disagree, trust `--help`.

## HA / mesh sync (gateway-replica state sharing)

| Flag | Default | Notes |
|---|---|---|
| `--enable-mesh` | `false` | Enable CRDT-based gRPC sync of worker registry + policy registry (radix tree, etc.) across gateway replicas. Eliminates the multi-replica 10-20% cache-hit penalty. |
| `--mesh-peer-urls URL [URL ...]` | empty | Static peer list, e.g. `grpc://gateway-0:39527 grpc://gateway-1:39527`. |
| `--mesh-port` | `39527` | Port the gateway listens on for mesh sync. Numeric port for K8s probes if you also probe gRPC here. |
| `--router-mesh-port-annotation` | `sglang.ai/mesh-port` | Pod annotation key the gateway reads when peer-discovering through K8s. |
| `--router-selector key=value` | empty | K8s label selector for peer gateway pods (mesh discovery). |

`MeshSyncManager` lives in `src/server.rs:744-981`. Uses the `crdts = "7.3"` crate for eventual-consistency sync.

## Network / binding

| Flag | Default | Notes |
|---|---|---|
| `--host` | `0.0.0.0` | Bind address. |
| `--port` | `30000` | HTTP/gRPC port. |
| `--prometheus-host` | `127.0.0.1` | Metrics bind. Set to `0.0.0.0` for K8s. |
| `--prometheus-port` | `29000` | Metrics port. |

## Worker registration

| Flag | Default | Notes |
|---|---|---|
| `--worker-urls URL [URL ...]` | empty | Static worker list. |
| `--service-discovery` | `false` | Enable K8s pod-watch discovery. |
| `--selector key=value` | empty | Repeatable. AND semantics. |
| `--service-discovery-port` | `80` | Port to probe on each pod IP. Set this to your worker's container port. |
| `--service-discovery-namespace` | `default` | Single namespace per gateway. |

## Routing policy

| Flag | Default | Notes |
|---|---|---|
| `--policy` | `cache_aware` | One of: `random`, `round_robin`, `power_of_two`, `cache_aware`, `prefix_hash`, `manual`. Plus `consistent_hashing` and `bucket` available via the policy factory at runtime (not in CLI value_parser). See `src/policies/factory.rs:77-91`. |
| `--cache-threshold` | `0.3` | Min match rate to count as cache hit (0.0-1.0). |
| `--balance-abs-threshold` | `64` | Load-balance absolute threshold for cache_aware fall-through. |

## PD disaggregation

| Flag | Default | Notes |
|---|---|---|
| `--pd-disaggregation` | `false` | Enable PD mode. |
| `--prefill URL [bootstrap_port]` | empty | Repeatable; prefill workers. |
| `--decode URL` | empty | Repeatable; decode workers. |
| `--prefill-policy` | inherits `--policy` | Specific policy for prefill pool. |
| `--decode-policy` | inherits `--policy` | Specific policy for decode pool. |
| `--prefill-selector key=value` | empty | K8s SD for prefill. |
| `--decode-selector key=value` | empty | K8s SD for decode. |
| `--bootstrap-port-annotation` | `sglang.ai/bootstrap-port` | Pod annotation key. |
| `--router-mesh-port-annotation` | `sglang.ai/ha-port` | Pod annotation key. |

## Reliability

| Flag | Default | Notes |
|---|---|---|
| `--retry-max-retries` | `5` | Max retries per request. |
| `--retry-initial-backoff-ms` | `50` | Initial backoff. |
| `--retry-max-backoff-ms` | `30000` | Max backoff. |
| `--retry-backoff-multiplier` | `1.5` | Exponential factor. |
| `--retry-jitter-factor` | `0.2` | Jitter. |
| `--disable-retries` | `false` | Disable entirely. |
| `--cb-failure-threshold` | `10` | Open after N consecutive failures. |
| `--cb-success-threshold` | `3` | Close after N consecutive successes. |
| `--cb-timeout-duration-secs` | `60` | Half-open delay. |
| `--cb-window-duration-secs` | `120` | Failure-counting window. |
| `--disable-circuit-breaker` | `false` | Disable entirely. |
| `--health-failure-threshold` | `3` | Mark unhealthy after N. |
| `--health-success-threshold` | `2` | Mark healthy after N. |
| `--health-timeout-secs` | `5` | Per-probe timeout. |
| `--health-check-interval-secs` | `60` | Active probe interval. |
| `--health-endpoint` | `/health` | Probe path. |
| `--disable-health-check` | `false` | Disable active probing. |

## Concurrency / rate-limiting

| Flag | Default | Notes |
|---|---|---|
| `--max-concurrent-requests` | varies | Cap concurrent in-flight requests. |
| `--queue-size` | varies | Bound the request queue. |
| `--rate-limit-tokens-per-second` | unlimited | Token-bucket rate limit. |
| `--rate-limit-burst-size` | varies | Burst allowance. |

## Security

| Flag | Default | Notes |
|---|---|---|
| `--api-key STR` | empty | Required header for clients. |
| `--tls-cert-path PATH` | empty | Server certificate. |
| `--tls-key-path PATH` | empty | Server key. |
| `--client-cert-path PATH` | empty | mTLS — client cert for upstream calls. |
| `--client-key-path PATH` | empty | mTLS — client key. |
| `--ca-cert-path PATH` | empty | mTLS — trust roots for upstream. |

## Tokenization

| Flag | Default | Notes |
|---|---|---|
| `--model-path STR` | none | HF repo ID **or** local directory. Local directory recommended for air-gapped. |
| `--tokenizer-path STR` | derived from `--model-path` | Override. |
| `--tokenizer-cache-enable-l0` | `false` | In-memory tokenizer cache. |
| `--tokenizer-cache-l0-max-entries` | `10000` | L0 cap. |
| `--tokenizer-cache-enable-l1` | `false` | Larger memory cache. |
| `--tokenizer-cache-l1-max-memory` | `52428800` (50 MiB) | L1 cap in bytes. |

## Observability

| Flag | Default | Notes |
|---|---|---|
| `--log-level` | `info` | `debug`, `info`, `warn`, `error`. |
| `--enable-trace` | `false` | OTel tracing. |
| `--otlp-traces-endpoint` | empty | OTLP endpoint, e.g. `localhost:4317`. |
| `--enable-metrics` | implicit | Prometheus exporter. |

## Parsers

| Flag | Default | Notes |
|---|---|---|
| `--reasoning-parser` | none | One of: `deepseek-r1`, `qwen3`, `glm45`, etc. |
| `--tool-call-parser` | none | One of: `json`, `python`, `xml`. |

## History / storage

| Flag | Default | Notes |
|---|---|---|
| `--history-backend` | `none` | One of: `memory`, `none`, `oracle`, `postgres`, `redis`. |
| (env) `POSTGRES_DB_URL` | — | For `postgres`. |
| (env) `ATP_DSN` | — | For `oracle`. |
| (env) `REDIS_URL` | — | For `redis`. |

## MCP

| Flag | Default | Notes |
|---|---|---|
| `--mcp-config PATH` | empty | YAML config of MCP servers. |
| `--enable-mcp-tools` | `false` | Surface MCP tools to clients. |

## Multi-model gateway (IGW)

| Flag | Default | Notes |
|---|---|---|
| `--enable-igw` | `false` | Inference Gateway mode (multi-model). |

## Common multi-flag recipes

### Cache-aware HTTP gateway in front of static vLLM workers

```bash
sgl-model-gateway \
  --worker-urls http://vllm-0:8000 http://vllm-1:8000 http://vllm-2:8000 \
  --policy cache_aware \
  --cache-threshold 0.3 \
  --tokenizer-path /models/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/<sha>/ \
  --host 0.0.0.0 --port 8080 \
  --prometheus-host 0.0.0.0 --prometheus-port 29000 \
  --max-concurrent-requests 256 \
  --retry-max-retries 3 \
  --cb-failure-threshold 10 \
  --log-level info
```

### K8s service discovery for SGLang workers

```bash
sgl-model-gateway \
  --service-discovery \
  --selector model_id=gemma-3-4b \
  --service-discovery-namespace sglang \
  --service-discovery-port 30000 \
  --model-path /models/huggingface/hub/models--RedHatAI--gemma-3-4b-it-FP8-dynamic/snapshots/<sha>/ \
  --policy cache_aware \
  --host 0.0.0.0 --port 8080 \
  --prometheus-host 0.0.0.0 --prometheus-port 29000 \
  --max-concurrent-requests 128 \
  --queue-size 64 \
  --retry-max-retries 3
```

### PD disaggregation with selectors

```bash
sgl-model-gateway \
  --pd-disaggregation \
  --service-discovery \
  --prefill-selector model_id=llama-3-405b,role=prefill \
  --decode-selector model_id=llama-3-405b,role=decode \
  --service-discovery-namespace sglang \
  --service-discovery-port 30000 \
  --prefill-policy cache_aware \
  --decode-policy power_of_two \
  --tokenizer-path /models/.../snapshots/<sha>/ \
  --host 0.0.0.0 --port 8080
```

### gRPC mode with mTLS

```bash
sgl-model-gateway \
  --worker-urls grpc://worker-0:50051 grpc://worker-1:50051 \
  --policy cache_aware \
  --tokenizer-path /models/.../snapshots/<sha>/ \
  --host 0.0.0.0 --port 50050 \
  --tls-cert-path /etc/tls/server.crt \
  --tls-key-path /etc/tls/server.key \
  --client-cert-path /etc/tls/client.crt \
  --client-key-path /etc/tls/client.key \
  --ca-cert-path /etc/tls/ca.crt
```

## Python launcher equivalence

```bash
python3 -m sglang_router.launch_router --worker-urls http://worker:8000 --policy cache_aware
```

is identical to

```bash
sgl-model-gateway --worker-urls http://worker:8000 --policy cache_aware
```

The Python launcher invokes the Rust binary under the hood. The Python module name `sglang_router` was **not renamed** in the Dec 2025 refactor — only the Rust crate, directory, and Docker image were.

## Env vars

The gateway reads:

- `RUST_LOG` — overrides `--log-level` for finer control (e.g. `RUST_LOG=info,sgl_model_gateway::policies=debug`).
- `POSTGRES_DB_URL`, `ATP_DSN`, `REDIS_URL` — for the matching `--history-backend`.
- `OTEL_*` standard env vars when `--enable-trace` is set.
- `HF_HOME`, `HF_HUB_CACHE` — used by the underlying `hf-hub` Rust crate (does **not** honour `HF_ENDPOINT`).

The gateway does **not** read `HF_HUB_OFFLINE` or `TRANSFORMERS_OFFLINE` directly — set them anyway as belt-and-suspenders.
