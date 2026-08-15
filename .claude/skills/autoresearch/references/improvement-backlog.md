# Improvement Backlog — autoresearch

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Resolved — 2026-08-16 (operator-directed restructure)

- **Fan-out cache discipline (skill-improver improvement-patterns 7.3).**
  The Mode 2 Research Agent Prompt Template moved verbatim into the
  `deep-researcher` agent definition (`.claude/agents/`, shipped as
  `agent:deep-researcher`) — one cached system prompt shared across each
  research round; spawns send only question/angle/prior-learnings.
  `references/deep-research.md` keeps the tail template and fallback. No
  change to the return format or synthesis flow.

## Resolved this pass — 2026-07-24 (improve + freshen)

Baseline self **79** (recalibrated from 82 after the blind scorer verified two
Dim 8 defects) / blind **74** (Opus 5) → final self **85** / blind **80**.
10 kept iterations, 0 discards (10-iteration cap reached; **no ceiling claim** —
see the honesty note at the end of this section).

- **B1 RESOLVED — Boris simplicity cap lifted.** Mode 2's Step 1/2/3 wrappers
  converted to prose, all content preserved (STORM perspectives, agent dispatch,
  the 5-item synthesis list, depth table). The final blind scorer now explicitly
  exempts the skill: "Boris scaffolding cap does **not** fire — the 19 numbered
  lines are dominated by the Mode 1 LOOP, which is the skill's genuine algorithm
  rather than derivable invocation flow." Carried since 2026-06-09, capped by 3
  of the previous 4 scorers.
- **Two live cross-file contradictions fixed (Dim 8, found by the baseline
  blind, not by self-scoring).** SKILL.md hardcoded `>2x baseline` timeout in two
  places against the tiered 3x/2x/1.5x/1.3x table in `experiment-loop.md:115-120`
  (short experiments were being wrongly killed), and specified flaky handling as
  *twice, average, >5%* against the reference's *3 runs, median, >2%* — a
  different threshold **and** a different aggregator. Both reconciled.
- **Duplication class eliminated, not just its symptom.** The standalone "Crash
  Handling" section was deleted and its two non-loop rules (runtime crash, flaky
  results) folded into LOOP step 4, leaving one authority inside SKILL.md. Note
  this is the *inverse* of the 2026-05-28 discard, which thinned the loop in
  favour of a pointer and was rejected because the loop must read top-to-bottom;
  this change completes the loop and removes the redundant section, so the
  contradiction cannot re-form.
- **Freshen — first real drift in four passes, invisible to liveness probes.**
  `alvinreal/awesome-autoresearch` → **`webfuse-com/awesome-autoresearch`**.
  GitHub redirects the old URL, so `archived=false` + HTTP 200 both pass while
  the canonical owner is wrong. Fixed in `ecosystem.md` + `sources.md`, with the
  method fix recorded inline: **probe `full_name` in the API response, not the
  HTTP status.** This is precisely what the 2026-07-21 method note predicted.
- **Freshen — new "Benchmarks for the Loop Itself" section.** PERFOPT-Bench
  (arXiv:2607.07744, 2026-07-08), OPT-BENCH (2605.08904), SEAGym (2606.17546).
  PERFOPT-Bench is the load-bearing one: the harness changes per-task speedup
  independently of the model, large gains are frequently shortcut exploitation
  (independent support for the anomaly check), and cross-session summary
  externalization measurably unlocks further gains.
- **Freshen — new "Mechanisms Worth Borrowing" section.** `goal-md` (construct
  the fitness function before optimizing — independent arrival at Mode 3's
  premise), `autoautoresearch` (novelty injection to escape stalls),
  `autoresearch-engram` (cross-session memory), `EvoSkill` (evolve skills from
  failed trajectories). Grouped by mechanism rather than scattered into the port
  lists, so the section stays useful as it grows.
- **Freshen — STORM's dormancy now has live competition** recorded under Research
  Patterns: `deer-flow` (pushed on the probe date), `gpt-researcher`,
  `open_deep_research`. The pattern Mode 2 borrows still holds; the codebase is
  what has been overtaken.
- **Resume procedure added (Dim 5)** — PERFOPT-Bench's cross-session finding and
  the baseline blind's "no resume-after-interrupt procedure" gap converged on the
  same hole: the skill wrote session summaries but never said to read one back.
- **Budget guardrail added to Mode 1 Step 1 (Dim 5)** — verifier duration ×
  iteration cap, stated when presenting the configuration, changed before the
  loop rather than during it.
- **Mode 2 save path disambiguated (Dim 8)** — reports go to the skill's own
  `results/`, not the target project tree. Documents the existing convention
  rather than changing it.
- **sources.md grew 21 → 39 rows**, oldest `Last verified:` 2026-05-28 (57 days,
  no Dim 9 cap).

### Post-blind pass — B5/B6/B7 closed the same day

