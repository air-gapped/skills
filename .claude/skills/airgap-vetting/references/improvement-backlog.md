# airgap-vetting — improvement backlog

Minimal memory across improvement passes: open work + decisions that must
not be re-proposed or re-researched. Design rationale lives in
`references/maintenance.md`, not here.

## Open

- **Build an eval set and measure `delta_pass_rate`** (Dim 10) — Dim 10 is
  capped at 8 (Negative-Transfer Gate, unmeasured) until the skill has
  `evals/evals.json` and a with/without-skill `benchmark.json` from the
  skill-creator plugin's eval loop. Multi-session work: author eval cases
  (e.g. the three smoke tests in `maintenance.md` §Testing as seeds), run
  the benchmark, record the delta. Not applicable in one iteration.
  (raised 2026-08-18)
- **`scripts/static-sweep.sh`** (Dim 7) — bundle the static grep batteries
  into one script emitting a structured hit list. Attempted 2026-07-15,
  superseded by the redesign. Re-screened 2026-08-18 and NOT built: it
  would duplicate every grep from the pattern files, recreating the drift
  surface the product-agnostic redesign deliberately removed. Needs an
  operator yes/no (either build it as the single source of truth with the
  pattern files pointing at it, or close this item). (carried 2026-08-18)

## Settled — do not re-propose

- **Pattern files stay product-agnostic** (author, 2026-07-15). No
  candidate-product examples in Q1–Q7 references; known-products.md is the
  only product log. Full redesign applied 2026-07-15.
- **No per-tool opt-out catalog** (author, 2026-07-15). Deleted
  `opt-out-catalog.env`; Q2 uses substring detection + SDK-layer grep
  (telemetry.md §Opt-out). Do not re-vendor a name list.
- **Phase-4 JSON schema stays inline in SKILL.md** (author judgment,
  2026-07-14) — it is the output contract; relocate only if SKILL.md grows
  materially past 350 lines.
- **Commits require explicit author approval** — improvement loops
  snapshot to scratchpad for revert, never commit on their own.
- **Sibling→sibling reference pointers stay** (2026-08-18 discard) —
  de-pathing cross-refs like ca-trust.md → `dynamic-harness.md step 4` was
  tried and reverted: the pointers are valid one-hop refs, SKILL.md loads
  every reference directly, and removing the path only makes the pointer
  vaguer for an agent that greps straight into a pattern file.

## Resolved this pass — 2026-08-18 (improve + freshen)

- Freshen (12 probes, 4 mutations, 6 sources.md rows restamped):
  electron#41590 fixed in Electron 30 (PR #41689) — ca-trust.md claim
  version-gated; kyverno#10115 fixed in Kyverno 1.12.0 (PR #9957) —
  verification-time.md claim version-gated; `SIGSTORE_*` env escape hatches
  confirmed alive in cosign v3 (`pkg/cosign/env/env.go`) — the file's own
  "freshen target" note replaced with the verified claim; cosign flag-break
  claim re-verified at v3.1.3; DCT shutdown 2026-12-08 and donottrack.sh
  re-confirmed. undici#2200 still open; aiohttp#3180 stale-closed, claim
  retained.
- **Verify-redesign-grounding item (raised 2026-07-15): resolved.** Two
  blind scorers (2026-07 pass and this pass's baseline, 84/100) plus this
  pass's freshen probes surfaced no ungrounded generic claim; known-products
  rows carry their evidence inline.
- Improve loop (5 keeps, 1 clean probe, 1 discard): SKILL.md 317→301 lines
  — Phase-1 question paragraphs compressed to remove reference-lead
  duplication, Phase-2 step enumeration collapsed to the ladder summary,
  redundant cross-cutting sub-check paragraph deleted, invocation line and
  Arguments block tightened, description trimmed to 75 chars of truncation
  headroom (no trigger phrase touched). Terminology probe (egress-deny /
  air-gap variants) came back clean, no mutation. Self-score 85→87.

History: initial improve+freshen+trigger pass 2026-07-14 (blind 79→86);
product-agnostic redesign + catalog deletion 2026-07-15; freshen 2026-07-14
(cosign v3.1.1, grype v6, gh v2.91.0 verified, zero mutations);
improve+freshen 2026-08-18 (blind 84→86, self 85→87).
