# Sources — dated URL index for freshen mode

Each row records the authoritative source for a claim in this skill. Freshen mode probes these and updates `Last verified:` dates.

## Official documentation

| Source | URL | Last verified | Notes |
|---|---|---|---|
| LMSYS HiCache blog (2025-09-10) | https://www.lmsys.org/blog/2025-09-10-sglang-hicache/ | 2026-04-25 | Architecture overview + headline performance numbers (Novita TTFT –56%, Ant Group TTFT –84%, "up to 6×/80%" uncited) |
| SGLang HiCache user doc | https://docs.sglang.ai/advanced_features/hicache.html | 2026-04-25 | User-facing entry-point. Mirrored in the local repo at `docs/advanced_features/hicache.rst` |
| SGLang HiCache design doc | https://docs.sglang.ai/advanced_features/hicache_design.html | 2026-04-25 | Class architecture, write/read paths, eviction. Local: `docs/advanced_features/hicache_design.md` |
| SGLang HiCache best-practices | https://docs.sglang.ai/advanced_features/hicache_best_practices.html | 2026-04-25 | Recommended flag combos. Local: `docs/advanced_features/hicache_best_practices.md` |
| SGLang HiCache runtime attach/detach | https://docs.sglang.ai/advanced_features/hicache_storage_runtime_attach_detach.html | 2026-04-25 | HTTP admin API for L3 swap without engine restart. Local: `docs/advanced_features/hicache_storage_runtime_attach_detach.md` |
| SGLang server-arguments doc | https://docs.sglang.ai/references/server_arguments.html | 2026-04-25 | Canonical flag list. Trust `python -m sglang.launch_server --help` over the doc when they disagree |

## Repository (source of truth for flags)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| sgl-project/sglang main | https://github.com/sgl-project/sglang | 2026-07-21 | Repo root. `main` = post-v0.5.15.post1 dev line |
| Latest stable tag | https://github.com/sgl-project/sglang/releases/tag/v0.5.15.post1 | 2026-07-21 | **v0.5.15.post1 cut 2026-07-14 (isLatest)**. v0.5.15 07-10, v0.5.14 06-26, v0.5.13 06-13, v0.5.12.post1 05-26, v0.5.11 05-05 |
| `server_args.py` hicache field definitions | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/server_args.py | 2026-07-21 | **Refactored to annotated-dataclass form** (`A[type, Arg(...)]`) — the old `:5635-5733` argparse line range no longer resolves; flags derive from field names. At v0.5.15.post1: write-policy gains `write_through_selective`; io-backend defaults to `kernel` and gains `kernel_ascend`; mem-layout defaults to `page_first` and gains `page_first_kv_split` + `page_head`; storage-backend gains `mori`. A separate `--enable-hisparse` / `--hisparse-config` subsystem now sits next to the hicache block |
| `server_args.py:_handle_hicache` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/server_args.py#L3100-L3200 | 2026-04-25 | Auto-rewrite normalisation rules — silent flips with WARNING logs |
| `mem_cache/hiradix_cache.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/hiradix_cache.py | 2026-04-25 | `HiRadixCache` class |
| `mem_cache/hi_mamba_radix_cache.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/hi_mamba_radix_cache.py | 2026-04-25 | `HiMambaRadixCache` for hybrid SSM models |
| `managers/cache_controller.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/cache_controller.py | 2026-04-25 | `HiCacheController` with two CUDA streams + two daemon threads |
| `mem_cache/storage/backend_factory.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/storage/backend_factory.py | 2026-04-25 | `StorageBackendFactory` — backend selection logic |

