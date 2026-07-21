# Improvement Backlog — vllm-caching

> **Local-only file. NOT committed yet** — captures live-lab findings staged
> for SKILL.md / sources.md. Reapply when ready to publish.

## Open — pending publish

### Hybrid-attention live-lab matrix — re-run needed on v0.25.1 (carried 2026-05-28, re-scoped 2026-07-21)

Dim 5 / Dim 9. File-set: improvement-backlog.md (this section) → SKILL.md + sources.md.

**Partially closed by the 2026-07-21 freshen pass.** The *static* half of this item is done: a `SupportsHMA` connector matrix verified against vLLM tag **v0.25.1** source now lives in SKILL.md "Critical pitfalls", and the decision-tree/Hybrid-models sections were rewritten around it. What remains is **author-only live-lab work**: the v0.19.1-era runtime verdicts below (fail-to-start, TOCTOU `AssertionError`, symmetric-mode no-discovery) have not been re-run on a modern image. Static `SupportsHMA` declarations tell you what vLLM *intends*; only a run tells you what happens. Needs a 2× H100 session on `vllm/vllm-openai:v0.25.1` with a hybrid model (Qwen3.6-27B-FP8 or Gemma-4).

Specifically worth re-measuring: native offload on a hybrid model with HMA left **on** (the new recommendation — never yet validated in this lab); `TieringOffloadingSpec` with an `fs` secondary tier, including the `PYTHONHASHSEED` cross-instance sharing requirement; and whether LMCache **MP** 0.5.x really serves a hybrid model end-to-end (upstream claims it does; `lmcache-mp` skill now says so on the strength of upstream docs + a source-level `SupportsHMA` check, with no local run behind it).

#### v0.19.1-era connector matrix (historical — runtime verdicts superseded, kept for the perf numbers)

Verified 2026-04-25 against vLLM v0.19.1 + LMCache 0.4.4 on Verda 2× H100 SXM5 80GB serving `Qwen/Qwen3.6-27B-FP8`. **Do not quote the `SupportsHMA` column** — see SKILL.md for the v0.25.1-verified one; several rows (OffloadingConnector, native, SimpleCPUOffloadConnector) are known-flipped.

