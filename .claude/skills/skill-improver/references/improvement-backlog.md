# Improvement backlog — skill-improver

Open blockers, decisions, and rejected changes that must not be re-proposed. Pass history is in git.

## Open

(none)

## Decided

- **Outcome evals stay on Claude Code** (2026-11-10). A second harness is built only when someone who runs one asks for the number.

- **Second outcome harness: OpenCode headless against an OpenAI-compatible
  endpoint, through the `opencode-ci-harness` skill's isolated runner**
  (2026-11-10). Reason: it runs an agent loop outside Claude Code, on a model
  that need not be Claude, with its own profile isolation — the two axes the
  current outcome numbers do not cover. Re-open if a case needs a tool that
  runner cannot grant.
- **Scorer ranking stability on close-quality skills: sweep not run**
  (2026-11-10; was Open since 2026-08-20). Reason: its result would only reorder
  a batch, and whether a pass helped is decided by the A/B comparator, not by
  blind totals. Re-open if an ordering by blind total between skills within five
  points of each other starts deciding something the comparator does not cover;
  the harness is `evals/scorer-sweep.2026-08-20.json`, about 60 scorer runs.

## Discard guards — do not re-propose

- **(2026-07-24) Dim 6/4: symptom → mode dispatch table** in §Invocation
  (13 lines). Net-negative: the table duplicated guidance already carried by
  the Trigger Mode stub ("Use trigger mode when…") and Standalone Evaluation
  step 4, so the Dim 4 gain was cancelled by Dim 6 redundancy. Do not
  re-propose as an addition — if mode dispatch is wanted at the entry point it
  has to *replace* those two passages. **Moved out of Open 2026-08-20:** a
  judged-net-negative change is a guard against re-proposal, not work pending a
  blocker, and it fails the admission test (the only thing standing in its way
  was the size of the rewrite, which is effort, not an absent thing). Keeping it
  under Open inflated the count with something nobody should ever do.

## Discards / judged no-ops — prior passes (2026-05-28 / 2026-06-09)

- **(carried 2026-05-28) Dim 2: collapse the freshen/trigger mode-summary stubs
  into one table** (a final blind agent's suggestion). DISCARD — the prose stubs
  carry the trigger context the model uses to know the modes exist; a table
  would compress that signal for ~3 lines. Net-negative. Applies equally to the
  philosophy stub added 2026-06-09.
- **Dim 6: trim ~20–30 lines of deliberate reinforcement** ("Operating Rules"
  restating phase rules; "What a stop is NOT"; "Open is NOT a wishlist"). Blind
  agents scored Dim 6 at 6–7 citing this density both passes. The 2026-05-28 run
  analyzed the deletion and DISCARDED it: the overlap is standing-instruction
  reinforcement that survives compaction (`anthropic-skill-design.md` §"Skill
  Content Lifecycle"). Author decision stands; re-evaluate only if a future
  blind agent shows the redundancy causing *behavioral* errors, not just
  rubric-cosmetic cost.

## Discard guards — recovered from earlier passes

Rejected changes recorded inside past passes' sections. Do not re-propose one unless a kept change has removed the reason it failed.

- (2026-11-09) one sentence in SKILL.md §Improve saying every iteration is self-scored and ends in keep or discard, aimed at eval 02's third assertion (re-evaluate, then decide), which fails every run with and without the skill. After the edit two of three answers self-scored and said keep;
- (2026-11-09) a hint line in `outcome-eval.py`'s weak-case list when an assertion fails every run in both arms. Replayed on the benchmark result it flagged both eval-side failures above, but it is additive, moved no rubric dimension and removed no defect (Δ0).
- (2026-11-09) deleting the SKILL.md §Outcome sentence that says what a run prints at its end, kept at Δ0 as a duplicate of the `scripts.md` row. All three comparators listed the removal under the winning side's regressions;
- (2026-09-23) judging freshen from history alone — every skill freshened a week earlier reads "not due"; misses all five real changes.
- (2026-09-23) "releases since the last pass" — misses a pass that stamped a skill but left an old version in its body (helm v4.2.4, barman v0.14.0). Compare against the version the text states.
- (2026-09-23) `floor` added to mode grammar/argument-hint — band-internal, additive (Open, above)
- (2026-09-23) "binds blind scorers" → every subagent's version finding — band-internal, additive (Open, above)
- (2026-09-01) extracting §A Measurement That Failed to a one-rule reference: Dim 2 band unchanged at 439 lines, a 16th reference for one rule is the too-granular failure, and the per-mode failure mechanisms land a hop from the rule they justify
- (2026-07-24) porting only the Dim 9 cap sentence into the blind prompt left the rest of the drift in place; Dim 8 stayed band-internal.
- (2026-07-18) example row in rubric §Results Log Format — Dim 8 pinned by the then-open P0 chain; pure addition.
- (2026-07-18) P0-chain flatten +1 failed cold rescore against a *false* blocker (see incident below); re-proposed and kept as iter 5 under the buffer's new-evidence exemption.
- (2026-08-15) trimming the v2.1.105 boundary from trigger-patterns' T4 constraint as "provenance archaeology" — reverted: the version is the decision boundary for which cap applies, and trigger mode loads without the rubric.
- (2026-08-15) rule-ceiling — invocation-fit self-record (moved to Open).
