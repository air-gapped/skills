# Improvement backlog — vllm-nvidia-hardware

Work-not-done log from skill-improver passes. "Open" = attempted as a hypothesis
but could not be applied in one atomic, score-improving iteration. Not a wishlist.

## Open

- **Convert sources.md `[LV: <date>]` markers to a machine-readable `Last verified:` table** (Dim 9; `references/sources.md`, all rows). The rubric staleness regex anchors on a `YYYY-MM-DD` date in a pipe-table row (`^\|.*\| (\d{4}-\d{2}-\d{2}) \|`), not inline `[LV:]` bullet markers. Converting the entire bulleted source list to a dated table is a multi-row restructure that rewrites prose across the whole file — violates the one-atomic-change / "relocation must not rewrite prose" constraint, and the staleness cap is not currently firing (freshen pass < 90 days), so it scores +0 while adding restructure risk. Defer to a dedicated structural pass.
- **Live re-probe of the Rubin R100 roadmap claim** (Dim 9; `references/rubin-roadmap.md` L19, `SKILL.md` L44/L81 — "H2 2026 / ~288 GB HBM4 / ~20 TB/s"). Recon marked this the single most volatile forward-looking claim and flagged it **unverifiable** this session (no live NVIDIA-roadmap WebSearch/WebFetch was run; network egress is blocked in the apply environment). Cannot apply a spec change without standing behind fresh evidence. Re-run in a freshen pass with network access to the NVIDIA Vera Rubin dev blog + CES 2026 coverage.
- **Re-verify the two cookie-gated / binary-only NVIDIA + Dell datasheet rows** (Dim 9; `references/sources.md` — Blackwell Ultra datasheet and Dell PowerEdge XE spec sheet, both `[LV: 2026-04-24, unverifiable]`). WebFetch could not extract text (cookie gate / PDF binary) in the prior pass and network is unavailable here. Needs a browser session to re-confirm per-SKU sizing numbers before any purchase-grade call.

## Resolved this pass (2026-05-28)

- **Removed dangling internal-artifact reference** "compiled from MEMORY_WALL_DEEP.md" from `SKILL.md` source-and-refresh section (Dim 6: 9→10).
- **Refreshed vLLM release rows** in `references/sources.md`: relabeled v0.19.1 (no longer "latest stable"), marked v0.20.0 GA 2026-04-27, added v0.20.1 / v0.20.2 / v0.21.0 (current latest, `isLatest=true`), and dropped the stale "pin v0.19.1 until v0.20.0 leaves pre-release" guidance — the one stale load-bearing version claim recon surfaced via live `gh release list` (Dim 9: 8→9). All updated rows stamped `[LV: 2026-05-28]`.
- **Clarified FlashInfer fix is a revert** in `references/vllm-platform-matrix.md` (§1 table + §5 prose) and `references/sources.md`: PR #2956 reverts the Blackwell-Ultra optimization that caused the SM103 deadlock (recon live-gh verified: issue #2939 closed 2026-04-07; PR title "[Fmha] revert blackwell ultra optimization that causes deadlocks"). Re-stamped the #2939 row `[LV: 2026-05-28]`.
