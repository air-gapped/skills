# OpenTelemetry tracing for vLLM

Last verified: 2026-04-24 (see `references/sources.md`)

Load when configuring OTLP export, choosing a tracing backend, or diagnosing why traces don't show spans expected.

## Enabling tracing

```bash
vllm serve "$MODEL" --otlp-traces-endpoint=grpc://otel-collector:4317
```

Plus standard OTel environment:

| Env | Default | Purpose |
|---|---|---|
| `OTEL_SERVICE_NAME` | unset | Service identifier in the tracing backend. Recommended: `vllm-<model>-<replica>` |
| `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | `grpc` | `grpc` or `http/protobuf` |
| `OTEL_EXPORTER_OTLP_TRACES_INSECURE` | — | No effect on the vLLM server: the endpoint scheme decides TLS (see § TLS to the collector) |
| `OTEL_EXPORTER_OTLP_TRACES_HEADERS` | unset | E.g. `Authorization=Bearer ...` for authenticated collectors |

All OTel Python packages (`opentelemetry-sdk`, `opentelemetry-api`, `opentelemetry-exporter-otlp`, `opentelemetry-semantic-conventions-ai`) ship with vLLM. No extra `pip install` needed.

## `--collect-detailed-traces` — leave unset

| Fact (v0.33.0) | Consequence |
|---|---|
| Only the V0 engine read the flag; V1 (v0.11.0+) has no consumer | No extra span, attribute or `/metrics` series appears. `vllm:model_forward_time_milliseconds`, `vllm:model_execute_time_milliseconds`, `gen_ai.latency.time_in_model_forward` and `…_execute` are never emitted |
| Config validation requires `--otlp-traces-endpoint` | Setting the flag alone fails startup |
| Values `model`, `worker`, `all`, space-separated | The comma form (`model,worker`) fails startup since v0.31.0 — fix manifests before upgrading |

## Span structure

vLLM emits **one span per finished request**: `llm_request`, kind SERVER, start time = request arrival. There are no queue, prefill, decode or per-step child spans — the phase timings are attributes on that one span (v0.33.0, `OutputProcessor.do_tracing`).

| Attribute | Meaning (latencies in seconds) |
|---|---|
| `gen_ai.request.id` | External request ID — the join key to logs |
| `gen_ai.latency.time_in_queue` | Queued → scheduled |
| `gen_ai.latency.time_to_first_token` | Arrival → first token |
| `gen_ai.latency.time_in_model_prefill` | Scheduled → first token |
| `gen_ai.latency.time_in_model_decode` | First token → last token |
| `gen_ai.latency.time_in_model_inference` | Scheduled → last token |
| `gen_ai.latency.e2e` | Arrival → finish |
| `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens` | Token counts |
| `gen_ai.request.max_tokens`, `…temperature`, `…top_p`, `…n` | Sampling parameters, only when set |

- The span carries no prompt or completion text, no finish reason and no model name. Identify the deployment with `OTEL_SERVICE_NAME`.
- An incoming W3C `traceparent` header is honoured: the span joins the caller's trace.
- Resource attributes: `vllm.process_id`; spans from worker processes add `vllm.process_kind` and `vllm.process_name`.
- Startup emits loading spans once per boot (`EngineCoreProc init`, `Prepare model`, …) with `code.function`, `code.namespace`, `code.filepath`, `code.lineno`. They are not per-request data.
- HTTP-layer spans exist only under FastAPI auto-instrumentation (next section).

## FastAPI auto-instrumentation

HTTP-layer spans are **not** automatic. Run under the auto-instrumenter:

```bash
opentelemetry-instrument --traces_exporter otlp \
  vllm serve "$MODEL" --otlp-traces-endpoint=grpc://otel-collector:4317
```

Or install `opentelemetry-instrumentation-fastapi` and enable in a custom entrypoint. Without this, traces start at the vLLM request span — useful for engine diagnosis, less useful for "is this a client-side timeout."

## Stack choices

### Jaeger all-in-one (dev)

```yaml
# docker-compose.yaml
jaeger:
  image: cr.jaegertracing.io/jaegertracing/jaeger:2.23.0   # v2 — OTLP receivers on by default
  ports:
    - "16686:16686"   # UI
    - "4317:4317"     # OTLP gRPC
    - "4318:4318"     # OTLP HTTP
