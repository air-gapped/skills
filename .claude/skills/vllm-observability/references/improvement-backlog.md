# Improvement Backlog — vllm-observability

Work-not-done log from skill-improver passes. Open = attempted-but-not-applied or deferred verification; not a wishlist.

## Open

- **(new 2026-08-11) Undocumented observability flags** (Dim 5) — `vllm/config/observability.py` at v0.27.0 carries several operator-visible switches the catalog never mentions: `cudagraph_metrics` (padded/unpadded token counts and runtime cudagraph dispatch modes — **log-only, emitted via `CUDAGraphLogging`, not Prometheus**), `enable_layerwise_nvtx_tracing` (per-layer NVTX ranges, incompatible with CUDA graphs), `enable_logging_iteration_details`, and `jit_monitor_mode` / `jit_monitor_verbose` (post-warmup JIT compilation events). Verified present at v0.25.1 as well, so this is a **pre-existing catalog gap, not drift** — out of scope for `freshen`, and left for an `improve` pass. The log-vs-Prometheus distinction is the load-bearing part: `cudagraph_metrics` will not appear on `/metrics`.

- ~~**Re-probe non-GitHub sources online**~~ (Dim 9) — **CLOSED 2026-08-11.** All four rows (docs.vllm.ai metrics page, ebpfchirp article, DCGM dashboard 15117, canonical design doc) probed; all HTTP 200. Carried unprobed since 2026-04-24 through two passes — and the deferral was hiding content, not just staleness: the docs.vllm.ai page documents the concrete NIXL series that replaced a `vllm:nixl_*` wildcard in the catalog.

## Resolved — 2026-08-11 (freshen)

The 2026-07-21 trigger fired twice over — **v0.26.0** and **v0.27.0** both
shipped. The prescribed `loggers.py` name diff ran first and came back **clean**:
37 names at v0.27.0, identical to v0.25.1, `gpu_cache_usage_perc` still absent.

- **The pass's real finding was in this skill's own catalog, not upstream.** The
  § KV connector / offload table had been published with names marked "(approx)",
  and **two of the three were misspelled**: `vllm:kv_offload_total_time_seconds`
  and `vllm:kv_offload_size_bytes` do not exist — the real names are
  `vllm:kv_offload_total_time` and `vllm:kv_offload_size`. For a metrics catalog
  this is the worst failure mode available: a PromQL query on a non-existent
  series returns no data silently, so the dashboard looks fine and stays empty.
  Replaced the whole section with names read verbatim from the v0.27.0 tree.
