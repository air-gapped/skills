# Improvement Backlog — vllm-caching

> **Local-only file. NOT committed yet** — captures live-lab findings staged
> for SKILL.md / sources.md. Reapply when ready to publish.

## Resolved — 2026-09-15 ("known-good tag" meant two different things)

- **The known-good tag list is a *bundling* claim and reads as a safety one.**
  `v0.14.0`+, `v0.19.0` and `v0.19.0-cu130` are listed because they ship
  `INSTALL_KV_CONNECTORS=true`. All three are **below the security floor**, so an
  operator picking the oldest listed tag gets working connectors and a vLLM with
  a critical authentication bypass. The two questions are now separated in place.
- **Floors named with their derivation**: **v0.22.0** for CVE-2026-48746 (critical
  `--api-key` / `VLLM_API_KEY` bypass via URL characters in the `Host:` header) —
  derived from the fix PR, because the advisory records *no* patched version and
  an unbounded range; and **v0.14.1** for CVE-2026-22778, the pre-auth video RCE,
  which applies **only** to deployments serving a video model. Detail lives in
  `vllm-configuration` § Server auth rather than being duplicated here.
- **The `v0.19.0-cu130` recipe tag in `connectors.md` is deliberately NOT bumped.**
  The recipe's numbers were measured on that image; silently changing the tag
  would invalidate the measurement it documents. It now carries a note saying the
  tag is below the floor, that it is kept for reproducing those numbers, and that
  anything else should run ≥ v0.22.0 and re-run the two-step bundling check —
  bundling is verified per tag, so a security bump is not free.

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

## Resolved — 2026-09-15 (the runtime-import half, finally run)

Ran `lmcache-mp/scripts/verify-bundling.sh` against `vllm/vllm-openai:v0.29.0`. The
item had been carried since July as "needs a pull + container run"; that is effort,
not a blocker, and the run takes minutes.

- **Measured:** vllm 0.29.0, lmcache **0.5.4**, nixl **1.3.2**, mooncake
  **0.3.13.post1**. All import; MP adapter classes and `ParallelStrategy` present;
  all four KV-offload connector classes load through the factory's own thunk. Exit 0.
- **nixl is 1.3.2, not the 1.3.1 this entry predicted.** The prediction came from the
  v0.26.0 pin commit; the image moved past it.
- **The probe under-reported mooncake, and would have again.** Its distribution is
  `mooncake-transfer-engine-cuda13` on this image, so querying the unsuffixed name
  printed NOT INSTALLED for a package that imports fine. The script now tries the
  CUDA-suffixed names before concluding absence — otherwise this measurement would
  have written a false negative into the table it exists to fill.
- **Sixteen connectors are registered at v0.29.0**, against the four this skill
  checks. The four are the KV-offload set and remain the right ones to gate on; the
  factory registry is the only place the other twelve are visible.
- The `ParallelStrategy` import hazard is now historical for current images — 0.5.4
  has the symbol. It still applies to anyone pinning a 0.4.3-era image.

## Resolved this pass (2026-08-11)

Freshen pass over v0.25.1 → v0.27.0 (two minors). Evidence via `git show <tag>:<path>` on the local vLLM clone, `gh api` for issue/PR state, and the skill's own `inspect-vllm-image.sh`.

- **Version drift**: v0.25.1 → **v0.27.0** (2026-08-10) across version gates, latest-stable line, known-good tags, `SupportsHMA` header + recheck probe, and `--calculate-kv-scales`. `nixl` pin `== 1.3.0` → `== 1.3.1` (#47559). LMCache v0.5.1 → v0.5.3.
- **Broken claim**: `self_describing_kv_events` is no longer rejected by `TieringOffloadingSpec` (#48679, v0.26.0) — `store_threshold` still is. connectors.md had them bundled as one rule.
- **Config drift**: `p2p` secondary tier's `port` default `7777` is gone → `VLLM_P2P_SIDE_CHANNEL_PORT` (5710) / `VLLM_P2P_SIDE_CHANNEL_HOST` (localhost) (#47636), bound port offset by DP index, `PYTHONHASHSEED` now a startup hard-fail.
- **Bug-state flips**: vLLM #40259 closed COMPLETED by the reporter (fix #41549 in v0.21.0; real trigger was DCP+offload, not EAGLE3) — avoidance dropped. LMCache #2942 closed by the **stale bot** with fix PR #3006 unmerged — warning kept and re-worded to say so explicitly.
- **New feature in scope**: `vllm:kv_offload_*` Prometheus family (7 metrics, 5 new in v0.26.0) documented in diagnostics.md.
- **Re-verified unchanged** (no edit beyond the stamp): `SupportsHMA` connector set, connector-directory file list, secondary-tier registry, `eviction_policy` key, `--calculate-kv-scales` deprecation.

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
