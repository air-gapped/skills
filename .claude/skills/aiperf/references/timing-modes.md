# Timing Modes & Load Generator Reference

The single most error-prone area in `aiperf profile` is picking a scheduling mode that's incompatible with the rest of the configuration. This file is the compatibility matrix and the validation-error decoder.

## Decision

| Goal | Mode | Trigger flag |
|---|---|---|
| Saturate within a concurrency cap | **concurrency-only burst** | `--concurrency N` (no rate flag) |
| Target QPS with arrival pattern | **request-rate** | `--request-rate Q [--arrival-pattern …]` |
| Replay a trace at exact timestamps | **fixed-schedule** | `--fixed-schedule` (auto-enabled for trace dataset types) |
| Per-user gap-controlled multi-turn | **user-centric-rate** | `--user-centric-rate Q --num-users N --session-turns-mean ≥2` |

If multiple are passed, AIPerf picks in this priority: `fixed-schedule` (or trace dataset) > `user-centric-rate` > `request-rate` > `concurrency-only`.

## Compatibility matrix

✅ compatible · ⚠️ conditional · ❌ raises validation error · 🔧 required

### Scheduling

| Option | request-rate | fixed-schedule | user-centric-rate | Notes |
|---|:-:|:-:|:-:|---|
| `--request-rate` | ✅ | ❌ | ❌ | |
| `--user-centric-rate` | ❌ | ❌ | 🔧 | Requires `--num-users` |
| `--fixed-schedule` | ❌ | 🔧 | ❌ | Requires trace dataset with timestamps |
| `--num-users` | ❌ | ❌ | 🔧 | Errors otherwise |
| `--request-rate-ramp-duration` | ✅ | ❌ | ❌ | Errors with fixed-schedule / user-centric |

### Stop conditions (≥1 required)

| Option | Notes |
|---|---|
| `--request-count` | Mutex with `--num-sessions` |
| `--num-sessions` | Mutex with `--request-count` |
| `--benchmark-duration` | Enables `--benchmark-grace-period` |

### Arrival patterns

| Option | request-rate | fixed | user-centric | Notes |
|---|:-:|:-:|:-:|---|
| `--arrival-pattern` | ✅ | ❌ | ❌ | `constant`, `poisson` (default), `gamma` |
| `--arrival-smoothness` | ⚠️ | ❌ | ❌ | Only with `--arrival-pattern gamma` |

`gamma`: shape `<1` bursty, `=1` Poisson, `>1` smoother than Poisson. `concurrency_burst` is auto-set when no rate is specified.

### Concurrency

| Option | request-rate | fixed | user-centric | Notes |
|---|:-:|:-:|:-:|---|
| `--concurrency` | ✅ | ✅ | ✅ | Acts as a ceiling with rate/fixed; the driver alone |
| `--prefill-concurrency` | ⚠️ | ⚠️ | ⚠️ | Requires `--streaming`; ≤ `--concurrency` |
| `--concurrency-ramp-duration` | ✅ | ✅ | ✅ | |
| `--prefill-concurrency-ramp-duration` | ⚠️ | ⚠️ | ⚠️ | Requires `--streaming` |

If `--concurrency` is unset, session concurrency is **unbounded**. With `--user-centric-rate`, set it to at least `--num-users` so all users can have in-flight requests.

### Grace period

| Option | Notes |
|---|---|
| `--benchmark-grace-period` | Requires `--benchmark-duration`. Default 30 s; user-centric duration mode defaults to ∞. |

### Fixed-schedule offsets

| Option | Notes |
|---|---|
| `--fixed-schedule-auto-offset` | Errors without `--fixed-schedule`. Mutex with `--fixed-schedule-start-offset`. |
| `--fixed-schedule-start-offset <ms>` | Errors without `--fixed-schedule`. |
| `--fixed-schedule-end-offset <ms>` | Errors without `--fixed-schedule`. Must be ≥ start. |

### Cancellation

| Option | Notes |
|---|---|
| `--request-cancellation-rate` | All modes. Percentage 0–100. |
| `--request-cancellation-delay` | Requires `--request-cancellation-rate`. |

### Sessions

