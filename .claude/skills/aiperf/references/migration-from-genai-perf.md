# Migrating from GenAI-Perf

AIPerf is a near-drop-in replacement. Most flags transfer 1-to-1. The few exceptions are listed here, plus the metric-semantics changes that subtly shift the numbers for reasoning-capable models.

## CLI flag changes

| genai-perf | aiperf | Notes |
|---|---|---|
| `--max-threads N` | `--workers-max N` | Finer-grained worker control. AIPerf auto-sizes via `0.75 * cpu_count - 1` capped at `AIPERF_WORKER_MAX_WORKERS_CAP` (32). |
| `-- <passthrough args>` | _(removed)_ | All args are first-class now. |
| `analyze` subcommand | _(not yet)_ | Planned; not in v0.7.0. |
| `config` / `create-template` / `process-export-files` | _(not yet)_ | Planned. |
| `generate-plots` | `aiperf plot` | More plot types, `--dashboard` for interactive. |

For everything else, the same flag names work.

## Input file format

`inputs.json` schema changed:

| genai-perf | aiperf |
|---|---|
| `payload` (singular, one object) | `payloads` (array, one entry per turn) |
| no session ID | `session_id` field per entry |
| single-turn only | multi-turn supported (each `payloads[i]` is one turn) |

Migration: rename `payload` → `payloads`, wrap the existing object in an array, generate session IDs (UUIDs).

## Reasoning model metric semantics — read this carefully

Reasoning models (DeepSeek-R1, Qwen3 with thinking enabled, GPT-OSS, OpenAI O1/O3) emit `reasoning_content` before the visible answer. **GenAI-Perf ignored this field**; **AIPerf parses it**. Numbers are not directly comparable.

### TTFT

| Tool | Definition |
|---|---|
| AIPerf `time_to_first_token` | Time to the first token of any kind (reasoning OR output). |
| AIPerf `time_to_first_output_token` (TTFO) | Time to the first non-reasoning token. |
| GenAI-Perf TTFT | Equivalent to AIPerf **TTFO**, not AIPerf TTFT. |

For an apples-to-apples migration: compare **AIPerf TTFO** to historical **GenAI-Perf TTFT**. AIPerf TTFT will be lower for reasoning models because reasoning chunks arrive first.

### OSL

| Tool | Definition |
|---|---|
| AIPerf `output_sequence_length` (OSL) | Reasoning + output tokens. |
| AIPerf `output_token_count` | Output tokens only (excludes reasoning). |
| AIPerf `reasoning_token_count` | Reasoning tokens only. AIPerf-exclusive. |
| GenAI-Perf OSL | Equivalent to AIPerf **`output_token_count`**, not AIPerf OSL. |

For migration: compare **AIPerf `output_token_count`** to historical **GenAI-Perf OSL**.

### Throughput consequences

`output_token_throughput` is `total_OSL / benchmark_duration`. Because AIPerf OSL includes reasoning, throughput numbers will be *higher* than GenAI-Perf for the same workload on a reasoning model. To compare apples-to-apples, compute throughput from `total_output_tokens` (output-only) instead.

## Practical migration recipe

1. Update CLI: rename `--max-threads` → `--workers-max`. Drop the `--` passthrough.
2. If using `inputs.json`: convert `payload` → `[payload]`, add `session_id`.
3. Rerun a baseline benchmark, capturing the same metric names used in prior reports.
4. For reasoning models, **map TTFT → TTFO and OSL → output_token_count** when checking against historical numbers.
5. Audit goodput SLO definitions — if they used TTFT thresholds for reasoning models, convert to TTFO.
6. **Verify the server emits `reasoning_content` as a separate SSE field.** Both genai-perf and aiperf need this to split reasoning from output; without it, aiperf TTFO collapses to TTFT and `reasoning_token_count` stays at 0. vLLM: `--reasoning-parser deepseek_r1` (or `qwen3` / `gpt_oss` etc., see vllm-reasoning-parsers skill). SGLang: `--reasoning-parser deepseek-r1`. Verify with `curl <url>/v1/chat/completions ... --data '{"stream":true,...}' | jq '.choices[0].delta.reasoning_content'` — should print non-null tokens before the answer begins.

## What's strictly new in AIPerf vs GenAI-Perf

- Multiple arrival patterns (constant / Poisson / gamma / concurrency burst).
- Prefill concurrency for memory-safe long-context.
- Concurrency / rate / prefill ramping.
- Duration-based stop with grace period.
- User-centric per-user-rate scheduling.
- HTTP trace (k6/HAR-style timings).
- Request cancellation injection.
- Multi-run confidence reporting (`--num-profile-runs`, statistical aggregate stats).
- Convergence early stopping.
- Reasoning-token parsing (TTFO + reasoning_token_count).
- Centralized credential redaction in logs (v0.7.0).
- 2xx success including 202 (v0.7.0).
- Live dashboard UI (Rich + Textual).
- FastAPI control plane for K8s deployments.
- Plugin system: 25 categories with YAML manifests.
