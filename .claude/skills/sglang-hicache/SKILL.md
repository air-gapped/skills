---
name: sglang-hicache
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, WebFetch
description: |-
  SGLang HiCache (hierarchical KV cache) — three-tier prefix cache: GPU HBM (L1) → pinned host DRAM (L2) → distributed L3 (Mooncake / 3FS / NIXL / AIBrix / EIC / SiMM / file / LMCache). Covers `--enable-hierarchical-cache`, all `--hicache-*` flags, write policies, page_first* layouts, prefetch policy (best_effort / wait_complete / timeout), per-rank sizing, MHA / MLA / DSA / Mamba / SWA support matrix (SWA + 3FS hybrid shipped in v0.5.11), runtime attach/detach HTTP admin, and auto-rewrite startup log lines that silently substitute layout × IO × storage combinations.
when_to_use: |-
  Trigger on "sglang hicache", "hierarchical cache", "sglang kv offload / cache / prefix caching", "sglang ttft too slow", "sglang long context", "--enable-hierarchical-cache", "--hicache-ratio / size / storage-backend / write-policy / io-backend / mem-layout / storage-prefetch-policy", "page_first / layer_first / page_first_direct", "mooncake / 3fs / hf3fs / nixl / aibrix / eic / simm backend", "hicache runtime attach / detach", "DeepSeek R1 / V3.2 prefix cache", "Qwen3-Next / Qwen3.5 sglang cache", "Gemma 3-4 sliding window sglang", "Mamba / SSM state offload", "DSA / NSA indexer offload", "PD-disagg decode kv offload", "sglang vs vllm caching", "sglang hybrid model caching", "migrating from LMCache to sglang". Audit / review `sglang.launch_server` invocations referencing hicache flags. Defer to `vllm-caching` for vLLM, and `nvidia-nixl` for transport-level NIXL details.
---

# SGLang HiCache — hierarchical KV cache

Target audience: operators running SGLang on H100/H200/H20/B200-class datacenter GPUs in production, especially long-context agentic workloads (coding agents, RAG, multi-turn chat) with strong prefix locality.

## Why this matters

