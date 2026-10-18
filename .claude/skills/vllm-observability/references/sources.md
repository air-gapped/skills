# External sources — last-verified inventory

Freshened: 2026-10-18 — every row probed at v0.32.0. Tree-wide `"vllm:…"` name diff v0.30.0 -> v0.32.0 (Python + Rust, tests excluded) is additions only: `loggers.py` 38 -> 42 names (`admission_rejections`, `num_requests_kv_fetch_by_stage`, `prompt_tokens_cached_by_source`, `watermark_requests`), plus HiSparse host-tier, NIXL after-expiry, tiering back-pressure, SimpleCPUOffloadConnector and sleep/RL operation series; `nixl_num_failed_transfers` semantics widened in v0.31.0 (#55854), comma form of `--collect-detailed-traces` removed (#55702), `--custom-histogram-buckets` added (#48867). Medium, DeepWiki and hud.pytorch.org refuse curl (403/429) but load in the browser.

Tracks every external reference the `vllm-observability` skill depends on, when it was last probed, and the verification result. Keep this file current every time the skill is freshened. `skill-improver` Dim 9 staleness cap uses the most-recent date here.

All dates UTC.

**Freshened: 2026-09-15 — every row probed.** All four PR merge-to-release attributions re-checked with `git tag --contains` rather than merge dates and all four hold (#42206, #39457, #44448 → v0.24.0; #46768 → v0.25.0). The `loggers.py` metric-name set is **identical at v0.27.0 and v0.29.0** — 37 names, no additions or removals — and `gpu_cache_usage_perc` is still absent at v0.29.0, so the rename guidance holds across two further releases.

**The name-diff alone would have missed the real change.** `vllm/v1/kv_offload/tiering/base.py` went from 2 metric names at v0.27.0 to **15 at v0.28.0** — 13 new `kv_offload_tiering_*` metrics that `loggers.py` never mentions, now documented in `metrics-catalog.md`. The trigger below that warns a `loggers.py` diff is not sufficient was right.

One evidence gap corrected: the `examples/observability/` row described `dashboards/grafana/` only. `dashboards/perses/` has been in that tree since v0.20.0 (PR #40123, merged 2026-04-17, moved from `examples/online_serving/`; corrected 2026-10-18 via `git tag --contains`) — it already existed when the previous pass wrote that row. `SKILL.md` and `dashboards.md` both document it correctly; only this file's evidence trail was incomplete.

## Probe log

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| vLLM PR #24245 "Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/24245 | 2026-10-18 | fresh | Re-confirmed `gh pr view`: state=MERGED, mergedAt=2025-09-16. Hides `gpu_*`-prefixed metrics behind `--show-hidden-metrics-for-version=X.Y` — a HIDING, not a rename. Terminal state. |
| vLLM PR #25392 "Revert [Metrics] Hide deprecated metrics with gpu_ prefix" | https://github.com/vllm-project/vllm/pull/25392 | 2026-10-18 | deprecation | Re-confirmed `gh pr view`: state=CLOSED, mergedAt=null, closedAt=2025-09-23. Revert never merged, so the hiding stuck. Terminal state. |
| vLLM V1 metrics source (loggers.py) | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/v1/metrics/loggers.py | 2026-10-18 | fresh | Re-probed at **tag v0.25.1** (1365 lines, was 1359 on main at the 2026-05-28 pass). Extracted every `name="vllm:..."` declaration and diffed against this skill's catalog: **no catalogued name removed or renamed**; `gpu_cache_usage_perc` still 0 occurrences. Emitted set: `corrupted_requests`, `e2e_request_latency_seconds`, `engine_sleep_state`, `external_prefix_cache_{hits,queries}`, `generation_tokens`, `inter_token_latency_seconds`, `iteration_tokens_total`, `kv_block_{idle_before_evict,lifetime,reuse_gap}_seconds`, `kv_cache_usage_perc`, `lora_requests_info`, `mm_cache_{hits,queries}`, `num_preemptions`, `num_requests_{running,waiting}`, `num_requests_waiting_by_reason`, `prefix_cache_{hits,queries}`, `prompt_tokens`, `prompt_tokens_by_source`, `prompt_tokens_cached`, `request_decode_time_seconds`, `request_generation_tokens`, `request_inference_time_seconds`, `request_max_num_generation_tokens`, `request_params_{max_tokens,n}`, `request_prefill_kv_computed_tokens`, `request_prefill_time_seconds`, `request_prompt_tokens`, `request_queue_time_seconds`, `request_success`, `request_time_per_output_token_seconds`, `time_to_first_token_seconds`. |
| _(superseded row — loggers.py on main)_ | https://github.com/vllm-project/vllm/blob/main/vllm/v1/metrics/loggers.py | 2026-10-18 | fresh | Re-probed `gh api contents` on main (1359 lines): all load-bearing names emitted — `vllm:kv_cache_usage_perc`, `vllm:num_requests_waiting`, `vllm:num_requests_waiting_by_reason`, `vllm:num_preemptions`, `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits`, `vllm:external_prefix_cache_{queries,hits}`, `vllm:inter_token_latency_seconds`, `vllm:request_time_per_output_token_seconds`, `vllm:request_queue_time_seconds`, `vllm:corrupted_requests`. `gpu_cache_usage_perc` NOT emitted (0 occurrences). Counters defined bare in Python (`foo`); Prom client appends `_total` on the wire — skill's wire-format names are correct. |
| vLLM `examples/observability/` dashboards tree | https://github.com/vllm-project/vllm/tree/main/examples/observability | 2026-10-18 | fresh | Re-listed at tag v0.32.0 (`git ls-tree`): `dashboards/{grafana,perses}/`, `metrics/offline.py`, `opentelemetry/`, `prometheus_grafana/{grafana.json,docker-compose.yaml,prometheus.yaml}`. No change v0.30.0 -> v0.32.0. All files cited by skill present. |
| vLLM production metrics doc (stable) | https://docs.vllm.ai/en/stable/usage/metrics/ | 2026-10-18 | fresh / **new names harvested** | HTTP 200. Re-scraped the `vllm:*` names: documents current V1 names and still does NOT document `gpu_cache_usage_perc`. **New this pass:** the page carries concrete NIXL-connector series — `vllm:nixl_bytes_transferred`, `nixl_xfer_time_seconds`, `nixl_post_time_seconds`, `nixl_num_descriptors`, `nixl_num_failed_transfers`, `nixl_num_failed_notifications`, `nixl_num_kv_expired_reqs` — which replaced the catalog's `vllm:nixl_*` wildcard. Also confirms `vllm:estimated_{flops,read_bytes,write_bytes}_per_gpu_total`. 2026-10-18: HTTP 200 and now serves the v0.32.0 surface — lists `admission_rejections`, `num_requests_kv_fetch_by_stage`, `prompt_tokens_cached_by_source`, `watermark_requests`, `nixl_num_notifications_after_expiry`, the HiSparse host-tier and `simple_kv_offload_*` names, and a Custom Histogram Buckets section; still no `gpu_cache_usage_perc`. |
| ebpfchirp "11-Second TTFT" incident article | https://ebpfchirp.substack.com/p/11-second-time-to-first-token-on | 2026-10-18 | fresh | HTTP 200 (`curl -L`). URL still resolves; cited in SKILL.md pitfall #8 and `dashboards.md` "Ebpfchirp incident reference". |
| DCGM exporter + Grafana dashboard 15117 | https://grafana.com/grafana/dashboards/15117-nvidia-dcgm-exporter/ | 2026-10-18 | fresh | HTTP 200 (`curl -L`). Carried at 2026-04-24 through two passes; finally re-probed. |
| Metrics design doc (canonical) | https://github.com/vllm-project/vllm/blob/main/docs/design/metrics.md | 2026-10-18 | fresh | Re-read at tag **v0.32.0** (718 lines): `gpu_cache_usage_perc` appears **0 times**; v0.30.0 -> v0.32.0 diff only adds `vllm:admission_rejections_total` to the metric list and fixes the `--oltp-traces-endpoint` typo to `--otlp-traces-endpoint`. |
| vLLM V1 metrics source (loggers.py) @ v0.27.0 | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/v1/metrics/loggers.py | 2026-10-18 | fresh | Re-probed at **tag v0.27.0** (1402 lines, was 1365 at v0.25.1). Extracted every `name="vllm:..."` declaration and diffed against the v0.25.1 set recorded above: **identical — 37 names, none added, none removed, none renamed**; `gpu_cache_usage_perc` still 0 occurrences. The file grew 37 lines without changing its metric surface. |
| KV-offload metric names (3 source files) | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/distributed/kv_transfer/kv_connector/v1/offloading/metrics.py | 2026-10-18 | **broken → corrected** | The catalog's "approx" offload names were **wrong**: actual deprecated names are `vllm:kv_offload_total_time` (catalog said `…_total_time_seconds`) and `vllm:kv_offload_size` (catalog said `…_size_bytes`). Read the real set from `offloading/metrics.py`, `vllm/v1/kv_offload/cpu/common.py` and `vllm/v1/kv_offload/tiering/base.py` at v0.27.0. Current surface is a direction-split `kv_offload_{load,store}_{bytes,time,size}` plus `lookup_{sync,async}_delay_seconds` and `allocation_failure`; the three legacy `total_*`/`size` names are deprecated, carry a `transfer_type` label, and are only observed when the spec is a `CPUOffloadingSpec`. |

## Probe budget

This pass: 6 of 8 probes consumed (4 `gh api`/`gh pr view` calls, 2 `WebFetch`). Remaining budget: 2 for drift triggered by follow-up audits. Kept in reserve rather than burning on links where the skill does not cite version-sensitive claims.

## Applied drift fixes

1. **PR #25392 merge status** — corrected from "partial revert (extended old name's life)" to "closed without merging" in three locations: SKILL.md pitfall #3, SKILL.md Version notes bullet, `references/metrics-catalog.md` rename-saga callout.
2. **PR #24245 semantics** — clarified "renamed" → "hid deprecated `gpu_*` names behind `--show-hidden-metrics-for-version`" in the same three locations. The new `kv_cache_usage_perc` name existed before #24245; that PR merely cleaned up by hiding the deprecated variant.
3. **`Last verified: 2026-04-24` stamps** — added to the header of all four reference files so agents loading them know the freshness bound.

No other content was substantively altered — skill prose, PromQL, and YAML examples remained in place.

## 2026-07-21 freshen — new metrics found (v0.24.0 / v0.25.0)

The 2026-05-28 trigger ("re-probe when vLLM release > v0.22") fired: latest is
now **v0.25.1** (2026-07-14). Four additions, two of which mean previously
collected data was wrong rather than merely incomplete.

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| PR #42206 — group-aware KV capacity in `cache_config_info` | https://github.com/vllm-project/vllm/pull/42206 | 2026-10-18 | new-feature / **corrects prior dashboards** | Merged 2026-06-12, v0.24.0. Fixes the Prometheus-vs-startup-log discrepancy in issue #42024. Adds labels `kv_cache_size_tokens` and `kv_cache_max_concurrency`, both per-DP-engine and group-aware. Upstream states plainly that `num_gpu_blocks * block_size` "can be wrong for hybrid models where requests occupy multiple KV cache groups" — i.e. any dashboard deriving capacity that way has been overstating it. Applied to `metrics-catalog.md` § KV cache. |
| PR #39457 — `MLAAttentionMetrics` for DeepSeek MFU | https://github.com/vllm-project/vllm/pull/39457 | 2026-10-18 | new-feature / **invalidates prior MFU on MLA** | Merged 2026-06-12, v0.24.0. The old `AttentionMetrics` assumed MHA/GQA with a `2 * num_kv_heads * head_dim` KV footprint; MLA stores one compressed `(kv_lora_rank + qk_rope_head_dim)` vector. For DeepSeek-V3 that is **576 vs 32,768 bytes per token per layer** — a ~57× bandwidth overestimate. MFU collected from a DeepSeek deployment on < v0.24.0 is unusable. Applied to `metrics-catalog.md` § MFU. |
| PR #44448 — `vllm:tool_call_parser_invocations_total` | https://github.com/vllm-project/vllm/pull/44448 | 2026-10-18 | new-feature | Merged 2026-06-10, v0.24.0. Counter recorded in `DelegatingParser`, labelled by `mode` (streaming/non-streaming), `outcome` (tool call / no tool call), and request type. Rollout-regression signal for tool calling. **Upstream-stated limit: non-harmony path only** — harmony does not route through `DelegatingParser`. New `metrics-catalog.md` § Tool-call parsing. |
| PR #46768 — per-request `metrics` field on Chat/Completions responses | https://github.com/vllm-project/vllm/pull/46768 | 2026-10-18 | new-feature | Merged 2026-07-07, v0.25.0. RFE #40076 (billing, SLAs, experimentation, debugging). Fields: `time_to_first_token_ms`, `generation_time_ms`, `queue_time_ms`, `mean_itl_ms`, `tokens_per_second`. **Double-gated** by `--enable-per-request-metrics` *and* the `include_metrics` request parameter; suppressed when single-stream attribution isn't meaningful (`n > 1`, multi-prompt). New `metrics-catalog.md` section — this is response-body data, not Prometheus. |

Also noted, not applied (KV-connector metric names remain "stabilizing" in the
catalog and none of these change a documented name): offloading-manager stats
(#35669) and labeled/CPU-usage metrics (#45957, #45737) in v0.24.0, KV tiering
metric plumbing (#45959) in v0.25.0, Mooncake operation metrics (#43392) in
v0.22.0.

## 2026-08-11 freshen — the catalog's own names were the finding

The 2026-07-21 trigger fired twice over: **v0.26.0** (2026-07-27) and **v0.27.0**
(2026-08-10). The prescribed `loggers.py` name diff ran first and came back
clean — 37 names, identical to v0.25.1. That is a real result, but it also means
the cheap mechanical check had reached the end of what it can catch, because the
metric churn in these two releases happened **outside `loggers.py`**, in the KV
offload namespace.

Going there found the pass's only `broken` classification, and it was
self-inflicted: the § KV connector / offload table had been published with names
marked "(approx)", and **two of the three were misspelled** —
`vllm:kv_offload_total_time_seconds` and `vllm:kv_offload_size_bytes` do not
exist and never did; the real names are `vllm:kv_offload_total_time` and
`vllm:kv_offload_size`. An "(approx)" hedge on a metric name is not a hedge — a
PromQL query built on it returns no data, silently. All three are now deprecated
anyway, superseded by a direction-split load/store set.

**Process lesson for the next pass:** a metric catalog can be simultaneously
"verified against the source" and wrong, if the verification only covers the file
the previous pass happened to check. Diff `loggers.py` *and* enumerate the metric
name constants under `vllm/v1/kv_offload/` and
`vllm/distributed/kv_transfer/kv_connector/v1/offloading/`.

Also cleared: the four non-GitHub rows that had been carried unprobed since
2026-04-24 through two passes. All four return HTTP 200, and the docs.vllm.ai
page turned out to carry the concrete NIXL series that replaced another wildcard
in the catalog — the deferred probe was hiding a content improvement, not just a
staleness risk.

## 2026-09-23 freshen — v0.30.0 release notes

The prior 2026-09-22 pass diffed `loggers.py` and the KV-offload namespace
mechanically but did not read the v0.30.0 release notes prose. This pass swept
those notes for observability-relevant items and verified each against tag
`v0.30.0` in the local clone.

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| PR #55624 — MFU/MBU for SWA and hybrid layers | https://github.com/vllm-project/vllm/pull/55624 | 2026-10-18 | new-feature / **invalidates prior MFU on SWA/hybrid** | Merged 2026-09-14, v0.30.0. `vllm/v1/metrics/perf.py` `AttentionMetrics` previously summed `num_tokens * context_len` unclamped for every layer; now splits `num_swa_layers` and clamps their context length to `sliding_window`. Overestimated attn FLOPs/bytes on long-context SWA/hybrid requests (Mistral, Qwen2.5, Gemma 2/3n, Llama 4, hybrid Mamba) before this PR. Applied to `metrics-catalog.md` § MFU / performance. |
| PR #56061 — HiSparse cache metrics via KV connector stats | https://github.com/vllm-project/vllm/pull/56061 | 2026-10-18 | new-feature | Merged 2026-09-12, v0.30.0. Found by the 2026-09-22 pass's `loggers.py` sweep but never applied to the catalog table until now. `vllm/distributed/kv_transfer/kv_connector/v1/hisparse/stats.py`: Counters `vllm:hisparse_cache_hits`, `vllm:hisparse_cache_misses`, `vllm:hisparse_host_to_device_bytes` (wire names get `_total`). Only emitted when `HiSparseConnector` is configured. Applied to `metrics-catalog.md` § KV connector / offload. |
| PR #48866 — consolidate Prometheus bucket defaults | https://github.com/vllm-project/vllm/pull/48866 | 2026-10-18 | skip — pure refactor | Merged 2026-09-11, v0.30.0. Moved inline bucket lists to named constants in new `vllm/v1/metrics/buckets.py`. Diffed every constant against the pre-refactor inline lists in `loggers.py` at v0.29.0: byte-identical values for all 7 families (`request_latency`, `time_to_first_token`, `inter_token_latency`, `iteration_tokens`, `request_params_n`, `request_num_preemptions`, `kv_cache_residency`). No dashboard/alert impact — not applied. |
| PR #52755 — Rust frontend Mooncake/NIXL KV-connector metrics | https://github.com/vllm-project/vllm/pull/52755 | 2026-10-18 | new-feature | Merged 2026-09-04, v0.30.0. `rust/src/metrics/src/scheduler.rs` registers `vllm:mooncake_store_operation_time_seconds` and the existing `vllm:nixl_*` names under the Rust frontend's own registry — same wire names as the Python engine. Applied to new `metrics-catalog.md` § Rust frontend. |
| PR #56990 — Rust frontend iteration token histogram | https://github.com/vllm-project/vllm/pull/56990 | 2026-10-18 | new-feature | Merged 2026-09-15, v0.30.0. `rust/src/metrics/src/request.rs` registers `vllm:iteration_tokens_total` — previously Python-engine-only. Applied to new `metrics-catalog.md` § Rust frontend. |
| PR #56058 — normalize HTTP method labels in Rust frontend metrics | https://github.com/vllm-project/vllm/pull/56058 | 2026-10-18 | security fix | Merged 2026-09-10, v0.30.0. `rust/src/server/src/middleware/metrics.rs`: `method` label on `http_requests_total`/`http_request_duration_seconds` (unprefixed, `PrometheusFastApiInstrumentator`-style names) now maps to a fixed set of HTTP verbs plus `other`; before this PR an arbitrary request method string became the label value directly (unbounded cardinality). Applied to new `metrics-catalog.md` § Rust frontend, cross-referenced from SKILL.md pitfall 6. |

Also checked, not applied: PR #49984 (`vllm:request_num_preemptions` histogram)
— already documented in `metrics-catalog.md` § Queue & scheduler state from the
2026-09-22 pass; re-confirmed correct, no change needed. PR #52358
(`CUDAGraphStat` support in Model Runner V2) and PR #55650 (backend-neutral
KV-cache/MFU log lines, GPU→device-name in log text) are both real v0.30.0
changes but log-only and out of this skill's H100/H200 GPU-fleet scope — not
applied; named here so a future pass does not re-research them from scratch.

## 2026-10-18 freshen — v0.31.0 / v0.32.0

Name sets extracted with `git grep -hoE '"vllm:[a-z0-9_]+'` over `*.py`/`*.rs` at v0.30.0 (176 strings), v0.31.0 (188), v0.32.0 (210); every new string located outside `tests/`. First release per PR from `git log v0.30.0..v0.31.0`. PR states: one GraphQL query, all MERGED.

| Ref | URL | Last verified | Result | Notes |
|---|---|---|---|---|
| vLLM V1 metrics source (loggers.py) @ v0.32.0 | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/v1/metrics/loggers.py | 2026-10-18 | new-feature | 1453 lines (1295 at v0.30.0). 38 -> 42 `name="vllm:…"`: `num_requests_kv_fetch_by_stage` (L573, `is_kv_consumer` only), `watermark_requests` (L644, `watermark_config` only), `prompt_tokens_cached_by_source` (L782), `admission_rejections` (L848, labels `model_name`,`reason` — no `engine`). No removals. Bucket default values in `buckets.py` byte-identical to v0.30.0. |
| PR #55812 — admission rejection metrics | https://github.com/vllm-project/vllm/pull/55812 | 2026-10-18 | new-feature | v0.32.0. Incremented in `vllm/v1/engine/async_llm.py` when `--max-num-queued-reqs`/`--max-num-queued-tokens` reject. Applied to catalog § Queue. |
| PR #58874 — KV-fetch stage gauges | https://github.com/vllm-project/vllm/pull/58874 | 2026-10-18 | new-feature | v0.32.0. Stages from `KV_FETCH_STAGES` in `stats.py`; consumer = `kv_role` in `kv_consumer`/`kv_both` (`vllm/config/kv_transfer.py`). Applied to catalog § Queue. |
| PR #56318 — cached prompt tokens by tier | https://github.com/vllm-project/vllm/pull/56318 | 2026-10-18 | new-feature | v0.32.0. Sources from `vllm/v1/metrics/cache_hit_source.py`. Also registered by Rust `scheduler.rs`. Applied to catalog § Token throughput. |
| PR #58715 — watermark status counter | https://github.com/vllm-project/vllm/pull/58715 | 2026-10-18 | new-feature | v0.32.0. `skipped` set in `input_processor.py apply_watermarking` (requested, engine watermarking, not applicable). Applied to catalog § Request outcomes. |
| PR #48867 — `--custom-histogram-buckets` | https://github.com/vllm-project/vllm/pull/48867 | 2026-10-18 | new-feature | v0.32.0. `ObservabilityConfig.custom_histogram_buckets`, validators in `vllm/config/observability.py`; family list in `buckets.py BucketFamilyKey`. No reference in `rust/` at v0.32.0. Applied to catalog § Bucket boundaries, `alerting.md` § Histogram bucket coverage. |
| PR #55702 — comma form of `--collect-detailed-traces` removed | https://github.com/vllm-project/vllm/pull/55702 | 2026-10-18 | deprecation | v0.31.0 (Breaking Changes). Removed the permutation `choices` from `arg_utils.py`; list args are `nargs="+"`. Applied to SKILL.md § Tracing, `tracing.md`. |
| PR #55854 — NIXL transport failures split from KV expiry | https://github.com/vllm-project/vllm/pull/55854 | 2026-10-18 | semantics change | v0.31.0. `nixl/stats.py`: `nixl_num_failed_transfers` now sums transfer + handshake + notification failures; `nixl_num_failed_notifications` documented as retained subset. Applied to catalog § KV connector, SKILL.md version notes. |
| PR #58875 — NIXL notifications after expiry | https://github.com/vllm-project/vllm/pull/58875 | 2026-10-18 | new-feature | v0.32.0. `vllm:nixl_num_notifications_after_expiry` in `nixl/stats.py`. Applied to catalog § KV connector. |
| PRs #58949, #59485 — HiSparse host-tier metrics | https://github.com/vllm-project/vllm/pull/59485 | 2026-10-18 | new-feature | v0.32.0. 2 gauges (#58949) + 3 residency histograms gated by `--kv-cache-metrics` (#59485) in `hisparse/stats.py`. Applied to catalog § KV connector. |
| PR #50045 — tiering back-pressure | https://github.com/vllm-project/vllm/pull/50045 | 2026-10-18 | new-feature | v0.31.0. 3 names in `vllm/v1/kv_offload/tiering/base.py`, recorded in `tiering/metrics.py`. Applied to catalog § KV connector. |
| PR #57251 — SimpleCPUOffloadConnector metrics | https://github.com/vllm-project/vllm/pull/57251 | 2026-10-18 | new-feature | v0.31.0. 5 names in `vllm/v1/simple_kv_offload/metrics.py`; caveats from `docs/usage/metrics.md` at v0.32.0. Applied to catalog § KV connector. |
| PRs #57033, #59937 — Rust frontend preemption histogram, corrupted counter | https://github.com/vllm-project/vllm/pull/59937 | 2026-10-18 | new-feature | #57033 v0.31.0, #59937 v0.32.0, both in `rust/src/metrics/src/request.rs`. Applied to catalog § Rust frontend parity table. |
| Sleep-mode / RL weight-update operation metrics (#52864, #55781) | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/entrypoints/serve/dev/sleep/metrics.py | 2026-10-18 | new-feature | v0.32.0. `vllm/entrypoints/serve/dev/sleep/metrics.py`, `vllm/entrypoints/rl/online/metrics.py`; label `operation` only. Applied to catalog § Queue + label exceptions. |
| `vllm:gpu_cache_usage_perc` removal tag | https://github.com/vllm-project/vllm/blob/v0.11.1/vllm/v1/metrics/loggers.py | 2026-10-18 | fresh | Tag-wide grep for `vllm:gpu_cache_usage_perc`: present in `v1/metrics/loggers.py` at v0.10.2, v0.11.0, v0.11.1; absent from all of `vllm/` at v0.12.0 and v0.32.0. `--show-hidden-metrics-for-version` therefore cannot restore it on v0.12.0+. |
| Tiering constant names (`BLOCK_*` → `CHUNK_*`) | https://github.com/vllm-project/vllm/blob/v0.30.0/vllm/v1/kv_offload/tiering/base.py | 2026-10-18 | fresh | Grep for `_QUERIES = `: v0.29.0 `BLOCK_QUERIES = "vllm:kv_offload_tiering_chunk_queries"`; v0.30.0–v0.32.0 `CHUNK_QUERIES`. Exported string unchanged since v0.28.0. |
| Medium OTel tracing post, DeepWiki production-stack dashboards, hud.pytorch.org | (see `tracing.md`, `dashboards.md`, `alerting.md`) | 2026-10-18 | fresh | Bare curl 403/429; all three load in the logged-in browser (titles match). HUD showed no records in its default 7-day range. |

Also checked, not applied: #57070 (MFU activation bytes from model dtype — changes only fp32 models, H100/H200 fleets run bf16/fp8); #54990 (log line drops 0.0% prefix hit rate before any query — log-only); #54960 (EC connector stats framework — no concrete Prometheus names in tree at v0.32.0); #58947 (scheduler `skipped_waiting` rework — no metric name or label change); KVCR `vllm:{name}` metrics in `tiering/kvcr/manager.py` (unchanged since v0.30.0).

## Next freshen triggers

Re-probe when any of the following change:
- vLLM release > **v0.32.0** (published 2026-10-18). Run the tree-wide `"vllm:` string diff over `*.py` and `*.rs` (not just `loggers.py`), then read every `git log <prev>..<new>` commit touching `vllm/v1/metrics`, `vllm/config/observability.py`, `rust/src/metrics`, `*/stats.py`/`*/metrics.py` under `kv_transfer`, `kv_offload`, `simple_kv_offload` — semantic changes (e.g. #55854's widened counter) add no new name.
- Ray Serve integration changes (Ray 2.52+ behavior).
- DCGM exporter 4.1+ (field-name drift).
- `examples/observability/` directory restructure (watch for a `dashboards/v2/` or similar).
- Langfuse / Tempo feature changes that affect operator defaults.