The three items the final blind scorer raised were applied after it returned, so
the recorded blind **80** predates them. Scored cold afterwards: still **85**
self. The fixes were real but the metric did not move, and that is the finding —
dedup returned ~5 lines while the two new guardrails cost ~15, so Dims 2/6 held
at 7. Trading the guardrail content back for line count would be optimizing the
score against the artifact, which is the reward hacking this skill exists to
warn about. Left as-is deliberately.

- **B5 CLOSED — but not by the blanket rule the scorer proposed.** Its three
  "duplications" were three different problems. (a) *median-of-3*: the SKILL.md
  copy is inside the LOOP, which the 2026-05-28 discard established must read
  top-to-bottom — so the **reference** side was trimmed instead, and
  `experiment-loop.md` §Nondeterminism now carries only source-level noise
  remedies (seeds, deterministic algorithms, cache pinning) plus a pointer.
  (b) *local-maxima escape*: *not duplication* — `SKILL.md:150-152` was already
  a bare pointer with no restatement. Scorer error; no change. (c) *provenance
  comments*: the genuine case — Mode 2 and Mode 3 each re-explained the
  mechanism the dedicated section owns; both reduced to bare pointers.
- **B6 CLOSED** — Mode 2 now budgets its fan-out (~11 agents Standard, ~23
  Exhaustive) and names web searches, not agents, as the binding constraint
  against the session's 200-search cap, with the failure mode stated: exhausting
  it fails mid-synthesis with partial findings and no report.
- **B7 CLOSED — and the scorer's premise was wrong.** The blind scorer framed
  `allowed-tools: Bash(git *)` as the loop being unable to run its own verifier.
  It is not: `allowed-tools` is a **pre-approval** list, not a restriction list
  (the restriction field is `disallowed-tools`, v2.1.152, which this skill does
  not use — see `anthropic-skill-design.md` frontmatter table). Nothing is
  blocked; WebSearch / WebFetch / Agent are pre-approved so Mode 2's fan-out does
  not prompt per agent, and Bash runs the verifier fine, it just asks once. The
  first wording of this fix inherited the scorer's error and implied a capability
  limit; corrected to state what the field actually does, and to allow the
  sensible middle option — pre-approving a *specific* verifier (`Bash(pytest *)`)
  is fine, blanket `Bash` is not.
  **Method note:** a blind scorer asserting a platform-semantics claim is not
  evidence. Check the frontmatter reference before acting on one.

**Honesty note — this run mapped no ceiling.** Ten iterations, ten keeps, zero
discards. Per skill-improver's own rule, a run with zero discards has not
demonstrated a ceiling; it hit the iteration cap with work still available. The
items under Open below are real remaining work, not a ceiling.

## Resolved — 2026-07-24 (B3, browser verifiers)

**B3 CLOSED — scoped down, not built out.** Carried since 2026-06-09; both that
day's scorers called the absence of a browser-driven verifier the main Dim 5 gap,
citing Karpathy's "put it in the loop with a browser MCP".

Checking first narrowed it: `domain-templates.md` already ships a Lighthouse
verifier measuring a real rendered page, so page-load metrics were never actually
missing. What a driven browser adds is only what a headless one-shot cannot see —
interactive flows, UI state, multi-step journeys.

Resolved as guidance rather than a feature, and deliberately so: raw interactive
timings swing 10%+ run-to-run, which is larger than most single experiments move
the metric, so they are the worst possible input to a keep/discard ratchet. The
new "Browser Flows" template says to convert the observation to binary assertions
first (the same subjective→binary conversion Mode 3 already prescribes), or take
a median of N if a continuous metric is genuinely needed — and to declare the
target un-optimizable when neither yields variance smaller than the improvement
being chased.

No frontmatter change: driving a browser takes the same one-time verifier
approval as any other non-git command, which the least-privilege design in
Mode 1 Step 3 already covers (see B7).

*Context for the timing:* this closed the same day the trigger run showed an
underpowered measurement manufacturing two false conclusions. Adding the noisiest
verifier class as a headline capability would have pointed the loop at exactly
the failure mode it handles worst.

## Resolved — 2026-07-24 (trigger mode)

**B4 RESOLVED — and its premise was backwards.** Carried since 2026-06-09 and
flagged by all four blind scorers as an over-trigger risk: `when_to_use` claimed
the bare phrase "deep research", colliding with the bundled `deep-research`
skill. Measured with `probe-trigger.py` against a new 14-query eval set
(`references/trigger-evals.json`, 7 should-trigger / 7 should-NOT):

