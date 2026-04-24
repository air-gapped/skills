# OpenTelemetry tracing for vLLM

Last verified: 2026-04-24 (see `references/sources.md`)

Load when configuring OTLP export, choosing a tracing backend, or diagnosing why traces don't show spans expected.

## Enabling tracing

```bash
vllm serve "$MODEL" \
  --otlp-traces-endpoint=grpc://otel-collector:4317 \
  --collect-detailed-traces=all     # or: model, worker, or comma-combined subset
```

Plus standard OTel environment:

| Env | Default | Purpose |
|---|---|---|
| `OTEL_SERVICE_NAME` | unset | Service identifier in the tracing backend. Recommended: `vllm-<model>-<replica>` |
| `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | `grpc` | `grpc` or `http/protobuf` |
| `OTEL_EXPORTER_OTLP_TRACES_INSECURE` | `false` | Set `true` only in dev — skips TLS verification |
| `OTEL_EXPORTER_OTLP_TRACES_HEADERS` | unset | E.g. `Authorization=Bearer ...` for authenticated collectors |

All OTel Python packages (`opentelemetry-sdk`, `opentelemetry-api`, `opentelemetry-exporter-otlp`, `opentelemetry-semantic-conventions-ai`) ship with vLLM. No extra `pip install` needed.

## What `--collect-detailed-traces` unlocks

The flag takes `model`, `worker`, `all`, or a comma-combined subset.

Without it, spans are emitted at request granularity but **without** the two metrics that matter most for slow-request diagnosis:

- `vllm:model_forward_time_milliseconds` — forward pass time
- `vllm:model_execute_time_milliseconds` — model execute incl. sampling

Docs explicitly warn: these "involve use of possibly costly and or blocking operations and hence might have a performance impact." Enable per incident, **not** as baseline — budget 5–10% throughput loss.

- `model` — model forward pass, logits, per-layer execution
- `worker` — worker GPU kernel launches, compilation, per-step scheduling
- `all` — both

## Span structure

Per-request trace typically includes:

1. **FastAPI span** (requires `opentelemetry-instrumentation-fastapi`) — HTTP entry, route, status code
2. **vLLM request span** — `vllm.request.serve` (or similar) — request lifetime from enqueue to response
3. **Queue span** — `vllm.request.queue` — WAITING state
4. **Prefill span** — `vllm.request.prefill` — scheduled → first token
5. **Decode span** — `vllm.request.decode` — first token → last token
6. **Per-step worker spans** (`--collect-detailed-traces=worker`) — per TP rank, per iteration
7. **Per-step model spans** (`--collect-detailed-traces=model`) — forward pass detail

Auto-attached attributes (vLLM + OTel semantic conventions):

| Attribute | Value |
|---|---|
| `code.function`, `code.namespace`, `code.filepath`, `code.lineno` | Emission site |
| `vllm.process_id`, `vllm.process_kind` | `worker` / `gpu` |
| `vllm.process_name` | Engine/worker identifier |
| `vllm.request_id` | Per-request correlation |
| `vllm.is_prefill` | Phase flag |

Request-span attributes typically include token counts, `finished_reason`, and `model_name` — join to metrics via those.

## FastAPI auto-instrumentation

HTTP-layer spans are **not** automatic. Run under the auto-instrumenter:

```bash
opentelemetry-instrument --traces_exporter otlp \
  vllm serve "$MODEL" --otlp-traces-endpoint=grpc://otel-collector:4317 \
  --collect-detailed-traces=all
```

Or install `opentelemetry-instrumentation-fastapi` and enable in a custom entrypoint. Without this, traces start at the vLLM request span — useful for engine diagnosis, less useful for "is this a client-side timeout."

## Stack choices

### Jaeger all-in-one (dev)

```yaml
# docker-compose.yaml
jaeger:
  image: jaegertracing/all-in-one:1.60
  environment:
    COLLECTOR_OTLP_ENABLED: "true"
  ports:
    - "16686:16686"   # UI
    - "4317:4317"     # OTLP gRPC
    - "4318:4318"     # OTLP HTTP
```

Point vLLM at `grpc://jaeger:4317`. UI at `http://localhost:16686`. What the repo's `examples/observability/opentelemetry/` POC uses.

### OTel Collector → Tempo → Grafana (production)

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-ttft
        type: latency
        latency: { threshold_ms: 3000 }
      - name: probabilistic-baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 1.0 }

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling]
      exporters: [otlp/tempo]
