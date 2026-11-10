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

