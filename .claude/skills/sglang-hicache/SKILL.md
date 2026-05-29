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

**Why this skill exists alongside `vllm-caching`:** as of 2026-05, vLLM tier-extension caching is broken for the entire 2026 hybrid-attention model lineup (Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4) — most KV connectors don't subclass `SupportsHMA`. SGLang HiCache ships full hybrid support as of v0.5.11: SSM/Mamba and DSA across Mooncake + 3FS, plus SWA HiCache (day-0 Gemma 4). For the arch × backend × release matrix and the "should we migrate?" decision tree, see `references/hybrid-models.md`.

> **NIXL deep-dive** — the NIXL transfer library (UCX / GDS / Mooncake / S3-OBJ plugins, agent API, telemetry) lives in the dedicated **`nvidia-nixl`** skill. This skill covers SGLang-side wiring of `--hicache-storage-backend nixl` only.

## Versions

- **Stable**: v0.5.12.post1 (2026-05-26, latest), v0.5.12 (2026-05-16), v0.5.11 (2026-05-05). Earlier: v0.5.10.post1 (2026-04-09).
- **v0.5.11 shipped the hybrid milestones** the v0.5.10-era notes called "landing": SWA HiCache (PR [#23391](https://github.com/sgl-project/sglang/pull/23391) merged 2026-05-06, day-0 Gemma 4), 3FS Mamba/DSA (PR #23241), hybrid CP.
- **Image**: `lmsysorg/sglang:v0.5.12.post1` (pip-installs `mooncake-transfer-engine` 0.3.10.post1; install `nixl-cu13`, `aibrix-kvcache`, `simm` etc. as needed for that backend).
- **Source of truth for flags**: `python -m sglang.launch_server --help`. If this skill disagrees with `--help` on a flag spelling, trust `--help` and freshen the skill.

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

4. **Hybrid-attention model support is arch-specific and version-gated** — the killer footgun. As of v0.5.11+:
   - **Mamba / SSM** (Qwen3-Next, Qwen3.5, MiniMax-M2 family): ✓ on Mooncake L3 (#21259, v0.5.10) and 3FS (#23241, v0.5.11).
   - **DSA** (DeepSeek-V3.2): ✓ via `HiMambaRadixCache` route on Mooncake (v0.5.10) and 3FS (v0.5.11).
   - **SWA** (Gemma 3-4, Mistral-class): ✓ as of v0.5.11 — PR [#23391](https://github.com/sgl-project/sglang/pull/23391) merged 2026-05-06 (day-0 Gemma 4), closing #23659. Pre-v0.5.11 raises `ValueError: HiRadixCache only supports MHA, MLA, and NSA (DSA) models` — upgrade to ≥ v0.5.11.
   - **Hybrid SWA without arch-specific guard** — `Llama4ForConditionalGeneration`, `GptOssForCausalLM`, `Gemma4ForCausalLM` have NO server-side guard like MiMoV2/Step3p5/Gemma3, so hicache treats SWA layers as full attention (memory bloat, possible quality drift). Either skip hicache for those models or pass `--disable-hybrid-swa-memory` and verify quality before going live.
   
   For the full arch × backend matrix and migration story from vLLM/LMCache, see `references/hybrid-models.md`.

5. **`write_back` policy crashes under load.** Issue [#19212](https://github.com/sgl-project/sglang/issues/19212) (open since 2026-02): `AssertionError: parent does not have child key` in `evict_host()` because the radix tree is mutated during heap iteration. **Workaround**: stay on `write_through` (the default).

6. **PP + HiCache is broken across multiple stacks.** Issue [#22607](https://github.com/sgl-project/sglang/issues/22607) (2026-04-12, high-priority meta): async L3 prefetch + per-rank scheduler diverge under `--pp-size > 1`. Wall-clock LRU produces different victim selection on each rank → host-tree shape mismatch → crash. Still **OPEN** as of 2026-05-29 — the meta (#22607) and the writing-ack-sync PR (#22878) did NOT make the v0.5.11/v0.5.12 cut. Recommend `pp_size = 1` with hicache until both close.

7. **Mooncake 0.5.6+ TTFT 10× regression vs 0.5.5** (historically: TTFT ~0.5 s → 5+ s, hit rate ~90% → ~30%). Issue [#16797](https://github.com/sgl-project/sglang/issues/16797) was **closed 2026-05-12** — fixed in the v0.5.11/v0.5.12 line. On ≥ v0.5.11 the pin is no longer load-bearing; on older builds, still pin `mooncake-transfer-engine 0.3.10.post1` and, if TTFT regresses, try `--hicache-storage-prefetch-policy best_effort` to bypass and isolate.

8. **PyPI sgl-kernel 0.3.21 + FA3 + MoE + SXM = IMA.** Issue [#19737](https://github.com/sgl-project/sglang/issues/19737): `CUDA_EXCEPTION_4: Warp Illegal Instruction` within ~10 min. Workaround: install `sgl-kernel` from the GitHub Release artifact (built with `-DCUTLASS_ENABLE_GDC_FOR_SM90`), not PyPI.

9. **Runtime attach/detach blocks until idle.** `PUT/DELETE /hicache/storage-backend` admin endpoints reject with HTTP 400 if any request is running, queued, in chunked-prefill, in PD bootstrap, or DLLM staging (`is_fully_idle()` check). With `dp_size > 1`, success is AND-aggregated across DP ranks — partial-success has no automatic rollback. Drain traffic before switching backends. Set `--admin-api-key` for production.

10. **`--page-size` is global, defaults to 1 on CUDA, recommended 64 for HiCache + L3.** Bigger pages reduce metadata / I/O overhead but lower hit rate when prefixes don't align. DeepSeek DSA forces `page_size = 64`; SSM models with `no_buffer` strategy + radix cache force `page_size = 1` and break with `trtllm_mha`. SSM with `extra_buffer` requires `mamba_track_interval % page_size == 0`.

## Open bugs to know before recommending

Active issues at the time of last verification (2026-05-29). Recheck via `gh issue view <N> --repo sgl-project/sglang` before quoting.

The two release-blockers (#22607 PP+HiCache, #19212 `write_back`) are detailed with root-cause in "Critical pitfalls" #6 and #5 above — not repeated here. The rest:

| Issue | Severity | Affects | Workaround |
|---|---|---|---|
| [#23429](https://github.com/sgl-project/sglang/issues/23429) | high | Mamba + write_back crash in `mamba_pool_host.free` during `_evict_host_leaf` | Stay on write_through; no other workaround |
| [#23457](https://github.com/sgl-project/sglang/issues/23457) | high | Mooncake multi-node runtime-attach uses wrong hostname | Inject `MOONCAKE_LOCAL_HOSTNAME` per node before launch |
| [#21880](https://github.com/sgl-project/sglang/issues/21880) | high | `file` backend is slow (prefetch dominates) in containers | Don't use `file` in production |
| [#19737](https://github.com/sgl-project/sglang/issues/19737) | high | PyPI sgl-kernel 0.3.21 + FA3 + MoE + SXM IMA | Install sgl-kernel from GitHub Release artifact, not PyPI |
| [#22105](https://github.com/sgl-project/sglang/issues/22105) | medium | Input-length validation rejects requests that fit in L1+L2 | `--allow-auto-truncate` (silent truncation, not a real fix) |

Recently resolved (no longer require workarounds on ≥ v0.5.11): [#23659](https://github.com/sgl-project/sglang/issues/23659)/PR [#23391](https://github.com/sgl-project/sglang/pull/23391) SWA HiCache (closed 2026-05-08, merged 2026-05-06); [#16797](https://github.com/sgl-project/sglang/issues/16797) Mooncake TTFT regression (closed 2026-05-12); [#22572](https://github.com/sgl-project/sglang/issues/22572)/PR #23241 3FS hybrid Mamba/DSA (shipped v0.5.11).

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
