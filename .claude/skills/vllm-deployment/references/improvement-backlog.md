# Improvement backlog — vllm-deployment

Work-not-done log for the skill-improver loop. `## Open` lists issues attempted as
hypotheses that could not be applied (or safely verified) in a single iteration.
`## Resolved this pass` lists changes the metric actually registered.

## Open

None.

## Decided

- **No boundary clause for benchmarking or KV-cache queries.** A `vllm bench
  serve` SLO sweep and an LMCache KV-offload question fire here only when this
  is the sole skill installed (4/7 and 3/7; 5/7 and 1/7 after the trim). With
  the 14 `vllm-*` siblings installed both read 0/7, before and after. Reason: a
  "do NOT use for" clause adds the very words it excludes. Re-open if either
  fires with the siblings installed.
- **No change for the "without restarting" pair with
  `vllm-speculative-decoding`.** The spec-decode flag question does not fire
  here (0/7). The rollout question that mentions spec decode in passing fires
  7/7 alone; with the sibling installed, 6/7 before the trim and 7/7 after.
  Both queries are in
  `trigger-evals.json`. Re-open if the rollout question falls below 4/7 with
  the siblings installed.

## Resolved this pass (2026-11-10 — trigger)

Baseline train 21/22, test 13/14 → final train 21/22, test 13/14 on
`claude-sonnet-5-5` at 7 runs per query; 1 iteration, 1 kept, 0 discarded;
`description` + `when_to_use` 1454 → 1217 characters.
- Kept: nine `when_to_use` phrasings that restate the description, and the
  description's closing author note, removed. Mean trigger rate: train should
  1.00 → 1.00, should-not 0.10 → 0.10; test should 0.86 → 0.89, should-not
  0.00 → 0.00. The 12 train should-trigger queries with the siblings installed:
  83/84 → 82/84 runs.
- Eval set 18 → 36 queries: negatives for eight `vllm-*` siblings, `keda`, a
  non-model Kubernetes manifest and a generic request; the rollout mirror of
  the spec-decode negative; eight more should-trigger queries. Two negatives
  whose handler is not a skill in this tree removed.
- The one failing train query is the benchmarking negative under Decided. One
  contextual should-trigger query fails in the held-out set; it is not named
  here so the set stays blind.
