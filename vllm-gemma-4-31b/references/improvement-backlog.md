# Improvement backlog — vllm-gemma-4-31b

Carries findings across `/skill-improver` runs. Skill-improver reads this in
Phase 0 and updates it in Phase 6. Do NOT delete entries — move to "Resolved
this pass" instead.

## Open

### 1. Narrow trigger surface (Dim 1 — locked at 7 by author mandate)

**Pointer:** `SKILL.md:6-7` (`when_to_use`)

**Finding:** Blind scoring agent (2026-04-30 final pass) flagged that
`when_to_use` requires both "Gemma 4 31B" AND {vLLM, deployment, tuning,
performance} to fire. Misses common operator shorthand: "AWQ-4bit gemma",
"cyankiwi", "RedHatAI", "EAGLE3 speculator gemma", "serving gemma-4 on H100".

**Why skill-improver couldn't apply it:** the author explicitly rejected
broader trigger surfaces in this skill's authoring session (2026-04-30):

> "no one writes like this... sorry but remove those triggers '31B
> replacement for our 27B', 'long-document summarizer', 'why does
> throughput plateau' — the only triggers are really gemma 4 31b"

> "you do not need the exact words with or without dashes do you? you
> would understand anyway would you not?"

The 7/10 score is by design, not by oversight. **Do not auto-fix in `improve`
or `freshen` mode.** If trigger misses become a problem in practice, switch
to `/skill-improver trigger vllm-gemma-4-31b --missed "<phrase>"` mode to
measure empirically — that's the only mode the author has consented to.

### 2. "Why gemma-4-31B-AWQ behaves differently" section is speculative without citations (Dim 6)

**Pointer:** `SKILL.md:124-143`

**Finding:** Four numbered "likely reasons" (AWQ vs fp8 weight size,
TRITON_ATTN scaling, EAGLE3 spec-dec topology, 31B vs 27B layer count) are
plausible mechanisms but none carry a measurement or upstream-source citation.
Blind agent suggested either (a) labelling explicitly as hypothesis with
"unverified" tag, (b) trimming, or (c) moving to a references/ file.

**Why skill-improver couldn't apply it in one iteration:** the section is
load-bearing — it answers the most likely user question ("why does my 27B
intuition not transfer?"). Trimming risks removing the explanatory value;
moving to references/ risks burying it. The right fix is a follow-up
empirical run measuring TP=1 vs TP=2 on Gemma 4 with one mechanism varied
at a time (e.g., FLASH_ATTN backend forced, EAGLE3 disabled, fp8 vs AWQ).
That's a multi-hour GPU-instance investigation, not a single edit.

**Trigger to revisit:** if the operator runs a new Gemma 4 audit (any
quant), produce data points that confirm or refute each mechanism, then
edit this section in a dedicated change.

### 3. SKILL.md length 263 lines (Dim 2 — could push to "focused" tier)

**Pointer:** `SKILL.md` overall

**Finding:** Blind agent noted 263 lines is fine under the 500-line cap
but slightly over the 150-line "focused" target. Recipe code blocks at
`SKILL.md:62-76` (LIGHT) and `SKILL.md:89-103` (PUSH) could move to
`references/recipes.md`, freeing ~30 lines.

**Why skill-improver couldn't apply it in one iteration:** the recipes ARE
the headline value of the skill — moving them behind a reference indirection
adds a load step every time the skill triggers. Trade-off is genuine. Not a
clean win without more user signal.

**Trigger to revisit:** if `/skill-improver score` ever caps Dim 2 below 7
(currently 8), reconsider. Today the skill is well under 500 and the recipe
inlining is intentional.

### 4. "Reproduction artifacts" tree at `SKILL.md:246-262` points to a private repo (Dim 6/8 — minor)

**Pointer:** `SKILL.md:246-262`

**Finding:** Block lists paths in the `model-preflight` repo
(`findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/...`). Useful for the author's
future reference but inert for any other skill consumer.

**Why skill-improver couldn't apply it:** removing it might violate
"Preserve the Author's Intent" — the author is the primary consumer of
this skill (this is a personal-knowledge capture, not a public-facing
artifact). Author should decide explicitly whether to keep, trim, or
gate behind a `<details>` block.

**Trigger to revisit:** if the skill ever ships to a public skills index or
gets shared with collaborators, drop the section then.

## Resolved this pass

- Created `references/sources.md` with 10 verified upstream refs (HF
  models, vLLM source paths, GH issues / PRs) all stamped
  `Last verified: 2026-04-30`. Lifted Dim 9 from 6/10 (capped) to 9/10.
- Swept SKILL.md to imperative voice — removed `your`/`we`/`us`
  constructions at original lines 14, 126, 146, 150, 152, 200, 219.
  Lifted Dim 3 from 5-7/10 to 9/10 (blind).
- Removed personal-memory absolute path at original line 163
  (`~/.claude/projects/.../feedback_one_restart_means_fail.md`).
  Surrounding paragraph already explains the rule. Lifted Dim 8 to 9/10.
- Added `references/sources.md` pointer to SKILL.md References list so the
  new file is discoverable.

**Final score (2026-04-30):** self 84/100, blind 86/100. Up from baseline
self 78 / blind 79. Four kept iterations, zero discards.