**Zero false positives, ever.** All 7 should-NOT queries returned 0.00 at
baseline, including both bare research asks ("Do deep research on EU AI Act
compliance deadlines", the Postgres/MySQL comparison) and the supposedly
over-broad numeric clause ("Make this function faster"). The collision three
passes of blind scorers worried about does not exist. Rubric scoring had the
sign wrong because reading a description cannot tell you what it competes with.

**The real defect was the opposite — under-triggering on its own advertised
phrases.** Baseline fired on only 4/7 should-trigger queries; Mode 3 ("research
best practices and then improve it") fired **1/7** — an entire mode effectively
invisible. Adopted description lifts mean trigger rate **0.531 → 0.694**
(26/49 → 34/49 fires at N=7), with Mode 3 at **1/7 → 6/7** (Fisher exact
p≈0.03) and **0/35 false fires** on the should-NOT set. Evidence strength:
the Mode 3 cell is individually significant; the aggregate (z≈1.66, p≈0.10) is
suggestive, not conclusive. Adopted on the combination of a clean boundary and
one unambiguous fix.

**Two discards worth not re-proposing:**
- *Full plain-language rewrite with `autoresearch` moved out of the lead*
  (cand1 as first probed): at N=3 this read as breaking the canonical
  "set up an autoresearch loop" query 0.67 → 0.00, which prompted an entire
  wasted iteration to "restore the proper noun to position 0". At N=7 the same
  pair was **6/7 vs 5/7 — noise**. There is no proper-noun-placement mechanism.
  Do not re-derive one.
- *Minimal targeted edit — baseline plus a broadened Mode 3 clause only*
  (+86 chars vs +339): scored **worse** than the full rewrite (Mode 3 3/7 vs
  6/7, mean 0.592 vs 0.694). The extra prose in the adopted version is doing
  real work; trimming it back to "just the proven clause" loses half the gain.
  This one is counterintuitive and will look like an obvious simplification to
  a future pass — it was measured and rejected.

**Method note:** the eval set is now persistent. Re-probe at
`--runs-per-query 7`; N=3 is reconnaissance only (see the noise-floor rule added
to skill-improver `trigger-patterns.md` §T5 the same day, which this run
produced).

## Resolved — 2026-07-21 (freshen)

**Third consecutive clean pass.** All 16 ecosystem repos alive and unarchived;
all 9 non-GitHub URLs return 200; Shopify Liquid PR #2056 still OPEN with
unchanged claims. Nothing to correct.

The value this pass was **separating "stable" from "dormant"** — three passes of
"no drift" can quietly mean "nothing is being maintained":

- **stanford-oval/storm** — the v1.1.0 pin has held across three passes, but
  v1.1.0 is from **2025-01-23 (~18 months)** and the repo last pushed
  **2025-09-30 (~10 months)**. Annotated in `ecosystem.md` so a reader doesn't
  infer active maintenance from a stable pin: Mode 2 borrows the *pattern*,
  which doesn't rot — treat the codebase as reference, not a tracked dependency.
- **SakanaAI/AI-Scientist-v2** — last push 2025-12-19 (~7 months).
- **karpathy/autoresearch** — dormant since 2026-03-26 (~4 months) while stars
  climbed **85,764 → 91,664** in six weeks. Recorded as a trend note in
  `sources.md` only (B2 keeps counts out of the body). The distinction matters
  for a skill whose methodology derives from that repo: the source is static,
  the practice is spreading. Dormancy is not deprecation here.

Most active, for contrast: `gepa-ai/gepa` pushed on the probe date itself,
`ralph-claude-code` (9.5k stars), `ShinkaEvolve`, `awesome-autoresearch`,
`aideml` — all within the last week.

**Method note for future passes:** a clean liveness sweep is necessary but not
sufficient. `archived=false` + `HTTP 200` says a link works, not that the
project moved. Record `pushed_at` age alongside liveness so dormancy shows up
as a signal rather than as an absence of findings.


## Open

*Empty as of 2026-07-24 — B1/B4/B5/B6/B7 resolved, B3 scoped down and closed.*

**This is not a ceiling claim.** Every item that had been attempted and parked is
now closed; that means the backlog is current, not that the skill is finished.
The 2026-07-24 improve run hit its 10-iteration cap with zero discards, which by
this skill's own rule demonstrates no ceiling at all. Known live constraints for
the next pass: Dim 2/6 sit at 7 because SKILL.md is 353 lines (the guardrail
content added on 2026-07-24 was judged worth the length — do not trade it back
for line count), and **Dim 10 is now capped at 8 for this skill until
`delta_pass_rate` is measured** under skill-improver's Negative-Transfer Gate.
`evals/evals.json` exists with 3 cases, so that measurement is available to run
and has not been run.

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
| 2026-07-24 baseline | 79 | 74 (Opus 5) | self recalibrated 82→79 after blind verified 2 real Dim 8 contradictions; Dim 8 gap +3, Dim 2 gap +2 |
| 2026-07-24 final | 85 | 80 (Opus 5) | no 2+ gaps; **B1 closed** — blind explicitly exempts Mode 1 LOOP from the Boris cap |
