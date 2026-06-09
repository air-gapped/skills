# Improvement Backlog — autoresearch

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Open

### B1 — Boris simplicity cap on Mode 2 procedural scaffolding (Dim 6) *(carried 2026-06-09, evidence updated)*
- **Dimension:** Dim 6 (Simplicity), cross-cutting Boris "strict workflow scaffolding" cap.
- **Where:** `SKILL.md` Mode 2 (Step 1/2/3, ~L164–197). Mode 3's Phase wrappers were
  converted to prose on 2026-06-09 (partial resolution); Mode 1's LOOP and Step 2
  baseline list are genuine algorithm — leave them.
- **Evidence:** The cap now fires for **3 of the 4 most recent blind scorers**
  (2026-05-28 final, 2026-06-09 baseline, 2026-06-09 final; only the 2026-05-28
  baseline scorer exempted). The 2026-06-09 final scorer adds two sharper claims:
  (a) collapsing Mode 2's Step wrappers would lift Dim 6 AND likely drop SKILL.md
  (331 lines) under the 300-line lean band, fixing Dim 2 as well; (b) Mode 2
  "partially duplicates the built-in `deep-research` skill", which dilutes Dim 10.
- **Why not applied:** Mode 2's steps carry the STORM decomposition and synthesis
  pedagogy — converting is a multi-section prose rewrite (fails the atomicity
  split-test) AND there is a scope question only the author can settle: keep Mode 2
  as a differentiated in-skill workflow, or slim it toward a pointer now that a
  built-in `deep-research` skill exists.
- **Action:** Author decides Mode 2's fate (full prose conversion vs scope cut).
  If converting, do it as one focused pass and re-score Dims 6/2/4/10 cold.

### B3 — Browser-MCP-in-the-loop verifier (Dim 5/10, optional) *(carried 2026-06-09)*
- **Dimension:** Dim 5 (Completeness) / Dim 10 (Differentiation).
- **Where:** `references/domain-templates.md` and/or Mode 1 verifier guidance; `allowed-tools` in `SKILL.md` frontmatter.
- **Why open:** Karpathy's Jan 2026 primary source explicitly lists "put it in the
  loop with a browser MCP" as a leverage technique; the skill's verifiers are all
  CLI-based. Both 2026-06-09 scorers independently named this the main completeness gap.
- **Why not applied:** Feature addition + frontmatter tool-scope change; author should decide if browser-loop verifiers are in scope.

### B4 — "deep research" trigger overlaps the built-in deep-research skill (Dim 1) *(carried 2026-06-09, evidence updated)*
- **Dimension:** Dim 1 (Trigger Precision).
- **Where:** `SKILL.md` `when_to_use` L11 — "deep research".
- **Why open:** All four recent blind scorers flag the collision with the installed
  built-in `deep-research` skill. The 2026-06-09 final scorer suggests disambiguating
  (e.g., "deep research with recursion/synthesis into a saved report"). The
  2026-06-09 baseline scorer also noted `evals/evals.json` has zero should-NOT-trigger
  cases, so the collision is currently unmeasurable.
- **Action:** Run `/skill-improver trigger autoresearch` with should-NOT evals that
  belong to the built-in `deep-research` (generic one-shot research asks) vs this
  skill's Research mode (recursive, saved-report, optimize-handoff asks). Empirical, not a blind description edit.

## Resolved this pass — 2026-06-09 (improve + freshen)

Baseline self **84** / blind **80** (Fable 5 scorer) → final self **86** / blind **84**.
10 kept iterations + 2 post-flag nits, 0 discards (10-iteration cap reached; no ceiling claim).

- **Freshen — stamps:** 21 sources.md rows re-verified and stamped 2026-06-09
  (9 GitHub repos via `gh api` liveness/archived/pushed_at; 10 non-GitHub URLs via
  batch HTTP probe, pjhoberman 429 confirmed alive via WebFetch; Shopify PR #2056
  still OPEN, claims unchanged). Zero drift, deprecations, or broken links.
  karpathy/autoresearch dormant-healthy (no pushes since 2026-03-26).
