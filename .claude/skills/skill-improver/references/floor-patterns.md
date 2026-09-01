# Floor Mode — Classification, Buckets, and What the Floor Moves

The full Floor Mode reference. `SKILL.md` §"Floor Mode" carries the stub —
invocation plus the two rules that bind without opening this file. Load this
when running `knowledge-floor.py` / `floor-fleet.py` or reading their
leaderboard.

## Table of Contents
- [Classify the skill before probing it](#classify-the-skill-before-probing-it)
- [Invocation](#invocation)
- [The three buckets](#the-three-buckets)
- [Two limits](#two-limits)
- [Floor results as a rubric input](#floor-results-as-a-rubric-input)

## Classify the skill before probing it

Measure what a **bare** model already knows about the skill's subject — no
skills loaded, no tools, no web. Whatever the model knows unaided does not need
to be in the skill; as the bleeding edge is absorbed into training, the skill
should shrink to the delta. Read-only: surfaces candidates, never edits.

**Classify the skill before probing it — the premise does not hold for both
kinds.** A *capability-uplift* skill encodes something the base model cannot do,
or cannot do consistently; its content decays as models improve, which is
exactly what a floor probe detects. An *encoded-preference* skill sequences
things the model can already do, into a specific house order — an air-gap
procedure, a commit ritual, which of several valid tools this operator uses.
Its claims are **supposed** to score `KNOWS`: the model knowing what a Helm
upgrade is says nothing about whether it knows to do it this way here.

Run Floor Mode on capability-uplift skills. On an encoded-preference skill a
high floor is the expected reading and not a delete list, so the probe spends
tokens to produce a number that must then be ignored — and the standing risk
is that some pass eventually acts on it. Where a skill is both, probe it and
scope the delete list to the capability-uplift claims. `--extract` writes the
claim set; the preference claims in it are the ones a high `KNOWS` share must
not touch.

## Invocation

One skill — `python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge-floor.py --skill <name> [--extract]`
· whole fleet — `python3 ${CLAUDE_SKILL_DIR}/scripts/floor-fleet.py --root <dir>`, which
writes each result as it lands so a multi-hour pass is resumable, and ranks by the
share of claims the strongest probed model already knows.

## The three buckets

The skill is its own answer key. Claims are extracted once to
`<skill>/references/knowledge-claims.json` (cached, hash-stamped against
SKILL.md) and each is put to the bare model across a model × effort matrix.
Three buckets:

| Bucket | Meaning | Action |
|---|---|---|
| **KNOWS** | model states the claim correctly | deletion **candidate** |
| **UNKNOWN** | does not know, or hedges | keep — real knowledge transfer |
| **CONFLICTS** | confidently states something else | keep, and make it louder |

`CONFLICTS` is the valuable bucket: filling a blank is worth something,
overriding a confident wrong prior is worth more, because unaided the model
does not hesitate — it proceeds, wrong.

## Two limits

**Recall is not application** — a model can state a flag and still not think
to use it mid-task, so `KNOWS` is a candidate to confirm with an eval delta,
never a licence to cut. And **a conflict never means the skill is wrong**:
skills here are freshened past the model cutoff, so the skill is presumed
correct and the model presumed stale (`SKILL.md` §"The Skill Outranks Training
Data"). The grader prompt encodes this; without it the probe becomes a
downgrade machine.

Re-run on each model release — the movement in `KNOWS` is the delete list.

## Floor results as a rubric input

Floor results move the unmeasured Dim 10 cap off its flat `8`, and they
classify the skill into one of three profiles — deletion candidate, pure
transfer, or correction skill. A high floor with durable conflicts means
*louder*, not leaner. See `references/quality-rubric.md` § Negative-Transfer
Gate.
