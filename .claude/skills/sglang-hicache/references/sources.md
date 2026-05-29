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
| sgl-project/sglang main | https://github.com/sgl-project/sglang | 2026-05-29 | Repo root. `main` = post-v0.5.12.post1 dev line |
| Latest stable tag | https://github.com/sgl-project/sglang/releases/tag/v0.5.12.post1 | 2026-05-29 | v0.5.12.post1 cut 2026-05-26 (isLatest). v0.5.12 2026-05-16. v0.5.11 2026-05-05. v0.5.10.post1 2026-04-09 |
| `server_args.py:5635-5733` flag definitions | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/server_args.py | 2026-04-25 | argparse definitions for all `--hicache-*` flags |
| `server_args.py:_handle_hicache` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/server_args.py#L3100-L3200 | 2026-04-25 | Auto-rewrite normalisation rules — silent flips with WARNING logs |
| `mem_cache/hiradix_cache.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/hiradix_cache.py | 2026-04-25 | `HiRadixCache` class |
| `mem_cache/hi_mamba_radix_cache.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/hi_mamba_radix_cache.py | 2026-04-25 | `HiMambaRadixCache` for hybrid SSM models |
| `managers/cache_controller.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/cache_controller.py | 2026-04-25 | `HiCacheController` with two CUDA streams + two daemon threads |
| `mem_cache/storage/backend_factory.py` | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/mem_cache/storage/backend_factory.py | 2026-04-25 | `StorageBackendFactory` — backend selection logic |

## Open bugs (release-blocker tier)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| #22607 PP + HiCache consistency meta | https://github.com/sgl-project/sglang/issues/22607 | 2026-05-29 | **Still OPEN**. #22878 also open. Did NOT make the v0.5.11/v0.5.12 cut. Workaround: pp_size = 1 |
| #19212 write_back crashes under load | https://github.com/sgl-project/sglang/issues/19212 | 2026-05-29 | Open since 2026-02-24. Workaround: write_through (the default) |
| #23659 SWA HiRadixCache rejection | https://github.com/sgl-project/sglang/issues/23659 | 2026-05-29 | **CLOSED 2026-05-08**. Resolved by PR #23391 (merged 2026-05-06), shipped in v0.5.11 |
| #23429 Mamba+write_back host-pool crash | https://github.com/sgl-project/sglang/issues/23429 | 2026-05-29 | Open. No workaround other than write_through |
| #23457 Mooncake multi-node attach hostname bug | https://github.com/sgl-project/sglang/issues/23457 | 2026-05-29 | Open. Inject MOONCAKE_LOCAL_HOSTNAME per node |
| #21880 file backend slow in containers | https://github.com/sgl-project/sglang/issues/21880 | 2026-05-29 | Open. Don't use `file` in production |
| #16797 Mooncake 0.5.6+ TTFT regression | https://github.com/sgl-project/sglang/issues/16797 | 2026-05-29 | **CLOSED 2026-05-12**. Fixed in v0.5.11/v0.5.12. Pin 0.3.10.post1 only on older builds |
| #19737 sgl-kernel 0.3.21 + FA3 + MoE + SXM IMA | https://github.com/sgl-project/sglang/issues/19737 | 2026-05-29 | Open. Install sgl-kernel from GitHub Release artifact, not PyPI |
| #22105 input-length validation rejects L1+L2 fits | https://github.com/sgl-project/sglang/issues/22105 | 2026-05-29 | Open. Workaround `--allow-auto-truncate` (silent truncation) |
| #20529 GLM5 pp2 indexer shape mismatch | https://github.com/sgl-project/sglang/issues/20529 | 2026-05-29 | Open since 2026-03-13. Same root cause as #22607 |
| #22757 GLM5/DSA L3 segfault on H20 | https://github.com/sgl-project/sglang/issues/22757 | 2026-05-29 | Open. No clean workaround |
| #22572 3FS hybrid/DSA support | https://github.com/sgl-project/sglang/issues/22572 | 2026-05-29 | **CLOSED 2026-04-25**. PR #23241 shipped in v0.5.11 |

## Recently merged PRs (hybrid model support)

| Source | URL | Last verified | Notes |
|---|---|---|---|
| PR #21259 Mooncake DSA + Mamba | https://github.com/sgl-project/sglang/pull/21259 | 2026-04-25 | Merged 2026-04-14. Lands in v0.5.10. Bench: Qwen3.5-9B TTFT 714 ms cold → 218 ms warm, throughput 11.6k → 20.9k tok/s |
| PR #23241 3FS DSA + Mamba | https://github.com/sgl-project/sglang/pull/23241 | 2026-05-29 | Merged. Shipped in v0.5.11 |
| PR #23391 SWA support in HiRadixCache | https://github.com/sgl-project/sglang/pull/23391 | 2026-05-29 | **MERGED 2026-05-06**, shipped in v0.5.11 (day-0 Gemma 4). Closed #23659 |
| PR #22878 Channel-B writing_check budget cap | https://github.com/sgl-project/sglang/pull/22878 | 2026-05-29 | **Still OPEN**. Part of PP+HiCache fix plan, not yet merged into v0.5.11/v0.5.12 |
| PR #22894 Emit KV events for L2 host insertions | https://github.com/sgl-project/sglang/pull/22894 | 2026-04-25 | Merged 2026-04-21. Restores L2 promotion observability |
| PR #19518 Spec v2 + decode KV offloading | https://github.com/sgl-project/sglang/pull/19518 | 2026-04-25 | Merged in v0.5.10. Lifted "Spec v2 and decode offload kv cache are incompatible" block |

## Backend-specific external sources

| Source | URL | Last verified | Notes |
|---|---|---|---|
| Mooncake × SGLang HiCache integration | https://kvcache-ai.github.io/Mooncake/getting_started/examples/sglang-integration/hicache-integration-v1.html | 2026-04-25 | Mooncake-side config recipe |
| Mooncake × SGLang HiCache benchmark | https://kvcache-ai.github.io/Mooncake/performance/sglang-hicache-benchmark-results-v1.html | 2026-04-25 | 8× H800 + Qwen3-235B + 8× mlx5; 2× A10 + Qwen3-14B + 2× 100Gbps eRDMA |
| Alibaba Tair × SGLang HiCache blog | https://www.alibabacloud.com/blog/_602767 | 2026-04-25 | Cross-references Novita Qwen3-Coder-480B numbers |
| Strata: Hierarchical Context Caching paper | https://arxiv.org/html/2508.18572v1 | 2026-04-25 | arXiv 2508.18572. Academic background — not normative for production decisions |

## Versions

- **Stable**: v0.5.12.post1 (2026-05-26, isLatest), v0.5.12 (2026-05-16), v0.5.11 (2026-05-05). Earlier: v0.5.10.post1 (2026-04-09), v0.5.10 (2026-04-06).
- **v0.5.11 milestones** (shipped 2026-05-05): SWA HiCache (PR #23391), 3FS Mamba/DSA (PR #23241), and the Mooncake TTFT-regression fix (#16797 closed 2026-05-12).
- **Repo `main`**: post-v0.5.12.post1 dev line.
- **Mooncake transfer engine**: 0.3.10.post1 historically bundled (PR #21844); the #16797 TTFT regression that motivated the pin was fixed in the v0.5.11/v0.5.12 line, so the pin is load-bearing only on pre-v0.5.11 builds. Re-confirm the bundled version with `scripts/inspect-sglang-image.sh v0.5.12.post1` before relying on a specific Mooncake version.
