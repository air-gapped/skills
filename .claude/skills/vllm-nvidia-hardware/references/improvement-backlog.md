# Improvement backlog — vllm-nvidia-hardware

Work-not-done log from skill-improver passes. "Open" = attempted as a hypothesis
but could not be applied in one atomic, score-improving iteration. Not a wishlist.

## Open

- **Convert sources.md `[LV: <date>]` markers to a machine-readable `Last verified:` table** (Dim 9; `references/sources.md`, all rows). The rubric staleness regex anchors on a `YYYY-MM-DD` date in a pipe-table row (`^\|.*\| (\d{4}-\d{2}-\d{2}) \|`), not inline `[LV:]` bullet markers. Converting the entire bulleted source list to a dated table is a multi-row restructure that rewrites prose across the whole file — violates the one-atomic-change / "relocation must not rewrite prose" constraint, and the staleness cap is not currently firing (freshen pass < 90 days), so it scores +0 while adding restructure risk. Defer to a dedicated structural pass.
- **Re-verify the two cookie-gated / binary-only NVIDIA + Dell datasheet rows** (Dim 9; `references/sources.md` — Blackwell Ultra datasheet and Dell PowerEdge XE spec sheet, both `[LV: 2026-04-24, unverifiable]`). WebFetch could not extract text (cookie gate / PDF binary) in the prior pass and network is unavailable here. Needs a browser session to re-confirm per-SKU sizing numbers before any purchase-grade call.

## Resolved — 2026-07-21 (freshen)

- **Closed the carried Rubin backlog item.** It had been Open since 2026-05-28
  as unverifiable ("network egress is blocked in the apply environment").
  Probed this pass, and the useful result is a *distinction* rather than a
  spec change: **"in production" is a fab statement, not a delivery
  statement.** Evidence now in `rubin-roadmap.md` as a dated table — CoreWeave
  validated a Dell-supplied Vera Rubin NVL72 on 2026-05-31 (L11 diagnostics +
  147-hour suite); Jensen Huang said "already in production" at a Tokyo event
  on 2026-07-15 while denying delay reports; NVIDIA has still given **no
  customer-delivery date**. The buy-or-wait guidance now names the signal to
  wait for (an OEM quoting firm order dates) instead of restating the
  H2-2026 window. Per-GPU specs (288 GB HBM4, ~20 TB/s) were **not** changed —
  nothing in this pass contradicted them, and they were not independently
  re-probed.
- **Silent-corruption bug found in the current release line — the pass's main
  operator value.** vLLM PR #48330 (merged 2026-07-12, ships in v0.25.1, fixes
  #48324): fused FlashInfer allreduce + RMSNorm + static-quant patterns matched
  mixed-dtype graphs (BF16 residual vs FP32 Gemma/Qwen-style RMSNorm weight,
  from `weight.float() + 1.0`), **corrupting the hidden state and emitting
  repeated `!!!!!` tokens** on NVFP4 models. Allreduce fusion has been default
  since v0.19.0, so a Blackwell multi-GPU NVFP4 serve on v0.25.0 is exposed.
  No crash, no metric movement — text is simply wrong. Added to
  `vllm-platform-matrix.md` §6 with the reproducer (`nvidia/Qwen3.6-27B-NVFP4`)
  and a `≥ v0.25.1` pin in `SKILL.md`.
- **Rebaselined the vLLM release line v0.21.0 → v0.25.1** across
  `sources.md` and `vllm-platform-matrix.md` §6, keeping only the rows that
  change an operator decision: Triton MoE now default on Hopper (#44220, a
  silent H100/H200 path change), `CUDA_VISIBLE_DEVICES` no longer set
  internally in favour of `device_ids` (#45026), PagedAttention removed
  (#47361), NUMA auto-binding on DGX B300 (#43270), GB300 all-reduce tuned for
  world_size=16 (#46392), SM90 CUTLASS FP8 odd-M `swap_ab` (+180–290% kernel,
  #44572).
- **Retired the FlashInfer #2939 pin advice as live guidance.** vLLM has shipped
  0.6.11.post2 → 0.6.12 → 0.6.13 across v0.22–v0.25, all far past the
  2026-04-07 fix. Kept the workaround text but scoped it to deployments that
  pin FlashInfer independently of vLLM — otherwise it reads as a live hazard.
- **New correction: `sm_110` is Thor, not Rubin.** vLLM's own build comments
  group it with Blackwell. Recorded alongside the CUDA 13 + Triton
  `ptxas fatal: Value 'sm_110a' is not defined` gotcha, which surfaces as
  `EngineDeadError` and so reads as an engine bug rather than a toolchain
  mismatch (fix: set `TRITON_PTXAS_PATH`).
- **Established a negative worth carrying: vLLM has no Rubin support** at
  v0.25.1 — zero issue-tracker hits, no Rubin SM target in the build scripts.
  Hardware availability and engine support are on different clocks.

**Honest gaps this pass:** the wccftech article naming the eight first-cohort
clouds returns **HTTP 403 to WebFetch** — that list comes from search-result
summaries and is flagged `unverifiable` in `sources.md`, not quotable as NVIDIA
guidance. The two remaining Open items (cookie-gated Blackwell Ultra datasheet,
binary-only Dell XE spec sheet) still need a browser session and were not
attempted.

## Resolved this pass (2026-05-28)

- **Removed dangling internal-artifact reference** "compiled from MEMORY_WALL_DEEP.md" from `SKILL.md` source-and-refresh section (Dim 6: 9→10).
- **Refreshed vLLM release rows** in `references/sources.md`: relabeled v0.19.1 (no longer "latest stable"), marked v0.20.0 GA 2026-04-27, added v0.20.1 / v0.20.2 / v0.21.0 (current latest, `isLatest=true`), and dropped the stale "pin v0.19.1 until v0.20.0 leaves pre-release" guidance — the one stale load-bearing version claim recon surfaced via live `gh release list` (Dim 9: 8→9). All updated rows stamped `[LV: 2026-05-28]`.
- **Clarified FlashInfer fix is a revert** in `references/vllm-platform-matrix.md` (§1 table + §5 prose) and `references/sources.md`: PR #2956 reverts the Blackwell-Ultra optimization that caused the SM103 deadlock (recon live-gh verified: issue #2939 closed 2026-04-07; PR title "[Fmha] revert blackwell ultra optimization that causes deadlocks"). Re-stamped the #2939 row `[LV: 2026-05-28]`.