## Open bugs (release-blocker tier)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| #22607 PP + HiCache consistency meta | https://github.com/sgl-project/sglang/issues/22607 | 2026-07-21 | **Still OPEN** (activity 2026-07-10). PR #22878 **closed without merging**. Workaround: pp_size = 1 |
| #30760 HiCache prefetch all_reduce deadlock, TP=4 no PP | https://github.com/sgl-project/sglang/issues/30760 | 2026-07-21 | **NEW, OPEN** (2026-07-10). Split out of #22607 as the TP-only case. Mismatched all_reduce call count across ranks. No published workaround — undermines the assumption that TP-only deploys dodge the #22607 family |
| #19212 write_back crashes under load | https://github.com/sgl-project/sglang/issues/19212 | 2026-07-21 | **CLOSED COMPLETED 2026-05-24.** Reporter confirmed PRs #22592 (merged 2026-04-16) + #23696 (merged 2026-05-01) fix it. write_through remains the default |
| #23659 SWA HiRadixCache rejection | https://github.com/sgl-project/sglang/issues/23659 | 2026-05-29 | **CLOSED 2026-05-08**. Resolved by PR #23391 (merged 2026-05-06), shipped in v0.5.11 |
| #23429 Mamba+write_back host-pool crash | https://github.com/sgl-project/sglang/issues/23429 | 2026-07-21 | **CLOSED COMPLETED 2026-04-25** |
| #23457 Mooncake multi-node attach hostname bug | https://github.com/sgl-project/sglang/issues/23457 | 2026-07-21 | **CLOSED COMPLETED 2026-06-15** (closed by the reporter) |
| #21880 file backend slow in containers | https://github.com/sgl-project/sglang/issues/21880 | 2026-07-21 | **CLOSED 2026-06-18 BY THE STALE BOT — not fixed.** Last substantive comment 2026-04-18 reproduced it. Keep treating `file` as dev-only; v0.5.15 #26670 (CP-aware LRU eviction on this backend) may have changed the picture — measure, don't assume |
| #16797 Mooncake 0.5.6+ TTFT regression | https://github.com/sgl-project/sglang/issues/16797 | 2026-05-29 | **CLOSED 2026-05-12**. Fixed in v0.5.11/v0.5.12. Pin 0.3.10.post1 only on older builds |
| #19737 sgl-kernel 0.3.21 + FA3 + MoE + SXM IMA | https://github.com/sgl-project/sglang/issues/19737 | 2026-07-21 | **CLOSED COMPLETED 2026-05-03** |
| #22105 input-length validation rejects L1+L2 fits | https://github.com/sgl-project/sglang/issues/22105 | 2026-07-21 | Still OPEN (activity 2026-06-02). Workaround `--allow-auto-truncate` (silent truncation) |
| #20529 GLM5 pp2 indexer shape mismatch | https://github.com/sgl-project/sglang/issues/20529 | 2026-07-21 | **CLOSED COMPLETED 2026-05-20** |
| #22757 GLM5/DSA L3 segfault on H20 | https://github.com/sgl-project/sglang/issues/22757 | 2026-07-21 | **CLOSED 2026-06-14 BY THE STALE BOT — not confirmed fixed.** Candidate PR #22120 was suggested 2026-04-14 but never confirmed on the thread. Treat as a live risk |
| #22572 3FS hybrid/DSA support | https://github.com/sgl-project/sglang/issues/22572 | 2026-05-29 | **CLOSED 2026-04-25**. PR #23241 shipped in v0.5.11 |

## Recently merged PRs (hybrid model support)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| PR #21259 Mooncake DSA + Mamba | https://github.com/sgl-project/sglang/pull/21259 | 2026-04-25 | Merged 2026-04-14. Lands in v0.5.10. Bench: Qwen3.5-9B TTFT 714 ms cold → 218 ms warm, throughput 11.6k → 20.9k tok/s |
| PR #23241 3FS DSA + Mamba | https://github.com/sgl-project/sglang/pull/23241 | 2026-05-29 | Merged. Shipped in v0.5.11 |
| PR #23391 SWA support in HiRadixCache | https://github.com/sgl-project/sglang/pull/23391 | 2026-05-29 | **MERGED 2026-05-06**, shipped in v0.5.11 (day-0 Gemma 4). Closed #23659 |
| PR #22878 Channel-B writing_check budget cap | https://github.com/sgl-project/sglang/pull/22878 | 2026-07-21 | **CLOSED WITHOUT MERGING.** The PP+HiCache fix did not land via this PR; #22607 stays open |
| PR #27759 HybridModel launches HiCache via UnifiedTree by default | https://github.com/sgl-project/sglang/pull/27759 | 2026-07-21 | **MERGED 2026-06-11, shipped v0.5.13.** Hybrid (SWA/Mamba) models get HiCache by default — the most consequential HiCache change of this window |
| PR #26670 opt-in CP-aware LRU eviction, file backend | https://github.com/sgl-project/sglang/pull/26670 | 2026-07-21 | MERGED 2026-06-11, shipped v0.5.15 line. Touches the backend that #21880 complained about |
| PR #22894 Emit KV events for L2 host insertions | https://github.com/sgl-project/sglang/pull/22894 | 2026-04-25 | Merged 2026-04-21. Restores L2 promotion observability |
| PR #19518 Spec v2 + decode KV offloading | https://github.com/sgl-project/sglang/pull/19518 | 2026-04-25 | Merged in v0.5.10. Lifted "Spec v2 and decode offload kv cache are incompatible" block |