| Connector | `SupportsHMA`? (v0.19.1) | Outcome on hybrid model (v0.19.1) |
|---|---|---|
| **LMCacheConnectorV1** | ✗ | startup `ValueError: ... failed to convert KV cache specs to one unified type` (LMCache #3106 — still open) |
| **LMCacheMPConnector** | ✗ | same `ValueError` — **flipped**: lmcache 0.5.x declares `SupportsHMA` |
| **OffloadingConnector** | ✗ | required `--disable-hybrid-kv-cache-manager` — **flipped** in v0.21.0/v0.23.0 |
| **MooncakeConnector / MoRIIOConnector / FlexKVConnector / P2pNcclConnector** | ✗ | hybrid-disable issue — Mooncake **flipped**; `P2pNcclConnector` **removed** in v0.24.0 (#44854) |
| **SimpleCPUOffloadConnector** | ✓ | runtime `AssertionError` / #39702 TOCTOU — #39702 closed 2026-05-19 |
| **NixlConnector** (`kv_role=kv_both`) | ✓ | starts; no auto peer discovery in symmetric mode. Note `kv_both` entered a deprecation cycle in v0.23.0 (#43874) |
| **NixlConnector** 1P1D (+ toy_proxy) | ✓ | works cross-pod |
| **Native** `--kv-offloading-size` | implicit ✗ (v0.19.1, #36463) | fail-to-start on Qwen3.5 — **flipped**, #36463 closed as dup of the v0.21.0 HMA work |

**v0.19.1 baseline measurements (still valid as raw perf numbers):**
- `Qwen/Qwen3.6-27B-FP8` TP=1 H100 SXM5 80GB: GPU KV 174,048 tokens; 2.6× concurrency at 262K; CUDA graphs c=10 ISL=4k OSL=200 → ITL 17.9 ms p50 / 22.5 ms p99, 393 tok/s aggregate, 56 tok/s/user.
- TP=2: GPU KV 447,664 tokens; 6.7× concurrency at 262K; ITL 14.3 ms, 2.42 req/s. Eager mode collapses ITL ~20× (358 ms vs 17.9 ms) — never `--enforce-eager` on datacenter HW.

#### Carried operator-pushback notes (still useful, not yet in SKILL.md)

- **vLLM image-tag freshness rule**: always run `gh release list --repo vllm-project/vllm` AND `skopeo list-tags docker://vllm/vllm-openai` before picking a tag; don't default to a memorized known-good tag.
- **Docker `-v /root/cache:/root/.cache` default**: cold restart H100 + Qwen3.6-27B-FP8 TP=2 ≈ 5 min (DeepGEMM SM_90A FP8 JIT + torch.compile inductor + CUDA graph capture); with persistent whole-`/root/.cache` mount ≈ 50 s. Mount the WHOLE cache, not just `/root/.cache/huggingface`.

### Runtime bundling table never captured past v0.19.1 (new 2026-07-21)

Dim 9. File-set: SKILL.md "Two-step bundling verification" + `lmcache-mp/references/sources.md`.

The only image whose runtime imports have actually been verified is `vllm/vllm-openai:v0.19.1` (vllm 0.19.1 / lmcache 0.4.3 / nixl 0.9.0 / mooncake 0.3.10.post1), captured 2026-04-26 — five vLLM minors ago. Not applied because it needs a pull + container run, not an edit: run `lmcache-mp/scripts/verify-bundling.sh v0.25.1` and replace the table. Expect nixl 1.3.0 (the exact pin) and lmcache ≥ 0.5.x.

## Resolved this pass (2026-07-21)

Freshen pass, evidence via `gh release view` / `gh issue view` / `git show <tag>:<path>` on a local vLLM clone:

- **Version drift**: v0.21.0 → **v0.25.1** (2026-07-14) across SKILL.md version-gates, latest-stable line, known-good tags, and sources.md. Added gate rows for multi-tier offloading (v0.22.0), HMA-by-default (v0.23.0), and `P2pNcclConnector` removal (v0.24.0).
- **Deprecation / inverted guidance (the big one)**: the "always pass `--disable-hybrid-kv-cache-manager`" pitfall — previously billed as "the single most common silent blocker" — was retired. v0.23.0 #41847 made the flag tri-state (auto). Replaced with a per-connector `SupportsHMA` table verified against v0.25.1 source, and stripped the flag from every recipe in connectors.md, the diagnostics preflight, and the decision tree.
- **New feature in scope**: documented the native multi-tier framework (`TieringOffloadingSpec`, `fs`/`obj`/`p2p` secondary tiers) in the decision tree plus a full recipe section in connectors.md — `cpu_bytes_to_use` units, `offload_prompt_only`, on-disk layout, the `PYTHONHASHSEED` cross-instance requirement, `max_offload_tokens`. Source: `docs/features/kv_offloading_usage.md`.
- **Bug-state flips**: vLLM #40624 (Gemma4 + spec-decode) closed COMPLETED 2026-05-26 — old workaround removed. #40259 still open; LMCache #2942 open but stale-flagged (noted as "stale ≠ fixed"); #3106 open and active.
- **Pin drift**: `kv_connectors.txt` now pins `nixl == 1.3.0` exactly; added the v0.22.1 dual-CUDA-wheel `ImportError` note.
- **Cross-skill**: hybrid guidance now routes to LMCache MP (supported) vs in-process LMCacheConnectorV1 (blocked), consistent with the same-day `lmcache-mp` freshen.

## Resolved this pass (2026-05-28)

- **Fixed SKILL.md typo** `recheckchecking` → `rechecking` (Dim 8). grep confirms 0 occurrences remain.
- **Relocated CPU-tier right-sizing math** (`kv_bytes_per_token` formula + Qwen3-4B ~41 K-token cap) from SKILL.md validation section into `references/hardware-sizing.md` "CPU-tier right-sizing", leaving a one-line pointer in SKILL.md (Dim 6 / Dim 2).
- **Freshen — version drift**: bumped sources.md + SKILL.md version-gates table to v0.21.0 latest stable (2026-05-15); v0.20.0 GA 2026-04-27, v0.20.1/.2 noted; added a KV-Offload+HMA v0.21.0 row; updated `--calculate-kv-scales` and Known-good-tags lines.
- **Freshen — HMA recommendation inversion**: rewrote the SKILL.md Hybrid-models section — kv_offload+HMA shipped in v0.21.0 (#41445/#41228/#39571 + Qwen3.5/Mamba #35520); re-test hybrid on v0.21.0 instead of unconditionally disabling HMA. Preserved the still-open LMCache #3106 LMCacheConnectorV1-on-hybrid caveat as a distinct gate.
- **Freshen — closed bug rows**: flipped vLLM #36463 (closed DUPLICATE 05-18), vLLM #39702 (closed COMPLETED 05-19), LMCache #2502 (closed NOT_PLANNED 05-04) in SKILL.md Open-bugs table + sources.md; kept #40259 and #2942 open; added #3106 as a new open row. Softened diagnostics.md preflight item 4 + connectors.md guidance accordingly.
- **Freshen — LMCache version**: bumped generic "latest LMCache" references to v0.4.5 (connectors.md + sources.md), kept the explicit v0.4.4-cu13 wheel URL (no v0.4.5-cu13 build observed).
- **sources.md re-stamp**: all re-confirmed rows stamped Last verified 2026-05-28; added a 2026-05-28 freshen-pass summary section.

## Resolved earlier (2026-04-25)

- 5e628ba `docs(vllm-caching): cross-reference nvidia-nixl skill for transport-level details` — 4 cross-references from vllm-caching → nvidia-nixl skill. Scoped vllm-caching to vLLM-side wiring; transport-level details delegated to nvidia-nixl.
