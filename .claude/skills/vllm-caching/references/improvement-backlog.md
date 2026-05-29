# Improvement Backlog — vllm-caching

> **Local-only file. NOT committed yet** — captures live-lab findings staged
> for SKILL.md / sources.md. Reapply when ready to publish.

## Open — pending publish

### Hybrid-attention KV caching matrix — needs reconciliation against v0.21.0 (carried 2026-05-28)

Dim 5 / Dim 9. File-set: improvement-backlog.md (this section) → SKILL.md backlog section + Open-bugs rows + sources.md.

**Could not be applied in one iteration** because the verified `SupportsHMA` connector matrix below was authored against **v0.19.1**, and the 2026-05-28 freshen pass established that the vLLM-native offload+HMA path shipped in **v0.21.0** (#41445 full HMA enablement). Promoting this matrix into SKILL.md now would contradict the freshened Hybrid-models section unless the per-connector "✗ / fail-to-start" verdicts are first re-run on v0.21.0. The LMCacheConnectorV1 row stays accurate (LMCache #3106 still open, updated 2026-05-27) but the OffloadingConnector / native / SimpleCPUOffloadConnector rows are now likely stale. Re-test on a v0.21.0 image, update the matrix verdicts, THEN promote. This is author-only live-lab work (needs a 2× H100 run), not a one-edit relocation.

**Goal**: add Step 0 gate to backend decision tree + new "Backlog: hybrid-attention KV caching" section to SKILL.md + Verda evidence row in sources.md — all reconciled against v0.21.0.

#### Proposed `SKILL.md` — Decision-tree Step 0 gate (insert before existing "Ask these in order:")

```markdown
**Step 0 — gate on attention shape.** If the model is hybrid (Gemma-4, Qwen3.5/3.6, gpt-oss, Llama-4 — has `layer_types: [sliding_attention, full_attention, ...]` OR `mtp.*`/`gdn.*` weights in `config.json`'s `text_config`): on vLLM **< v0.21.0** no connector reliably extends HBM with a DRAM/NVMe tier; on **v0.21.0+** the native offload path integrates with HMA (re-test it) but **LMCacheConnectorV1 is still blocked** (LMCache #3106). For non-hybrid models, ask in order:
```

#### v0.19.1-era connector `SupportsHMA` matrix (NEEDS v0.21.0 RE-VERIFICATION before promotion)

Verified 2026-04-25 against vLLM v0.19.1 + LMCache 0.4.4 on Verda 2× H100 SXM5 80GB serving `Qwen/Qwen3.6-27B-FP8`:

| Connector | `SupportsHMA`? (v0.19.1) | Outcome on hybrid model (v0.19.1) | Re-check on v0.21.0? |
|---|---|---|---|
| **LMCacheConnectorV1** | ✗ | startup `ValueError: ... failed to convert KV cache specs to one unified type` (LMCache #3106) | #3106 still open 2026-05-27 — likely still ✗ |
| **LMCacheMPConnector** | ✗ | same `ValueError` | re-check |
| **OffloadingConnector** | ✗ | requires `--disable-hybrid-kv-cache-manager` | **likely fixed by v0.21.0 HMA enablement — re-test** |
| **MooncakeConnector / MoRIIOConnector / FlexKVConnector / P2pNcclConnector** | ✗ | hybrid-disable issue | re-check |
| **SimpleCPUOffloadConnector** | ✓ | starts; runtime `AssertionError`/#39702 TOCTOU | #39702 CLOSED 2026-05-19 — **re-test, likely fixed** |
| **NixlConnector** (`kv_role=kv_both`) | ✓ | starts; no auto peer discovery in symmetric mode | designed for proxy 1P1D |
| **NixlConnector** 1P1D (+ toy_proxy) | ✓ | works cross-pod | proven on non-hybrid Qwen3-4B |
| **Native** `--kv-offloading-size` | implicit ✗ (v0.19.1, #36463) | fail-to-start on Qwen3.5 | #36463 CLOSED 2026-05-18 as dup of v0.21.0 HMA — **re-test, likely fixed** |

**v0.19.1 baseline measurements (still valid as raw perf numbers):**
- `Qwen/Qwen3.6-27B-FP8` TP=1 H100 SXM5 80GB: GPU KV 174,048 tokens; 2.6× concurrency at 262K; CUDA graphs c=10 ISL=4k OSL=200 → ITL 17.9 ms p50 / 22.5 ms p99, 393 tok/s aggregate, 56 tok/s/user.
- TP=2: GPU KV 447,664 tokens; 6.7× concurrency at 262K; ITL 14.3 ms, 2.42 req/s. Eager mode collapses ITL ~20× (358 ms vs 17.9 ms) — never `--enforce-eager` on datacenter HW.

#### Carried operator-pushback notes (still useful, not yet in SKILL.md)

- **vLLM image-tag freshness rule**: always run `gh release list --repo vllm-project/vllm` AND `skopeo list-tags docker://vllm/vllm-openai` before picking a tag; don't default to a memorized known-good tag.
- **Docker `-v /root/cache:/root/.cache` default**: cold restart H100 + Qwen3.6-27B-FP8 TP=2 ≈ 5 min (DeepGEMM SM_90A FP8 JIT + torch.compile inductor + CUDA graph capture); with persistent whole-`/root/.cache` mount ≈ 50 s. Mount the WHOLE cache, not just `/root/.cache/huggingface`.

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
