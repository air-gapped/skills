# Output Artifacts & Programmatic Analysis

After every benchmark, AIPerf writes an artifact directory. Path: `--artifact-dir` (default `artifacts/`). Layout:

```
artifacts/
├── inputs.json                                    # All input dataset sessions in wire format
├── profile_export_aiperf.csv                      # Aggregated stats (one metric per row)
├── profile_export_aiperf.json                     # Aggregated stats + user config
├── profile_export.jsonl                           # Per-request records (one line per request)
├── profile_export_raw.jsonl                       # Raw payloads (--export-level raw only)
├── profile_export_aiperf_timeslices.csv           # --slice-duration enabled
├── profile_export_aiperf_timeslices.json
├── profile_export_aiperf_gpu_telemetry.jsonl      # GPU metrics over time
├── profile_export_aiperf_server_metrics.{csv,json,jsonl,parquet}  # Prometheus scrape
├── logs/aiperf.log
└── aggregate/                                     # --num-profile-runs > 1
    ├── profile_export_aiperf_aggregate.csv
    └── profile_export_aiperf_aggregate.json
```

`--profile-export-prefix` overrides the file-name stem (`profile_export_aiperf` → user-chosen).

## Export levels

| `--export-level` | What's written |
|---|---|
| `summary` | `.csv` + `.json` (aggregated stats only) |
| `records` (default) | + `.jsonl` (per-request metrics, no payloads) |
| `raw` | + `_raw.jsonl` (full request/response payloads) |

`raw` can be enormous on long runs — only enable when debugging individual requests.

## `inputs.json` schema

```json
{
  "data": [
    {
      "session_id": "a5cdb1fe-19a3-4ed0-9e54-ed5ed6dc5578",
      "payloads": [{ /* formatted request body for the configured endpoint */ }]
    }
  ]
}
```

`session_id` correlates with `conversation_id` in `profile_export.jsonl`.

## `profile_export.jsonl` per-request record

Successful request:

```json
{
  "metadata": {
    "session_num": 45,
    "x_request_id": "7609a2e7-...",
    "x_correlation_id": "32ee4f33-...",
    "conversation_id": "77aa5b0e-...",
    "turn_index": 0,
    "request_start_ns": 1759813207532900363,
    "request_ack_ns": 1759813207650730976,
    "request_end_ns": 1759813207838764604,
    "worker_id": "worker_359d423a",
    "record_processor_id": "record_processor_1fa47cd7",
    "benchmark_phase": "profiling",
    "was_cancelled": false,
    "cancellation_time_ns": null
  },
  "metrics": {
    "input_sequence_length": {"value": 550, "unit": "tokens"},
    "time_to_first_token": {"value": 255.886, "unit": "ms"},
    "request_latency": {"value": 297.525, "unit": "ms"},
    "output_token_count": {"value": 9, "unit": "tokens"},
    "inter_chunk_latency": {"value": [4.898, 5.316, 4.801, ...], "unit": "ms"},
    "output_sequence_length": {"value": 9, "unit": "tokens"},
    "inter_token_latency": {"value": 5.205, "unit": "ms"},
    "output_token_throughput_per_user": {"value": 192.13, "unit": "tokens/sec/user"}
  },
  "error": null
}
```

Failed / cancelled request:

```json
{
  "metadata": { ..., "was_cancelled": true, "cancellation_time_ns": 1759879161119772754 },
  "metrics": { "error_isl": {"value": 550, "unit": "tokens"} },
  "error": {
    "code": 499,
    "type": "RequestCancellationError",
    "message": "Request was cancelled after 0.000 seconds"
  }
}
```

Metadata fields:

- `session_num` — sequential index across all benchmark requests (single-turn) or sessions (multi-turn).
- `x_request_id` — unique per request, sent as `X-Request-ID` header.
- `x_correlation_id` — unique per session, same across all turns in a multi-turn conversation. Sent as `X-Correlation-ID`.
- `conversation_id` — input dataset session ID.
- `request_start_ns`, `request_ack_ns` (streaming only), `request_end_ns` — nanosecond epoch stamps.
- `benchmark_phase` — `warmup` or `profiling`.

Errors:

- `code` — HTTP status or custom code.
- `type` — Python exception class (`RequestCancellationError`, `TimeoutError`, …).
- `message` — human-readable.

## Pydantic models for parsing

```python
from aiperf.common.models import (
    MetricRecordInfo,
    MetricRecordMetadata,
    MetricValue,
    ErrorDetails,
    InputsFile,
    SessionPayloads,
)
```

Source: `src/aiperf/common/models/{record_models,error_models,dataset_models}.py` in the local checkout.

### Sync loader

```python
from pathlib import Path
from aiperf.common.models import MetricRecordInfo

def load_records(path: Path) -> list[MetricRecordInfo]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(MetricRecordInfo.model_validate_json(line))
    return records
```

### Async loader (large runs)

```python
import aiofiles
from aiperf.common.models import MetricRecordInfo

async def stream_records(path):
    async with aiofiles.open(path, encoding="utf-8") as f:
        async for line in f:
            if line.strip():
                yield MetricRecordInfo.model_validate_json(line)
```

### Custom percentile from raw JSONL

```python
import json
import numpy as np

ttft = []
with open("artifacts/profile_export.jsonl") as f:
    for line in f:
        rec = json.loads(line)
        if rec["error"]:
            continue
        ttft.append(rec["metrics"]["time_to_first_token"]["value"])
print(f"P75 TTFT: {np.percentile(ttft, 75):.2f} ms")
```

### Correlate inputs to results

```python
from aiperf.common.models import InputsFile, MetricRecordInfo

with open("artifacts/inputs.json") as f:
    inputs = InputsFile.model_validate_json(f.read())
sessions = {s.session_id: s for s in inputs.data}

with open("artifacts/profile_export.jsonl") as f:
    for line in f:
        rec = MetricRecordInfo.model_validate_json(line)
        session = sessions[rec.metadata.conversation_id]
        payload = session.payloads[rec.metadata.turn_index]
        # rec.metrics + payload now joined
```