| Option | request-rate | fixed | user-centric | Notes |
|---|:-:|:-:|:-:|---|
| `--session-turns-mean` | ✅ | ✅ | ⚠️ | user-centric requires ≥ 2 |
| `--session-turns-stddev` | ✅ | ✅ | ✅ | |
| `--dataset-sampling-strategy` | ✅ | ❌ | ✅ | Not with fixed-schedule |

## Warmup

Warmup runs internally as rate-based scheduling regardless of the main mode. Each warmup-prefixed flag falls back to its non-warmup counterpart.

| Option | Notes |
|---|---|
| `--warmup-request-count` | Mutex with `--num-warmup-sessions` |
| `--warmup-duration` | |
| `--num-warmup-sessions` | Mutex with `--warmup-request-count` |
| `--warmup-concurrency` | Defaults to `--concurrency` |
| `--warmup-prefill-concurrency` | Requires `--streaming` |
| `--warmup-request-rate` | Defaults to `--request-rate` |
| `--warmup-arrival-pattern` | Defaults to `--arrival-pattern` |
| `--warmup-grace-period` | Default ∞ |
| `--warmup-concurrency-ramp-duration`, `--warmup-prefill-concurrency-ramp-duration`, `--warmup-request-rate-ramp-duration` | Per-knob warmup ramp |

## Validation errors → fixes

| Error | Fix |
|---|---|
| `--user-centric-rate cannot be used together with --request-rate or --arrival-pattern` | Use exactly one scheduling mode |
| `--user-centric-rate requires --num-users to be set` | Add `--num-users` |
| `--user-centric-rate requires multi-turn conversations (--session-turns-mean >= 2)` | Use `--request-rate` for single-turn or set `--session-turns-mean ≥2` |
| `--benchmark-grace-period can only be used with duration-based benchmarking` | Add `--benchmark-duration` |
| `--warmup-grace-period can only be used when warmup is enabled` | Add `--warmup-request-count` / `--warmup-duration` / `--num-warmup-sessions` |
| `--prefill-concurrency requires --streaming to be enabled` | Add `--streaming` |
| `--arrival-smoothness can only be used with --arrival-pattern gamma` | Switch arrival pattern or drop smoothness |
| `Dataset sampling strategy is not compatible with fixed schedule mode` | Drop `--dataset-sampling-strategy` |
| `Both a request-count and number of conversations are set` | Use one of `--request-count` or `--num-sessions` |
| `Both --warmup-request-count and --num-warmup-sessions are set` | Use one |
| `--num-users can only be used with --user-centric-rate` | Drop `--num-users` or add `--user-centric-rate` |
| `--request-cancellation-delay can only be used with --request-cancellation-rate` | Add the rate |
| `--fixed-schedule-* can only be used with --fixed-schedule` | Add `--fixed-schedule` or drop the offset |
| `--request-rate-ramp-duration cannot be used with --user-centric-rate` / `--fixed-schedule` | Drop the ramp |

## Worked examples

### Concurrency-only burst (saturation)

```bash
aiperf profile -m my-model -u http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-model \
  --concurrency 100 --request-count 1000 \
  --isl 1000 --osl 500
```

### Request-rate with concurrency ceiling

```bash
aiperf profile -m my-model -u http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-model \
  --request-rate 20 --arrival-pattern poisson \
  --concurrency 50 --benchmark-duration 120
```

### Fixed-schedule trace replay (with time window)

```bash
aiperf profile -m my-model -u http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-model \
  --input-file trace.jsonl --custom-dataset-type mooncake_trace \
  --fixed-schedule \
  --fixed-schedule-start-offset 60000 --fixed-schedule-end-offset 180000
```

### User-centric KV-cache TTL test

```bash
aiperf profile -m my-model -u http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-model \
  --user-centric-rate 1.0 --num-users 15 \
  --session-turns-mean 20 --shared-system-prompt-length 1000 \
  --benchmark-duration 600
```

`turn_gap = num_users / user_centric_rate` → 15 s between turns per user.

### Smooth ramp-up to investigate elbow

```bash
aiperf profile ... --concurrency 200 --concurrency-ramp-duration 60 \
  --benchmark-duration 300 --slice-duration 10
```