## Backend-specific external sources

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Mooncake × SGLang HiCache integration | https://kvcache-ai.github.io/Mooncake/getting_started/examples/sglang-integration/hicache-integration-v1.html | 2026-04-25 | Mooncake-side config recipe |
| Mooncake × SGLang HiCache benchmark | https://kvcache-ai.github.io/Mooncake/performance/sglang-hicache-benchmark-results-v1.html | 2026-04-25 | 8× H800 + Qwen3-235B + 8× mlx5; 2× A10 + Qwen3-14B + 2× 100Gbps eRDMA |
| Alibaba Tair × SGLang HiCache blog | https://www.alibabacloud.com/blog/_602767 | 2026-04-25 | Cross-references Novita Qwen3-Coder-480B numbers |
| Strata: Hierarchical Context Caching paper | https://arxiv.org/html/2508.18572v1 | 2026-04-25 | arXiv 2508.18572. Academic background — not normative for production decisions |

## 2026-07-21 freshen pass

SGLang moved three minors (v0.5.12.post1 → v0.5.15.post1). Headline: **v0.5.13 makes HiCache the default path for hybrid SWA/Mamba models via UnifiedTree (#27759)**, superseding the per-arch opt-in matrix. Bug state moved a lot: #19212 (`write_back` crash), #23429, #23457, #19737 and #20529 all closed **with fixes**, while #21880 (`file` backend slow) and #22757 (GLM5/DSA H20 segfault) were closed **by the stale bot with no fix** — those two are recorded as live risks, not resolutions. #22607 (PP + HiCache) is still open and its fix PR #22878 was closed unmerged; a new TP-only sibling #30760 opened 2026-07-10. Flag surface changed (new write-policy / io-backend / mem-layout / storage-backend choices, `server_args.py` refactored to annotated dataclasses). Cross-skill: the "vLLM is broken on 2026 hybrids" framing used to justify this skill's existence is now stale — corrected in SKILL.md, `hybrid-models.md`, and `migration-from-vllm-caching.md`. Not re-probed: LMSYS blog + docs.sglang.ai pages, Mooncake/Tair/arXiv rows, the `mem_cache/` source-file rows (2026-04-25 stamps stand).

## Versions

- **Stable**: v0.5.15.post1 (2026-07-14, isLatest), v0.5.15 (2026-07-10), v0.5.14 (2026-06-26), v0.5.13 (2026-06-13). Earlier: v0.5.12.post1 (2026-05-26), v0.5.11 (2026-05-05).
- **v0.5.11 milestones**: SWA HiCache (PR #23391), 3FS Mamba/DSA (PR #23241), Mooncake TTFT-regression fix (#16797 closed 2026-05-12).
- **v0.5.13 milestones**: HiCache-by-default for hybrid models via UnifiedTree (#27759); decode-side HiCache incremental KV transfer (#26227); Spec V2 becomes the default speculative path.
- **v0.5.14–v0.5.15 HiCache work**: int8 checkpoint pool for linear-attention states (#28185), hybrid-pool staged H2D kernel (#28434), asymmetric pool direct backend (#28446), MiMo-V2 HiCache (#27378), file-backend CP-aware LRU eviction (#26670), NIXL bucketed multi-dir file layout (#27672) + FILE cache cleaner (#28258), Mooncake group semantics (#26574), bulk-token-byte hashing (#28287), AMD UMBP tiered DRAM+SSD L3 backend (#25377).
- **Repo `main`**: post-v0.5.15.post1 dev line.
- **Mooncake transfer engine**: 0.3.10.post1 historically bundled (PR #21844); the #16797 TTFT regression that motivated the pin was fixed in the v0.5.11/v0.5.12 line, so the pin is load-bearing only on pre-v0.5.11 builds. Re-confirm the bundled version with `scripts/inspect-sglang-image.sh v0.5.12.post1` before relying on a specific Mooncake version.