```

Tail sampling policy above:
- Keep 100% of traces with errors
- Keep 100% of traces with TTFT > 3s
- 1% baseline sampling of healthy traces

At H200 scale without sampling, traces run into gigabytes/hour. The combination of tail sampling (for debugging tails) + low baseline (for fleet-wide patterns) is the operator default.

Grafana: configure Tempo datasource, enable exemplars on Prometheus latency panels to link `histogram_quantile` spikes to actual traces.

### Langfuse

Product-side LLM observability. Consumes OTLP directly. Captures token counts and latency spans but **not prompts/completions** — SDK-level instrumentation needed for those.

Best for: LLM-product teams who want eval/cost analytics, not for SRE latency triage.

### Commercial APM

Datadog, Dynatrace, Instana — all consume OTLP out of the box. No vLLM-specific configuration. Point `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` at the agent and enable traces.

## Multi-node with Ray

Ray injects its own trace context automatically. vLLM picks it up — a FastAPI span on the frontend node bridges into vLLM spans on any Ray worker node.

Caveats:
- Each Ray actor emits spans with its own `vllm.process_id` — useful for TP rank identification
- Ray's own instrumentation (if enabled) can double-span — prefer enabling one side (either Ray's or vLLM's OTel export, not both)

## Gotchas

### Sampling at scale

Without sampling, 100 req/s with 1KB spans = 8.6 GB/day per pod. Tail sampling + 1% baseline is the default.

### Trace retention vs metric retention

Metrics are cheap (TSDB), traces are expensive (object storage). Typical retention: 7–14 days for traces, 30–90 days for metrics. Plan queries accordingly — "what happened last month at 3am" is a metrics question, not a traces question.

### FastAPI spans missing

Without `opentelemetry-instrument` wrapper or explicit instrumentation init, HTTP-layer spans are absent. First sign: traces start at a `vllm.*` span with no parent.

### Collector down = traces dropped silently

OTel SDK buffers with BatchSpanProcessor but eventually drops on overflow. No emission metric exported by default. Add a sidecar to verify the collector is reachable, or enable collector's self-telemetry.

### Ray double-instrumentation

Enabling `opentelemetry-instrument` on Ray workers and having Ray's native instrumentation both export can produce duplicate spans for the same operation, doubling both span volume and analysis complexity. Pick one.

### Trace exporter TLS issues

Common in air-gapped: internal collector uses self-signed TLS. `OTEL_EXPORTER_OTLP_TRACES_INSECURE=true` disables verification but is inappropriate in prod. Mount the internal CA bundle instead:

```bash
export OTEL_EXPORTER_OTLP_CERTIFICATE=/etc/pki/ca-trust/source/anchors/internal-ca.pem
```

### Span attribute cardinality

Don't put prompt text or `request_id` in `OTEL_RESOURCE_ATTRIBUTES` — those become resource labels and cross with every span, blowing storage.

### Useful Jaeger/Tempo queries

Find slow TTFT requests:
```
{service.name="vllm-llama-70b"} | duration > 3s
```

Correlate with a request ID:
```
{service.name="vllm-llama-70b"} | vllm.request_id="req_abc123"
```

Find preemptions:
```
{service.name="vllm-llama-70b"} | vllm.preempted="true"
```

## Code anchors

- Tracing init / wiring: `vllm/tracing/__init__.py:66-87`
- OTLP exporter + protocol selection: `vllm/tracing/otel.py:60-124`
- ObservabilityConfig (CLI + env binding): `vllm/config/observability.py:17-153`
- Detailed-traces flag parsing: `vllm/engine/arg_utils.py:560-563`

## References

- OTel Python SDK docs: https://opentelemetry.io/docs/languages/python/
- Tempo: https://grafana.com/docs/tempo/latest/
- OTLP protocol spec: https://github.com/open-telemetry/opentelemetry-proto
- Jaeger: https://www.jaegertracing.io/
- Langfuse + vLLM: https://langfuse.com/integrations/model-providers/vllm
- vLLM OTel POC: https://github.com/vllm-project/vllm/tree/main/examples/observability/opentelemetry
- Medium — Supercharging vLLM with OTel distributed tracing: https://medium.com/@ronen.schaffer/follow-the-trail-supercharging-vllm-with-opentelemetry-distributed-tracing-aa655229b46f
