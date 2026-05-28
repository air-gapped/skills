# Improvement Backlog — autoresearch

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Open

### B1 — Boris simplicity cap on Mode 2/3 procedural scaffolding (Dim 6)
- **Dimension:** Dim 6 (Simplicity), cross-cutting Boris "strict workflow scaffolding" cap.
- **Where:** `SKILL.md` Mode 2 (Step 1/2/3, ~L159-203) and Mode 3 (Phase 1/Phase 2, ~L207-238); also the Mode 1 `Step 2` numbered list (~L74-82). The Mode 1 `Step 3` LOOP (~L89-128) is genuine algorithm — leave it.
- **Evidence (why it's open, not done):** Two independent Opus blind scorers *disagree* on whether the cap fires — baseline agent scored Dim 6 = 8 ("numbered lines are reference content, not invocation scaffolding"); final agent scored Dim 6 = 6 ("Step 1/2/3 and Mode 2/3 sequences prescribe invocation flow discoverable via plan mode"). The cap is genuinely borderline. Lifting it cleanly means converting the most mechanical numbered wrappers in Modes 2/3 to terse standing-instruction prose while preserving the differentiated content (STORM decomposition, breadth-halving, research→optimize handoff, subjective→binary-assertion conversion).
- **Why not applied in one iteration:** It is a multi-section prose rewrite (not pure relocation), so it fails the atomicity split-test, and it risks eroding author intent (the numbered teaching structure) and Dim 10 differentiation for a contested +2. Needs author judgment on how much procedural framing to keep.
- **Action:** Author decides whether to collapse Mode 2/3 `Step`/`Phase` wrappers to prose. If yes, do it as one focused pass (keep the Mode 1 LOOP verbatim) and re-score Dim 6 + Dim 4 cold.

### B2 — Star counts in ecosystem.md rot immediately (Dim 9, cosmetic)
- **Dimension:** Dim 9 (Domain Accuracy), minor.
- **Where:** `references/ecosystem.md` — "67K stars" (now 83.9K), "18.6K stars", "2.2K stars", "4.5K stars", etc.
- **Why open:** `sources.md` policy deliberately does NOT mutate star drift ("not a correctness claim"), so each freshen leaves them stale. The cleaner fix is to *delete* the star counts (they are transient noise, not correctness claims) rather than chase them every pass.
- **Why not applied:** Touches ~6 author-written bullets; deletion of author content is a judgment call, not a freshen mutation. Left for author.

### B3 — Browser-MCP-in-the-loop verifier (Dim 5/10, optional)
- **Dimension:** Dim 5 (Completeness) / Dim 10 (Differentiation).
- **Where:** `references/domain-templates.md` and/or Mode 1 verifier guidance; `allowed-tools` in `SKILL.md` frontmatter.
- **Why open:** Karpathy's Jan 2026 primary source (now cited in sources.md) explicitly lists "put it in the loop with a browser MCP" as a leverage technique. The skill's verifiers are all CLI-based; a browser-driven verifier (visual regression, e2e metric, scraped number) is a legitimate Mode 1 pattern not covered. Adding it would also need browser tools in `allowed-tools`.
- **Why not applied:** Feature addition + frontmatter tool-scope change; out of proportion to a single hill-climb iteration and arguably niche. Author should decide if browser-loop verifiers are in scope for this skill.

### B4 — "deep research" trigger overlaps the built-in deep-research skill (Dim 1)
- **Dimension:** Dim 1 (Trigger Precision).
- **Where:** `SKILL.md` `when_to_use` L11 — "deep research".
- **Why open:** Both final blind scorers noted the phrase collides with the separate `deep-research` built-in skill (possible contention / false-positive). This is empirical trigger territory — resolve with `trigger` mode (eval set + `claude -p` probes), not a blind description edit.
- **Action:** Run `/skill-improver trigger autoresearch` with a `--missed`/should-NOT-trigger eval set distinguishing autoresearch's Research mode from generic deep-research requests.

## Resolved this pass (2026-05-28)

- **Freshen — date stamps:** Probed and stamped `Last verified: 2026-05-28` on karpathy/autoresearch (×2), stanford-oval/storm (v1.1.0 pin confirmed), WecoAI/aideml, gepa-ai/gepa, SakanaAI/ShinkaEvolve, metauto-ai/HGM, dzhng/deep-research, alvinreal/awesome-autoresearch. All alive, unarchived, no drift/deprecations/broken links. Three-file architecture of karpathy/autoresearch verified in the live tree.
- **Freshen — new primary source (Dim 9/10):** Added Karpathy's "notes from claude coding" X post (x.com/karpathy/status/2015883857489522876, 2026-01-26) to `sources.md` Canonical and `ecosystem.md`. Verified live via the Chrome browser agent. Its *Leverage* paragraph is the author's own articulation of the skill's thesis; same post the 160K-star `andrej-karpathy-skills` repo derives from.
- **Improve — Dim 6 (kept, +1 self):** Trimmed `SKILL.md` Blind Validation section from a duplicated 3-step protocol to a summary + pointer, matching the skill's own progressive-disclosure pattern (the full protocol already lives in `experiment-loop.md`). 329→324 lines, no decision rule lost.
- **Improve — crash/timeout consolidation (attempted, discarded):** Tried replacing the inline crash/timeout bullets in LOOP Step 4 with a pointer to the Crash Handling section. Discarded — the loop is the skill's core executable artifact and must read top-to-bottom; the inline thresholds are the loop-critical subset, intentionally placed. Net actionability cost for ~0 simplicity gain.

## Score record

| Pass date | Self | Blind (Opus) | Notes |
|-----------|------|--------------|-------|
| 2026-05-28 baseline | 88 | 90 | mature skill, no caps fired by baseline scorer |
| 2026-05-28 final | 89 | 89 | Dim 6 contested (Boris cap: scorer A=8, scorer B=6); freshen + 1 keep, 1 discard |
