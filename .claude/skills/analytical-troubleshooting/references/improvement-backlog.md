# Improvement Backlog

Carries findings across skill-improver runs. See skill-improver's
`references/backlog-format.md` for admission rules.

## Open

- **Re-run the eval benchmark at n≥3 per cell** (Dim 10; `evals/benchmark.json`).
  Final blind scorer 2026-07-29 flagged the +0.15 delta_pass_rate as thin: 1 run
  per cell, 1 of 3 evals non-discriminating (day-one-twin passes 6/6 both arms),
  baseline already at 84.7%. Not applicable in one iteration — requires 18+
  subagent runs via skill-creator plus hardening the weak eval (messier evidence,
  assertions on spec-table/EXTENT-question/ground-rules behaviors per the
  iteration-1 analyst notes in the workspace benchmark). Until then treat the
  delta as directional.
- **Remaining restatements** (Dim 6; hard rule 5 vs `SKILL.md` Stage 4 loop
  rule; "Proportionality, restated" vs Stage 1). Deliberate-redundancy judgment
  call: hard rules act as standing summary (SKILL.md loads alone; references
  load on demand), so cross-file "duplication" flagged by the final blind
  (rules 4/5 vs reference content) is load-order-driven and should stay. The
  two *intra-file* repeats are genuine candidates but each carries a unique
  clause (the tighten-not-relax loop rule at the point of failure; the
  severity≠ceremony maxim) — removing them needs author judgment on teaching
  value vs. lines. ~10 lines at stake.

### Discard rationales (anti-re-proposal guards)

- **2026-07-29, iter 10, discarded:** "Universal discriminating probes" command
  menu in `test-toolkit.md` (Dim 4). Δ0, +9 lines, and 3 of 5 example probes
  (`ping -M do`, `dmidecode -t memory`, crash-boot journal) mirror the eval
  scenarios — shipping the eval answer key inside the skill corrupts future
  benchmark iterations. Do not re-propose command menus sourced from eval
  content; a future Dim 4 lift must use probes independent of `evals/`.

## Resolved this pass — 2026-07-29 (trigger mode)

- **Cheap-repro exclusion added and measured** (was Open). Fable-5 N=7 probe
  confirmed the predicted over-fire: "my unit test fails after my last commit,
  help me debug this python function" fired 5/7 against the pre-mutation
  frontmatter (the Haiku N=3 screen had masked it — Haiku's bias is false
  unders, so negatives must be confirmed on the real model). NOT-clause for
  cheaply-reproducible code bugs added to `when_to_use`: negative → 0/7,
  software-flavored positives held 7/7. Combined frontmatter 1266/1536 chars.
- **`understanding-human-error` collision check resolved: no collision.** The
  postmortem query ("outage is resolved — write a blameless postmortem") reads
  0/7 on Fable 5 at N=7; the existing NOT-clause routes correctly.
- Eval set persisted: `references/trigger-evals.json` (13 queries, must stay a
  bare JSON array — probe-trigger.py iterates `item["query"]`); run record in
  `trigger-evals.meta.json`.

## Resolved — 2026-07-29 (improve + freshen pass)

- Split `description`/`when_to_use` — cleared the 1024-char spec hard-fail
  (Dim 9 cap 3→uncapped). Self 72→75.
- Created `references/sources.md`, 14 rows stamped `Last verified: 2026-07-29`
  (freshen deliverable; all sources fetched same day by the authoring research
  run) — cleared the absent-sources.md Dim 9 cap at 6.
- Converted second-person body prose to imperative (Dim 3, 18→1 occurrence;
  the survivor is a quoted maxim).
- Shipped `evals/benchmark.json` (delta_pass_rate +0.15) — cleared the Dim 10
  unmeasured cap; metadata corrected post-loop (skill_path/models were
  templated; token means had been read from grader-side chars).
- TOC on `specification.md` (>100-line rule).
- "Agent-executed tests" section in `test-toolkit.md` — mode parity with the
  human-executed section (final blind Dim 5 dock closed).
- Distribution-safe pointer in `evidence.md` (was a repo-external path).
- Candidate/hypothesis/H1..Hn equivalence declared once (`SKILL.md` Stage 3).
- Removed fast-path restatement paragraph (−2 lines, Dim 6).

Scores: self 72→83 (cold), blind 70→79 (Opus 5 pin, both passes). No dimension
self/blind gap ≥2 at either end.
