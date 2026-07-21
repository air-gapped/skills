# Improvement Backlog — vllm-observability

Work-not-done log from skill-improver passes. Open = attempted-but-not-applied or deferred verification; not a wishlist.

## Open

- **Re-probe non-GitHub sources online** (Dim 9) — `references/sources.md` rows for the production metrics doc (docs.vllm.ai), ebpfchirp incident article, DCGM dashboard 15117, and the canonical design doc were NOT re-probed this pass (probe budget spent on the accuracy-gating GitHub refs: PRs #24245/#25392, loggers.py, examples/observability tree). They remain stamped 2026-04-24 (34 days old, within the 90-day no-cap window). Verify each URL resolves and content matches on the next freshen pass.

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
