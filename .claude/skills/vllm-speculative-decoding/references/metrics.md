# Metrics & PromQL for spec-dec

Load when wiring spec-dec into Grafana, writing acceptance-rate alerts, or
diagnosing why measured throughput gain doesn't match expected AL.

## Metric surface

Source of truth: `vllm/v1/spec_decode/metrics.py:154-198` (V1 engine). Four
counters, one of them labeled.

| Metric (base) | Type | Labels | Exported as |
|---|---|---|---|
| `vllm:spec_decode_num_drafts` | Counter | (engine_idx) | `..._total` |
| `vllm:spec_decode_num_draft_tokens` | Counter | (engine_idx) | `..._total` |
| `vllm:spec_decode_num_accepted_tokens` | Counter | (engine_idx) | `..._total` |
| `vllm:spec_decode_num_accepted_tokens_per_pos` | Counter | (engine_idx, position) | `..._total` |

`position` is 0 to `num_speculative_tokens - 1`. Counter names get `_total`
suffix on export (prometheus_client convention) — so PromQL must reference
`vllm:spec_decode_num_drafts_total`, not `vllm:spec_decode_num_drafts`.

In-memory aggregator (`SpecDecodingStats` at lines 17-46) is what feeds the
engine log-line every `log-stats-interval`:

```
SpecDecoding metrics: Mean acceptance length: 2.73, Accepted: 12.4 tok/s,
Drafted: 15.1 tok/s, Per-position acceptance rate: [0.89, 0.76, 0.61]
```

## PromQL recipes

The source comments in `metrics.py:122-139` are the canonical forms.

**Overall acceptance rate (0–1):**
```promql
sum(rate(vllm:spec_decode_num_accepted_tokens_total[5m])) by (model_name)
/
sum(rate(vllm:spec_decode_num_draft_tokens_total[5m])) by (model_name)
```

**Mean acceptance length (tokens per target step, including the bonus):**
```promql
1 + (
  sum(rate(vllm:spec_decode_num_accepted_tokens_total[5m])) by (model_name)
  /
  sum(rate(vllm:spec_decode_num_drafts_total[5m])) by (model_name)
)
```
Expected values (rough):
- EAGLE-3: 3.0–4.0
- MTP (DeepSeek V3): 1.6–1.85 (n_predict=1)
- DFlash (Qwen3 BS=1): 3.5–4.5
- Suffix on agentic traffic: 2.5–5.0
- ngram on repetitive code: 1.5–2.5
- ngram on chat: 1.1–1.3

**Per-position acceptance — watch the tail falloff:**
```promql
sum by (position) (rate(vllm:spec_decode_num_accepted_tokens_per_pos_total[5m]))
/
sum(rate(vllm:spec_decode_num_drafts_total[5m]))
```

Healthy shape: smooth decay (0.85 → 0.70 → 0.55 → ...). If position-0 is
already <0.5, the drafter is fundamentally mis-aligned with the target
(tokenizer or temperature drift). If position-0 is fine but position-k falls
off a cliff at k=2, `num_speculative_tokens` is too high — drop it.

**Drafted throughput (how much work the drafter is doing):**
```promql
sum(rate(vllm:spec_decode_num_draft_tokens_total[5m])) by (model_name)
```

**Accepted throughput (how much useful work got out):**
```promql
sum(rate(vllm:spec_decode_num_accepted_tokens_total[5m])) by (model_name)
```

## Alerting templates

**Low acceptance — drafter divergence or tokenizer mismatch:**
```yaml
- alert: SpecDecAcceptanceCollapsed
  expr: |
    (
      sum(rate(vllm:spec_decode_num_accepted_tokens_total[15m])) by (model_name)
      /
      sum(rate(vllm:spec_decode_num_draft_tokens_total[15m])) by (model_name)
    ) < 0.50
  for: 10m
  labels: { severity: warning }
  annotations:
    summary: "vLLM {{ $labels.model_name }} spec-dec acceptance <50%"
    description: |
      Acceptance below 50% means spec-dec is burning draft compute with little
      throughput return. Causes: drafter tokenizer mismatch, temperature drift,
      domain shift, or drafter checkpoint corruption.
```

**Drafter idle — method configured but not being invoked:**
```yaml
- alert: SpecDecNotInvoked
  expr: |
    absent(rate(vllm:spec_decode_num_drafts_total[10m]))
    and on() vllm_spec_decode_config_enabled == 1
  for: 5m
```
(Requires a synthetic `vllm_spec_decode_config_enabled` metric — vLLM doesn't
emit one natively. Alternative: scrape the engine start log for the
`SpeculativeConfig` line.)

**Per-position tail collapse — num_speculative_tokens set too high:**
```yaml
- alert: SpecDecPositionTailCollapsed
  expr: |
    (
      sum(rate(vllm:spec_decode_num_accepted_tokens_per_pos_total{position="2"}[15m]))
      /
      sum(rate(vllm:spec_decode_num_drafts_total[15m]))
    ) < 0.40
  for: 30m
  annotations:
    summary: "Position-2 acceptance <40% for {{ $labels.model_name }}"
    description: |
      Reducing num_speculative_tokens will likely improve net throughput.
```

## Grafana dashboard additions

Current `examples/observability/prometheus_grafana/grafana.json` does NOT
include spec-dec panels. Add (on vLLM metrics only, not DCGM):

1. **Acceptance rate over time** — single-stat + timeseries, 5m window.
2. **Mean acceptance length over time** — timeseries.
3. **Per-position acceptance bar/heatmap** — use the `position` label as the
   Y-axis; healthy shape is smooth monotonic decay.
4. **Drafted vs accepted tokens/s** — two-line timeseries; gap between them
   visualises waste.

Pair with the `vllm-observability` skill's TTFT/ITL/queue panels — spec-dec
changes affect decode throughput, not prefill.

## Cross-metric diagnostics

Spec-dec interacts with other vLLM state. Use these joined reads:

- **Acceptance falling while KV utilisation climbs** → drafter is getting the
  wrong cache slots (rare, bug-class). Check recent upgrades for known issues.
- **Acceptance stable but throughput didn't improve** → draft compute is not
  overlapping with target. Check that async scheduling is on (default
  v0.14.0+) and `enforce_eager` is False. Smoke test with
  `scripts/check-spec-decode.sh`.
- **AL high but queue growing** → verification is fine, but the BS-growing
  regime makes target compute-bound. Consider `disable_by_batch_size` or
  routing high-concurrency traffic away from spec-dec replicas.
- **`num_preemptions` up + acceptance down** → KV pressure is causing
  drafter stalls; see `vllm-caching` for tiered-KV mitigation before touching
  spec-dec config.

## Verifying metric emission

`${CLAUDE_SKILL_DIR}/scripts/check-spec-decode.sh <base-url>` smoke-tests the
endpoint for the four canonical series + prints current AL.

Manual verification:
```bash
curl -s http://localhost:8000/metrics | grep -E '^vllm:spec_decode_' | head -30
```

If no spec-dec lines appear, either `--speculative-config` wasn't passed, or
the engine fell back to non-spec-dec after a validation error. Check engine
start logs for `SpeculativeConfig` disambiguation.
