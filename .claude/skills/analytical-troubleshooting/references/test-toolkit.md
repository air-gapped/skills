# Test Selection Toolkit

Testing is where time and money actually go, so choose tests like an
economist, not a completionist. Full analysis of *what to test next* beats
enthusiasm about *what to test first*.

## The ordering rule: probability ÷ cost

When candidate causes each have a check/fix, order actions by
`likelihood ÷ cost` — most-probable-per-unit-effort first, re-checking the
system after each action. This greedy rule is provably optimal under
single-fault assumptions and a strong heuristic beyond them. Two corollaries:

- A 30-second test of a 20% candidate beats a 2-hour test of a 60% one.
- Update after every result: probabilities shift, so the ordering is a live
  queue, not a fixed plan.

**Is a measurement worth taking at all?** Observe (rather than act) only when
the observation's cost plus the expected cost of what you'll do *after it*
beats acting now. Don't gold-plate certainty on a cause whose fix is cheaper
than the next test — apply the fix as the test (Stage 5 "fix and monitor").

## Split the space, don't enumerate it

Eliminating *classes* of causes is exponentially cheaper than testing causes
one at a time.

- **Half-split:** in any chain (signal path, pipeline, request flow), test
  the midpoint: good → fault is downstream; bad → upstream. Repeat. A
  10-stage chain falls in ~3–4 probes instead of ~5 average by walking.
  Underused everywhere; use it whenever the system has a topology.
- **Families of variation:** before hunting individual causes, determine
  which *family* the cause lives in by comparing patterns you already have:
  within-one-unit vs unit-to-unit vs time-to-time vs site-to-site. One
  observational comparison ("do all replicas fail identically, or each
  differently?") can eliminate whole families and every cause inside them.
- **Best vs worst:** put the most-affected and least-affected units side by
  side and diff *everything*. Extreme units concentrate signal; a handful of
  paired comparisons often reveals the distinguishing factor without any
  instrumentation.
- **Problem-splitting:** if the failure pattern is heterogeneous (different
  locations, different signatures), suspect several smaller problems wearing
  one name; split and re-specify before hunting causes (back to Stage 0).

## Experiment discipline

- **One variable per experiment.** Change one thing, observe, record, revert
  if it didn't help. Multi-variable changes produce unattributable results
  and contaminate the spec table.
- **Record every result, including boring ones.** "No change" is IS-NOT
  data. Keep the audit trail in the spec/hypothesis file — memory of what
  was tried decays within a session, never mind across days.
- **Name the refutation target before running** (hard rule 3): "this test
  kills H2 if the counter is flat, kills H4 if it spikes". If a proposed test
  kills nothing, find a better test.
- **Reversal is the gold standard:** undo the suspected change → problem
  stops; redo it → problem returns. Twice the evidence of a swap, because it
  demonstrates the mechanism both ways.
- **Minimize the failing case** when reproduction is cheap: iteratively cut
  the input/config/diff in half, keeping whichever half still fails
  (delta debugging). The minimal failing case usually *is* the diagnosis.
- **Swap symmetrically, interpret carefully:** if moving the suspect part
  moves the problem, strong signal. If not — you've learned the part is
  innocent, so update; don't keep swapping unfailing components "to be sure"
  (part-shotgunning is the classic unbounded fast path).

## Agent-executed tests

When shell/log/API access allows testing directly, the same discipline binds —
speed is not a license to shotgun:

- Still name the refutation target before each probe; a fast loop of
  confirmation-only tests is just faster anchoring.
- Prefer read-only probes (logs, counters, configs, dry-runs) before
  state-changing experiments; a state change mid-hunt contaminates the very
  evidence being gathered, so it needs the one-variable + revert discipline.
- Transcribe raw command output into the table as `[observed]` — quote the
  actual line, not a paraphrase of it. Summarized evidence is where
  fabrication creeps in.
- Cheap tests shift the economics (dozens of probes per human round-trip),
  not the bookkeeping: batch reads freely, but update the table and
  hypothesis statuses before choosing the next batch, or the loop degrades
  into undirected scanning.

## Human-executed tests

When the human runs the tests (hardware in their hands, prod behind their
badge):

- Specify the *procedure and the discriminating observable*, not vibes:
  "boot with only DIMM A2 populated; note whether the beep pattern changes"
  beats "try reseating the RAM".
- State in advance what each possible outcome will mean for the hypothesis
  list — this keeps interpretation honest and makes the human a
  collaborator, not a gofer.
- One test (or one tight batch) per round-trip; long checklists rot.
- Ask for raw observations ("what exactly did it print?"), not conclusions
  ("did it work?"). Transcribe results into the table with `[observed]` only
  when the human actually observed them.