```

Point vLLM at `grpc://jaeger:4317`. UI at `http://localhost:16686`.

Jaeger v1 reached end-of-life on 2025-12-31. The repo's `examples/observability/opentelemetry/` README still runs `jaegertracing/all-in-one:1.57` (through v0.33.0) — follow its vLLM steps, substitute the v2 image, and drop `COLLECTOR_OTLP_ENABLED`.

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
      - name: slow-request
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
- Keep 100% of traces longer than 3s — trace duration is end-to-end, not TTFT; filter on `gen_ai.latency.time_to_first_token` at query time
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

Without `opentelemetry-instrument` wrapper or explicit instrumentation init, HTTP-layer spans are absent. First sign: traces start at an `llm_request` span with no parent.

### Collector down = traces dropped silently

OTel SDK buffers with BatchSpanProcessor but eventually drops on overflow. No emission metric exported by default. Add a sidecar to verify the collector is reachable, or enable collector's self-telemetry.

### Ray double-instrumentation

Enabling `opentelemetry-instrument` on Ray workers and having Ray's native instrumentation both export can produce duplicate spans for the same operation, doubling both span volume and analysis complexity. Pick one.

### TLS to the collector

The endpoint scheme decides, not `OTEL_EXPORTER_OTLP_TRACES_INSECURE` — vLLM builds the gRPC exporter with `insecure=True` (v0.33.0):

| `--otlp-traces-endpoint` | Transport |
|---|---|
| `grpc://host:4317` (or `http://`, or bare `host:4317`) | **Plaintext, always.** A TLS-only collector rejects it |
| `https://host:4317` | gRPC over TLS |
| `https://host:4318/v1/traces` with `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf` | HTTP over TLS |

Internal or self-signed CA: mount the bundle and point the exporter at it.

```bash
export OTEL_EXPORTER_OTLP_CERTIFICATE=/etc/pki/ca-trust/source/anchors/internal-ca.pem
```

### Span attribute cardinality

Don't put prompt text or `request_id` in `OTEL_RESOURCE_ATTRIBUTES` — those become resource labels and cross with every span, blowing storage.

### Useful Tempo (TraceQL) queries

```
{ resource.service.name = "vllm-llama-70b" && span.gen_ai.latency.time_to_first_token > 3 }
{ resource.service.name = "vllm-llama-70b" && span.gen_ai.latency.time_in_queue > 1 }
{ span.gen_ai.request.id = "<request-id>" }
```

Preemption is not on the span — use `vllm:request_num_preemptions` (v0.30.0+).

## Code anchors

At tag v0.33.0 (file length in parentheses):

- Request span and its attributes: `OutputProcessor.do_tracing` in `vllm/v1/engine/output_processor.py`; names in `vllm/tracing/utils.py`
- Tracer init and exporter/protocol selection: `vllm/tracing/otel.py:60-102` (260)
- `instrument` / `instrument_manual` wrappers: `vllm/tracing/__init__.py:66-89` (155)
- ObservabilityConfig, tracing validation: `vllm/config/observability.py:19-222` (222)

## References

- OTel Python SDK docs: https://opentelemetry.io/docs/languages/python/
- Tempo: https://grafana.com/docs/tempo/latest/
- OTLP protocol spec: https://github.com/open-telemetry/opentelemetry-proto
- Jaeger: https://www.jaegertracing.io/
- Langfuse + vLLM: https://langfuse.com/integrations/model-providers/vllm
- vLLM OTel POC: https://github.com/vllm-project/vllm/tree/main/examples/observability/opentelemetry
- Medium — Supercharging vLLM with OTel distributed tracing: https://medium.com/@ronen.schaffer/follow-the-trail-supercharging-vllm-with-opentelemetry-distributed-tracing-aa655229b46f