Long-context inference is almost always KV-cache bound, not compute bound. HiCache extends effective KV capacity beyond HBM through pinned host DRAM (L2) and an optional distributed L3 (Mooncake / 3FS / NIXL / AIBrix / EIC / SiMM / file). Reported gains: TTFT –56% / throughput ×2 (Novita Qwen3-Coder-480B + 3FS), TTFT –84% on cache hits (Ant Group DeepSeek-R1-671B + Mooncake) — see [LMSYS blog 2025-09-10](https://www.lmsys.org/blog/2025-09-10-sglang-hicache/). LMSYS's headline "up to 6× / up to 80%" is uncited — trust the deployment-specific numbers.

**Why this skill exists alongside `vllm-caching`:** the two stacks are now at parity on hybrid-attention models, so the choice is about topology and L3 ecosystem rather than a capability gap. **The old "vLLM is broken on 2026 hybrids" framing is stale** — vLLM's native offload gained HMA support in v0.21.0 and HMA became the default for `SupportsHMA` connectors in v0.23.0, and LMCache MP added hybrid support in its 0.5 line. SGLang HiCache reached hybrid support first (v0.5.11 SWA + 3FS Mamba/DSA, default-on via UnifiedTree in v0.5.13) and still has the broader menu of distributed L3 backends. Where vLLM's in-process `LMCacheConnectorV1` remains genuinely blocked (LMCache #3106), that is one connector, not the stack. For the arch × backend × release matrix and the "should we migrate?" decision tree, see `references/hybrid-models.md`.

> **NIXL deep-dive** — the NIXL transfer library (UCX / GDS / Mooncake / S3-OBJ plugins, agent API, telemetry) lives in the dedicated **`nvidia-nixl`** skill. This skill covers SGLang-side wiring of `--hicache-storage-backend nixl` only.

## Versions

- **Stable**: v0.5.15.post1 (2026-07-14, latest), v0.5.15 (2026-07-10), v0.5.14 (2026-06-26), v0.5.13 (2026-06-13). Earlier: v0.5.12.post1 (2026-05-26), v0.5.11 (2026-05-05).
- **v0.5.11 shipped the SWA/3FS hybrid milestones**: SWA HiCache (PR [#23391](https://github.com/sgl-project/sglang/pull/23391) merged 2026-05-06, day-0 Gemma 4), 3FS Mamba/DSA (PR #23241), hybrid CP.
- **v0.5.13 made HiCache the default for hybrid models**: `HybridModel` (SWA/Mamba) launches HiCache via **UnifiedTree** by default (PR [#27759](https://github.com/sgl-project/sglang/pull/27759), merged 2026-06-11), so hierarchical offload reaches sliding-window and Mamba hybrids out of the box rather than through arch-specific opt-in. v0.5.13 also added decode-side HiCache for incremental KV transfer (#26227). Spec V2 became the default speculative-decoding path in the same release (Spec V1 deprecated).
- **v0.5.14–v0.5.15** are HiCache-heavy: int8 checkpoint pool for linear-attention recurrent states in the Mamba radix cache (#28185), hybrid-pool staged H2D kernel (#28434), asymmetric pool direct-backend support (#28446), HiCache for MiMo-V2 (#27378), opt-in CP-aware LRU eviction on the `file` backend (#26670), bucketed multi-dir layout for NIXL file storage (#27672), a NIXL FILE cache cleaner (#28258), Mooncake group semantics (#26574), bulk-token-byte hash generation (#28287), and an AMD **UMBP** tiered DRAM + SSD L3 backend with a hugepage host allocator (#25377). A separate `--enable-hisparse` subsystem (hierarchical sparse attention) also landed and can target NIXL DRAM KV destinations (#27563) — distinct from HiCache, don't conflate the flags.
- **Image**: `lmsysorg/sglang:v0.5.15.post1` (pip-installs `mooncake-transfer-engine`; install `nixl-cu13`, `aibrix-kvcache`, `simm` etc. as needed for that backend). Confirm the bundled versions with `scripts/inspect-sglang-image.sh v0.5.15.post1` — the 0.3.10.post1 Mooncake figure was captured on the v0.5.12 line.
- **Source of truth for flags**: `python -m sglang.launch_server --help`. If this skill disagrees with `--help` on a flag spelling, trust `--help` and freshen the skill. Note `server_args.py` was refactored to annotated-dataclass form — flags are derived from field names, so old line-number citations into the argparse block no longer resolve.
- **Flag surface at v0.5.15.post1** (verified 2026-07-21 against `python/sglang/srt/server_args.py`): `--hicache-write-policy` now takes `write_through` (default), `write_back`, **`write_through_selective`**. `--hicache-io-backend` defaults to **`kernel`** and adds `kernel_ascend` alongside `direct`. `--hicache-mem-layout` defaults to `page_first` and adds **`page_first_kv_split`** and **`page_head`** to the old three. `--hicache-storage-backend` adds **`mori`** to file / mooncake / hf3fs / nixl / aibrix / dynamic / eic / simm. `--hicache-ratio` defaults to 2.0, `--hicache-size` to 0 (ratio wins unless size is set).

## Three-tier architecture, in one paragraph

L1 = GPU HBM, per-rank, owned by the engine. L2 = pinned CPU DRAM, per-rank (`MHATokenToKVPoolHost` / `MLATokenToKVPoolHost`), sized by `--hicache-ratio` or `--hicache-size`. L3 = an optional distributed pluggable backend (`HiCacheStorage` ABC, see backend table below). All three are addressed through one `HiRadixCache` (or `HiMambaRadixCache` for hybrid SSM models) which extends RadixAttention with extra `host_value` / `hash_value` fields. A `HiCacheController` runs two CUDA streams (`write_stream`, `load_stream`) for L1↔L2 transfers and two daemon threads (prefetch, backup) for L2↔L3. TP ranks synchronise hit length via `all_reduce(op=min)` over a separate `gloo` `prefetch_tp_group`. Eviction: L1 follows `--radix-eviction-policy` (LRU); L2 only frees pages already replicated to L3; L3 eviction is delegated to the L3 backend (e.g. Mooncake's `eviction_high_watermark_ratio`). For full call paths, classes, and per-tier policies, see `references/architecture.md`.

## Decision tree — pick the L3 backend

Ask in order:

1. **Single node, host-DRAM tier only, no L3 needed?** → omit `--hicache-storage-backend`. Just `--enable-hierarchical-cache --hicache-ratio 2`. The L1↔L2 pipeline alone is the 80% case and doesn't need any extra service.
2. **Cluster with RDMA fabric and a managed Mooncake deployment?** → `mooncake`. The most-tested L3 in 2026, only one with **shipped hybrid-Mamba support** (PR [#21259](https://github.com/sgl-project/sglang/pull/21259)). Requires Mooncake master + (optional) metadata server.
3. **Cluster with the DeepSeek 3FS operator already deployed?** → `hf3fs`. Best-tested with DeepSeek-R1 on H20-3e (LMSYS benchmark). Hybrid Mamba/DSA support shipped in v0.5.11 (PR #23241).
4. **NVIDIA Dynamo / GB200 / KVBM stack?** → `nixl`. Wraps 3FS / GDS / POSIX / OBJ; auto-priority `3FS > POSIX > GDS_MT > GDS > OBJ`. Use a `@config.toml` file via `--hicache-storage-backend-extra-config` — flags don't fit on one line.
5. **ByteDance AIBrix shop?** → `aibrix`. Volcengine cloud? → `eic`. Scitix RDMA cluster? → `simm`.
6. **Already standardised on LMCache and want vLLM/SGLang sharing?** → `--enable-lmcache` (an *alternative* to HiCache, not a backend underneath it). Cannot coexist with `--enable-hierarchical-cache`.
7. **Dev / CI / smoke test only?** → `file`. `SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR=/tmp/hicache`. **Do not use in production** — issue [#21880](https://github.com/sgl-project/sglang/issues/21880) documents the prefetch path as the bottleneck even with all data in CPU.

For per-backend env vars, install steps, and config recipes, see `references/storage-backends.md`.

## Baseline production config (the happy path)

The recipe in `docs/advanced_features/hicache_best_practices.md` converges across HF3FS and Mooncake examples:

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-235B-A22B-Instruct-2507 \
  --tp 8 \
  --page-size 64 \
  --enable-hierarchical-cache \
  --hicache-ratio 2 \
  --hicache-mem-layout page_first_direct \
  --hicache-io-backend direct \
  --hicache-write-policy write_through \
  --hicache-storage-backend mooncake \
  --hicache-storage-prefetch-policy timeout \
  --hicache-storage-backend-extra-config '@/etc/sglang/mooncake.toml' \
  --mem-fraction-static 0.85 \
  --enable-cache-report --enable-metrics
```

`timeout` is the only prefetch policy explicitly recommended for production SLOs in the official docs — `best_effort` runs prefetches in the background and returns the device hit even if L2/L3 is partially loaded; `wait_complete` blocks until L3 hits land (high TTFT variance); `timeout` waits up to a budget then degrades gracefully. Tune via `prefetch_timeout_base` and `prefetch_timeout_per_ki_token` in the extra-config.

For PD-disaggregation add `--disaggregation-decode-enable-offload-kvcache` (only valid with a storage backend set). For full recipes (Mooncake H100 RDMA, 3FS DeepSeek-R1, NIXL Dynamo, runtime attach/detach), see `references/recipes.md`.

## Critical pitfalls

1. **`--hicache-size` is per rank, not total.** `--hicache-size 30 --tp 8` allocates 240 GB total across ranks, not 30 GB. The opposite of vLLM's `--cpu-offload-gb` (per-GPU) and `--kv-offloading-size` (total). Operators repeatedly OOM their hosts on this. Same convention as SGLang's other `--*-size` flags.

2. **`--hicache-ratio` must be > 1.** Host pool must exceed device pool. The L2 capacity used for prefetch is `0.8 * (mem_pool_host.size − mem_pool_device.size)`, so `--hicache-ratio 1.2` leaves only ~16% of L1 for prefetched-but-not-yet-used pages — enough for spec-decode tests but chokes under multi-turn workloads. Production deployments use ratio ≥ 2.

3. **Layout × IO × storage are silently auto-rewritten at boot.** Three normalisation rules in `server_args.py:_handle_hicache`:
   - `page_first_direct` + `kernel` IO → forces IO to `direct`
   - `page_first` + `direct` IO → forces layout to `page_first_direct`
   - Mooncake + `layer_first` → forces `page_first` or `page_first_direct`
   - FA3 decode backend + non-`kernel` IO → forces `kernel` (with a "may lead to suboptimal performance with small page sizes" warning)
   
   If benchmark numbers don't match the recipe, **scan the boot-time WARNING log** for the substitution — no error, just a log line. Verify the effective layout/IO with `journalctl -u sglang | grep -iE 'switching to .* layout|FlashAttention3 decode backend|Hierarchical cache enabled'` (or `docker logs <id> 2>&1 | grep ...`).

4. **Hybrid-attention model support is version-gated, and the gate moved twice.** As of v0.5.13+ hybrids are the *default* path, not an opt-in:
   - **v0.5.13 (#27759)**: `HybridModel` (SWA/Mamba) launches HiCache through **UnifiedTree by default**. This supersedes the per-arch opt-in story below and is the single most important version line for hybrid deploys — a config tuned on v0.5.11/v0.5.12 may take a different code path after upgrade, so re-benchmark rather than assuming continuity.
   - **Mamba / SSM** (Qwen3-Next, Qwen3.5, MiniMax-M2 family): ✓ on Mooncake L3 (#21259, v0.5.10) and 3FS (#23241, v0.5.11).
   - **DSA** (DeepSeek-V3.2): ✓ via `HiMambaRadixCache` route on Mooncake (v0.5.10) and 3FS (v0.5.11).
   - **SWA** (Gemma 3-4, Mistral-class): ✓ as of v0.5.11 — PR [#23391](https://github.com/sgl-project/sglang/pull/23391) merged 2026-05-06 (day-0 Gemma 4), closing #23659. Pre-v0.5.11 raises `ValueError: HiRadixCache only supports MHA, MLA, and NSA (DSA) models` — upgrade to ≥ v0.5.11.
   - **Hybrid SWA without arch-specific guard** — `Llama4ForConditionalGeneration`, `GptOssForCausalLM`, `Gemma4ForCausalLM` were documented as having NO server-side guard (hicache treats SWA layers as full attention → memory bloat, possible quality drift). That finding predates the UnifiedTree default; **re-verify against v0.5.13+ before applying the old avoidance** (`--disable-hybrid-swa-memory`, or skipping hicache), since the default hybrid path changed underneath it.
   
   For the full arch × backend matrix and migration story from vLLM/LMCache, see `references/hybrid-models.md`.

5. **`write_back` crashes under load — fixed, but verify before switching.** Issue [#19212](https://github.com/sgl-project/sglang/issues/19212) (`AssertionError: parent does not have child key` in `evict_host()`) was **closed COMPLETED 2026-05-24**; the reporter confirmed PRs [#22592](https://github.com/sgl-project/sglang/pull/22592) (stale eviction assertion in `HiMambaRadixCache`, merged 2026-04-16) and [#23696](https://github.com/sgl-project/sglang/pull/23696) (host-protected node deletion in the HiMamba tombstone path, merged 2026-05-01) resolved it. `write_through` is still the default and still the safe choice; `write_back` is now a defensible experiment on ≥ v0.5.12 rather than a known crash.

6. **PP + HiCache is still broken.** Issue [#22607](https://github.com/sgl-project/sglang/issues/22607) (high-priority meta): async L3 prefetch + per-rank scheduler diverge under `--pp-size > 1`. Wall-clock LRU produces different victim selection on each rank → host-tree shape mismatch → crash. Still **OPEN** as of 2026-07-21 (last activity 2026-07-10), and the writing-ack-sync PR #22878 was **closed without merging**. Keep `pp_size = 1` with hicache. New in this window: [#30760](https://github.com/sgl-project/sglang/issues/30760) (opened 2026-07-10) reports a HiCache prefetch `all_reduce` deadlock with **TP=4 and no PP** — mismatched call count across ranks — so the failure mode is no longer PP-only. Watch it before assuming a TP-only deploy is safe.

7. **Mooncake 0.5.6+ TTFT 10× regression vs 0.5.5** (historically: TTFT ~0.5 s → 5+ s, hit rate ~90% → ~30%). Issue [#16797](https://github.com/sgl-project/sglang/issues/16797) was **closed 2026-05-12** — fixed in the v0.5.11/v0.5.12 line. On ≥ v0.5.11 the pin is no longer load-bearing; on older builds, still pin `mooncake-transfer-engine 0.3.10.post1` and, if TTFT regresses, try `--hicache-storage-prefetch-policy best_effort` to bypass and isolate.

8. **PyPI sgl-kernel 0.3.21 + FA3 + MoE + SXM = IMA.** Issue [#19737](https://github.com/sgl-project/sglang/issues/19737) (`CUDA_EXCEPTION_4: Warp Illegal Instruction` within ~10 min) was **closed COMPLETED 2026-05-03**. The workaround — install `sgl-kernel` from the GitHub Release artifact (built with `-DCUTLASS_ENABLE_GDC_FOR_SM90`) rather than PyPI — only matters if you are pinned to that old kernel build.

9. **Runtime attach/detach blocks until idle.** `PUT/DELETE /hicache/storage-backend` admin endpoints reject with HTTP 400 if any request is running, queued, in chunked-prefill, in PD bootstrap, or DLLM staging (`is_fully_idle()` check). With `dp_size > 1`, success is AND-aggregated across DP ranks — partial-success has no automatic rollback. Drain traffic before switching backends. Set `--admin-api-key` for production.

10. **`--page-size` is global, defaults to 1 on CUDA, recommended 64 for HiCache + L3.** Bigger pages reduce metadata / I/O overhead but lower hit rate when prefixes don't align. DeepSeek DSA forces `page_size = 64`; SSM models with `no_buffer` strategy + radix cache force `page_size = 1` and break with `trtllm_mha`. SSM with `extra_buffer` requires `mamba_track_interval % page_size == 0`.

## Open bugs to know before recommending

Issue states verified 2026-07-21. Recheck via `gh issue view <N> --repo sgl-project/sglang` before quoting.

The PP+HiCache release-blocker (#22607, plus the new TP-only #30760) is detailed with root-cause in "Critical pitfalls" #6 above — not repeated here. Still open:

| Issue | Severity | Affects | Workaround |
|---|---|---|---|
| [#30760](https://github.com/sgl-project/sglang/issues/30760) | high | HiCache prefetch `all_reduce` deadlock at **TP=4 with no PP** — mismatched call count across ranks. Opened 2026-07-10 | None published yet. Reduces confidence that TP-only deploys are unaffected by the #22607 family |
| [#22105](https://github.com/sgl-project/sglang/issues/22105) | medium | Input-length validation rejects requests that fit in L1+L2 | `--allow-auto-truncate` (silent truncation, not a real fix) |

**Closed with a fix** (no workaround needed on current releases): [#19212](https://github.com/sgl-project/sglang/issues/19212) `write_back` crash (2026-05-24, via PRs #22592 + #23696); [#23429](https://github.com/sgl-project/sglang/issues/23429) Mamba + write_back host-pool crash (2026-04-25); [#23457](https://github.com/sgl-project/sglang/issues/23457) Mooncake multi-node attach hostname (2026-06-15); [#19737](https://github.com/sgl-project/sglang/issues/19737) sgl-kernel 0.3.21 IMA (2026-05-03); [#20529](https://github.com/sgl-project/sglang/issues/20529) GLM5 pp2 indexer shape mismatch (2026-05-20); [#23659](https://github.com/sgl-project/sglang/issues/23659)/PR [#23391](https://github.com/sgl-project/sglang/pull/23391) SWA HiCache (2026-05-08); [#16797](https://github.com/sgl-project/sglang/issues/16797) Mooncake TTFT regression (2026-05-12); [#22572](https://github.com/sgl-project/sglang/issues/22572)/PR #23241 3FS hybrid Mamba/DSA (v0.5.11).

**Closed by the stale bot — treat as still-live risks, not fixes.** No maintainer fix was linked on either:

| Issue | Closed | Reality |
|---|---|---|
| [#21880](https://github.com/sgl-project/sglang/issues/21880) | 2026-06-18, inactivity | `file` backend slow in containers (`Pin budget: 0 tokens (ratio=0.000)`, prefetch dominates). Last substantive comment 2026-04-18 reproduced it. **Still don't use `file` in production** — though note the CP-aware LRU eviction added in v0.5.15 (#26670) touches this backend, so a fresh measurement is worth taking |
| [#22757](https://github.com/sgl-project/sglang/issues/22757) | 2026-06-14, inactivity | GLM5/DSA L3 segfault on H20. A candidate fix (PR #22120) was suggested 2026-04-14 but never confirmed on the thread |

For symptom → diagnosis → fix flow, see `references/troubleshooting.md`.

## What to read next — and when

| File | Read when... |
|---|---|
| `references/architecture.md` | Understanding L1/L2/L3 paths, the `HiRadixCache` / `HiMambaRadixCache` / `HiCacheController` classes, write/read/eviction policies, prefetch_tp_group. |
| `references/cli-flags.md` | Looking up a flag, default, valid values, or one of the auto-rewrite normalisation rules with the exact log line. |
| `references/storage-backends.md` | Picking or wiring up `mooncake` / `hf3fs` / `nixl` / `aibrix` / `eic` / `simm` / `dynamic` / `lmcache` / `file`. Per-backend deps, env vars, layout requirements, gotchas. |
| `references/recipes.md` | Concrete production commands for Mooncake-on-H100, 3FS DeepSeek-R1, NIXL Dynamo, file-backend dev, LMCache replacement, runtime attach/detach. |
| `references/hybrid-models.md` | The model-arch × storage-backend × version support matrix. Why `Llama4` / `GptOss` / `Gemma4` are footguns. The migration story from vLLM/LMCache. |
| `references/troubleshooting.md` | A specific error message, a wrong-looking number, or "TTFT regressed when I added hicache". Open bug list with symptoms + workarounds. |
| `references/migration-from-vllm-caching.md` | Operators with a vLLM/LMCache deploy hitting the hybrid-attention wall. What's equivalent, what's better, what's worse. |
| `references/sources.md` | Verifying or freshening external claims. Per-row `Last verified:` dates. |
| `scripts/inspect-sglang-image.sh <tag>` | Confirm which `mooncake-transfer-engine` / `nixl-cu*` / `aibrix-kvcache` / `lmcache` versions an `lmsysorg/sglang:<tag>` image bundles, without pulling. Reads the image config blob from Docker Hub. |

The upstream repo at https://github.com/sgl-project/sglang is the most authoritative reference — `docs/advanced_features/hicache*.md`, `python/sglang/srt/server_args.py:5635-5733` for flag definitions, and `docs/advanced_features/hicache_storage_runtime_attach_detach.md` for the admin HTTP API. When this skill disagrees with the repo, trust the repo (and update this skill).
