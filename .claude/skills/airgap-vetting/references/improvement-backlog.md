# airgap-vetting — improvement backlog

Minimal memory across improvement passes: open work + decisions that must
not be re-proposed or re-researched. Design rationale lives in
`references/maintenance.md`, not here.

## Open

- **`scripts/static-sweep.sh`** (Dim 7) — bundle the static grep batteries
  (telemetry hostnames/SDKs, kill-switch substrings, CA vars, fallback
  hosts) into one script emitting a structured hit list. Attempted
  2026-07-15, superseded by the redesign before completion.
- **Verify the redesign left no generic claim ungrounded** (Dim 5/10) —
  and that known-products.md rows carry the evidence the pattern files
  used to hold inline. (raised 2026-07-15)

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
- **Freshen 2026-07-14**: cosign v3.1.1 flags, grype v6 endpoint, gh
  v2.91.0 telemetry all verified current; zero mutations needed.

History: initial improve+freshen+trigger pass 2026-07-14 (blind 79→86);
product-agnostic redesign + catalog deletion 2026-07-15.