- **B2 RESOLVED — star counts deleted:** removed the four standalone star-count
  sentences from `ecosystem.md` (67K/2.2K/4.5K/18.6K — drift had reached 28% on the
  headline repo, third consecutive pass of rot; backlog itself named deletion the
  cleaner fix). Header date refreshed. *Residue:* the adjectival "160K-star
  andrej-karpathy-skills" phrasing remains in ecosystem.md + sources.md — embedded
  in prose, author call whether to degrade it to "widely-forked".
- **Dead stopping rule fixed (baseline-blind top issue):** "Plateau: 5 consecutive
  discards" stop made "Ceiling mapped: 8+" unreachable and contradicted
  experiment-loop.md §Local Maxima escape-at-5 guidance. Plateau now pivots via the
  escape strategies; ceiling-at-8+ (3 categories) is the discard-based stop.
- **Mode 3 Phase wrappers → prose** (partial B1): 9 numbered invocation-flow lines
  converted; all content preserved (research targets, subjective→binary conversion,
  config-confirm handoff, provenance). Mode 1 LOOP untouched.
- **Voice sweep (Dim 3):** 18 second-person body slips converted across
  experiment-loop.md (8), domain-templates.md (4, incl. heading + TOC anchor),
  deep-research.md (5+1 found by final blind). Agent-prompt-template second person kept intentionally.
- **Loose files referenced (Dim 2/8):** sources.md + improvement-backlog.md added to SKILL.md Additional Resources.
- **Verifier permission warm-up note (baseline-blind Dim 9 finding):** Step 2
  baseline run documented as the permission warm-up, since Bash is pre-approved
  only for `git *`; wording clarified after the final blind flagged ambiguity.
- **evals.json alignment (Dim 8):** eval 1 expectation now accepts revert (the
  skill's actual mechanism) alongside reset.

## Resolved — 2026-05-28

- **Freshen — date stamps:** Probed and stamped `Last verified: 2026-05-28` on karpathy/autoresearch (×2), stanford-oval/storm (v1.1.0 pin confirmed), WecoAI/aideml, gepa-ai/gepa, SakanaAI/ShinkaEvolve, metauto-ai/HGM, dzhng/deep-research, alvinreal/awesome-autoresearch. All alive, unarchived, no drift/deprecations/broken links. Three-file architecture of karpathy/autoresearch verified in the live tree.
- **Freshen — new primary source (Dim 9/10):** Added Karpathy's "notes from claude coding" X post (x.com/karpathy/status/2015883857489522876, 2026-01-26) to `sources.md` Canonical and `ecosystem.md`. Verified live via the Chrome browser agent. Its *Leverage* paragraph is the author's own articulation of the skill's thesis; same post the 160K-star `andrej-karpathy-skills` repo derives from.
- **Improve — Dim 6 (kept, +1 self):** Trimmed `SKILL.md` Blind Validation section from a duplicated 3-step protocol to a summary + pointer, matching the skill's own progressive-disclosure pattern (the full protocol already lives in `experiment-loop.md`). 329→324 lines, no decision rule lost.
- **Improve — crash/timeout consolidation (attempted, discarded):** Tried replacing the inline crash/timeout bullets in LOOP Step 4 with a pointer to the Crash Handling section. Discarded — the loop is the skill's core executable artifact and must read top-to-bottom; the inline thresholds are the loop-critical subset, intentionally placed. Net actionability cost for ~0 simplicity gain.

*(2026-05-28 record restored 2026-06-09 — dropped in that day's backlog rewrite;
prior-pass history stays in the live file so future loops inherit it without
digging through git.)*

## Score record

| Pass date | Self | Blind | Notes |
|-----------|------|--------------|-------|
| 2026-05-28 baseline | 88 | 90 (Opus) | mature skill, no caps fired by baseline scorer |
| 2026-05-28 final | 89 | 89 (Opus) | Dim 6 contested (Boris cap: scorer A=8, scorer B=6); freshen + 1 keep, 1 discard |
| 2026-06-09 baseline | 84 | 80 (Fable 5) | Dim 8 flag (+2): dead stopping rule; Dim 6 Boris cap fired |
| 2026-06-09 final | 86 | 84 (Fable 5) | no 2+ gaps; Dim 6 cap persists on Mode 2 (B1) — 3 of last 4 scorers cap it |