- **The offload surface also moved substantially across v0.26.0/v0.27.0** and the
  `loggers.py` diff could not see any of it, because these metrics are declared
  in `vllm/v1/kv_offload/` and
  `vllm/distributed/kv_transfer/kv_connector/v1/offloading/`. Current shape:
  direction-split `kv_offload_{load,store}_{bytes,time,size}` replacing the
  aggregated legacy trio; CPU read/write usage gauges split (#47666, v0.26.0);
  tiering lookup delay split into sync/async histograms (#47679, v0.26.0). The
  three legacy names are deprecated **and** only observed under a
  `CPUOffloadingSpec` — on any other spec they register but never increment.
- **NIXL wildcard replaced with real names.** The long-deferred docs.vllm.ai
  probe turned out to document seven concrete `vllm:nixl_*` series; the two
  failure counters and `nixl_num_kv_expired_reqs` are the alertable ones.
- **Closed the two-pass-old Open item.** All four non-GitHub rows probed, all
  HTTP 200. The design doc was fetched raw at v0.27.0 and independently
  corroborates the rename saga (`gpu_cache_usage_perc`: 0 occurrences).
- **Sharpened the next trigger** to run the loggers.py diff **and** a kv_offload
  constant sweep — naming the gap that let this drift through.

## Resolved — 2026-07-21 (freshen)

The 2026-05-28 trigger fired (latest is now **v0.25.1**, four minors past the
">v0.22" threshold). Re-ran the `loggers.py` name diff at tag v0.25.1 — the
cheap mechanical check that does most of the work here — plus a release-body
sweep for metrics/observability changes.

- **Catalog integrity confirmed, not assumed.** Extracted every
  `name="vllm:..."` declaration at v0.25.1 and diffed against the catalog:
  **no catalogued name removed or renamed**, `gpu_cache_usage_perc` still
  absent. The apparent "missing" entries in the raw diff were all deliberate —
  V0 deprecated names the skill documents on purpose, histogram `_bucket`
  suffixes, and metrics defined in other modules (spec-decode, MFU, KV
  connector). Recorded so a future pass doesn't re-litigate them.
- **Two additions that invalidate previously collected data** (the pass's real
  value — both are "your existing numbers were wrong", not "here's a new
  gauge"):
  - **#42206** (v0.24.0) — `vllm:cache_config_info` gains group-aware
    `kv_cache_size_tokens` and `kv_cache_max_concurrency`. Upstream states
    `num_gpu_blocks * block_size` "can be wrong for hybrid models where
    requests occupy multiple KV cache groups" — the startup log was right and
    Prometheus-derived capacity was not (issue #42024). Any dashboard computing
    the product has been overstating capacity on hybrid models.
  - **#39457** (v0.24.0) — `MLAAttentionMetrics`. The old estimator assumed
    MHA/GQA; for DeepSeek-V3 that means **576 vs 32,768 bytes per token per
    layer**, a ~57× KV-bandwidth overestimate. MFU figures from a DeepSeek
    deployment on < v0.24.0 are unusable, not merely imprecise.
- **Two genuinely new surfaces documented:** `vllm:tool_call_parser_invocations_total`
  (#44448, v0.24.0) with its upstream-stated non-harmony-only limit and a
  ready PromQL ratio for catching tool-calling rollout regressions; and the
  per-request response-body `metrics` field (#46768, v0.25.0), which is
  **double-gated** (`--enable-per-request-metrics` + `include_metrics`) and
  suppressed for `n > 1` / multi-prompt — both facts worth having written down
  before someone files a bug about missing fields.
- **Sharpened the next trigger** to "> v0.25.1, and re-run the loggers.py name
  diff" — naming the mechanism, since that diff is what caught these.

**Carried forward unchanged:** the single Open item below (re-probe the four
non-GitHub sources: docs.vllm.ai metrics page, ebpfchirp article, DCGM
dashboard 15117, canonical design doc). Not attempted this pass either — the
budget again went to the version-sensitive GitHub refs, which is the right
trade, but it means those rows are now ~3 months stale and should lead the
next pass rather than trail it.

## Resolved this pass (2026-05-28)

- Deleted editorializing sentence "This table is the skill's single most valuable line. Everything else is how to read the underlying metrics." in `SKILL.md` core-diagnostic section (Dim 6) — the queue-depth x TPOT table stands on its own; no instruction lost.
- Trimmed PR-number/date forensics out of the frontmatter `description` block scalar in `SKILL.md` (Dim 1, 644 -> 627 chars; combined desc+when_to_use 1389, under the 1536 listing cap). Kept the `gpu_->kv_ rename saga` trigger keyword; the PR #24245/#25392 forensics still live verbatim in the Version notes section.
- Restamped 4 re-confirmed GitHub source rows in `references/sources.md` to 2026-05-28 (PR #24245 MERGED 2025-09-16; PR #25392 CLOSED-unmerged 2025-09-23; loggers.py emits all cited names with `gpu_cache_usage_perc` absent; examples/observability tree intact) — Dim 9 staleness reset on the version-sensitive refs.
- Annotated the `references/sources.md` "Next freshen triggers" bullet: observed current latest release is v0.21.0 (2026-05-15), still below the ">v0.22" re-probe trigger, so no version-drift mutation is due.
- Restamped the `references/metrics-catalog.md` "Last verified" header from 2026-04-24 to 2026-05-28 with a re-probe note.

## Process note

An intermittent tool-output channel outage struck twice this session (Bash/Read returning empty or stale results). The first APPLY attempt produced a StructuredOutput based on stale file-state context that claimed edits which had NOT landed (notably a "stray fence removal" that was never real — all files have balanced fence parity, confirming the recon's retraction of the earlier hallucinated fence defect). That output is superseded. The edits recorded above are the ones whose Edit calls returned explicit success-with-integrity-check confirmations against freshly-Read file content.
