# Improvement backlog — vllm-speculative-decoding

Work-not-done log from skill-improver passes. `## Open` = issues attempted as a
hypothesis but not applicable in one atomic iteration. `## Resolved this pass` =
changes a metric actually registered.

## Open

- **Deduplicate the BS>=32 / domain-mismatch caveat** — Dim 6 (Simplicity).
  Files: SKILL.md "wins/loses" L17-32 (canonical home), references/eagle3.md
  "When EAGLE-3 fails to pay off" L137-149, references/dflash.md "When DFlash is
  the wrong choice" L77-84, references/troubleshooting.md. The general caveat
  recurs across four files. The per-method "when X fails" restatements in
  eagle3.md and dflash.md carry method-specific falloff data (DFlash falls off
  faster than vanilla EAGLE-3; EAGLE-3 chat-tuned AL ~3→~2), so they are not pure
  duplicates and cannot be deleted wholesale — the dedup should collapse the
  *generic* statement to SKILL.md and leave only the method-specific delta in the
  references, which is a multi-file restructure (>1 atomic edit). Could not be
  applied this pass: the tool channel returned empty for every Read of
  troubleshooting.md, so its exact text could not be confirmed and a blind Edit
  would risk corruption.

## Resolved this pass

- Fixed aux_hidden_states allowlist line-anchor drift 818-833 → 895-909 in
  references/eagle3.md L27 and references/dflash.md L41 (Dim 8 — matches
  SKILL.md/methods.md; sources.md row 15 had already claimed this fixed).
- Added EAGLE 3.1 note (vLLM blog 2026-05-26) to references/eagle3.md after the
  P-EAGLE section (Dim 9 / Dim 5 — captures newest in-scope EAGLE feature).
- Re-stamped sources.md "vLLM releases" row from stale "v0.20.0 one day ago" to
  v0.21.0 stable / v0.22.0rc as of 2026-05-29; added an EAGLE 3.1 blog row; both
  stamped Last verified 2026-05-29 (Dim 9).
- Trimmed two near-duplicate implicit triggers ("faster inference", "higher
  tok/s") from SKILL.md when_to_use — subsumed by retained "speed up decode" /
  "can we get more tokens/sec"; widens listing-cap headroom (Dim 1 / Dim 6).
