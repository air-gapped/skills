# Improvement Backlog — sglang-hicache

Prior skill-improver runs and ceiling findings.

## Open

### Bundle `scripts/hicache-doctor.sh` boot-log auto-rewrite scanner

- **Dim:** 7 + 4
- **Where:** new `scripts/hicache-doctor.sh`; pointer in SKILL.md "Critical pitfalls #3" and `references/troubleshooting.md` "Validation / debug commands".
- **Why ceiling-bound:** `_handle_hicache` silently rewrites layout × IO × storage combinations and only emits a WARNING log. A short shell helper (`tail journalctl -u sglang | grep -E '(switching to|FlashAttention3 decode backend|Hierarchical cache enabled)'`) would surface all the auto-rewrites in one go. Operator-side, scriptable, but author-judgment-dependent on which log sources to scan (systemd / docker / kubectl). Skip until the operator workflow is more concrete.
- **Score impact if resolved:** Dim 7 9→10 + Dim 4 9→10 (~+2 total).

### Recipes for `simm` / `eic` / `dynamic` backends

- **Dim:** 5
- **Where:** `references/recipes.md` would need 3 new recipe sections.
- **Why ceiling-bound:** these backends are listed in `references/storage-backends.md` but have no worked recipe — niche but documented. Adding sample configs requires probing the AIBrix / Volcengine / Scitix doc sites for proprietary env-var sets that may not be public. Defer until an operator request surfaces.
- **Score impact if resolved:** Dim 5 9→10 (~+1 total).

## Resolved this pass (2026-04-25)

- **Writing Style (Dim 3) — 8→10.** 2 second-person slips removed (iter 1): `references/cli-flags.md:64` and `references/troubleshooting.md:41`. Zero "you/your" remaining. Blind agent confirmed Dim 3 = 10/10.
- **Simplicity (Dim 6) — 8→9.** Consolidated SKILL.md "Why this matters" hybrid-attention duplication (iter 2). Net –7 lines.
- **Resource Quality (Dim 7) — 8→9.** Added `scripts/inspect-sglang-image.sh` (iter 3). Reads `lmsysorg/sglang:<tag>` Docker image config without pulling layers; reports CUDA, mooncake-transfer-engine / nixl-cu* / aibrix-kvcache / lmcache versions. Smoke-tested against `v0.5.10` — confirms mooncake + nixl-cu13 bundled, no aibrix or lmcache.
- **Domain Accuracy (Dim 9) — freshen findings.** Iter 4: PR #23391 (SWA support) and PR #22878 (Channel-B writing_check) re-classified as **OPEN** in SKILL.md, sources.md, troubleshooting.md, hybrid-models.md (skill had claimed merged 2026-04-24). Issue #23659 framing tightened — "fix path" now correctly says "v0.5.11 once PR #23391 merges (still OPEN as of 2026-04-25)". Mooncake-transfer-engine v0.3.10.post2 (released 2026-04-22) noted in sources.md Versions section.

### Score trajectory

| iter | self | blind | delta | status | description |
|------|------|-------|-------|--------|-------------|
| 0    | 88   | 92    | —     | baseline | first version drafted with rubric loaded upfront |
| 1    | 89   |       | +1    | keep   | 2 second-person → imperative |
| 2    | 90   | 95    | +1    | keep   | consolidate "Why this matters" hybrid-attention duplication |
| 3    | 91   |       | +1    | keep   | add `scripts/inspect-sglang-image.sh` (Docker image inspector) |
| 4    | 92   | **97** | +1   | keep   | freshen findings — PR #23391/#22878 re-classified OPEN, Mooncake post2 noted |

**Stop conditions met:** self 92/100, final blind **97/100**, no dim < 9 on blind. Run converged. Self-blind gap is +5 (blind higher) — no flagged dims, scores aligned. Remaining ceiling items (`hicache-doctor.sh`, niche-backend recipes) carried forward — author-judgment-dependent.

Blind trajectory 92 → 95 → 97 across iters 0/2/4 confirms each iteration produced a real, defensible gain measured by an independent agent.
