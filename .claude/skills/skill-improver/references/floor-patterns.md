# Floor Mode — Classification, Buckets, and What the Floor Moves

Full Floor Mode reference; `SKILL.md` §"Floor" carries the stub. Load when running `knowledge-floor.py` / `floor-fleet.py` or reading their leaderboard.

## Table of Contents
- [Classify the skill before probing it](#classify-the-skill-before-probing-it)
- [Invocation](#invocation)
- [The three buckets](#the-three-buckets)
- [Two limits](#two-limits)
- [Floor results as a rubric input](#floor-results-as-a-rubric-input)

## Classify the skill before probing it

Floor measures what a **bare** model (no skills, tools, web) knows about the skill's subject. Whatever it knows unaided need not be in the skill. Read-only: surfaces candidates, never edits.

| Skill kind | Content | Floor reading |
|---|---|---|
| Capability-uplift | something the base model cannot do, or not consistently | run Floor; high `KNOWS` = decay |
| Encoded-preference | sequences things the model can do into a house order (air-gap procedure, commit ritual, which valid tool this operator uses) | do not run; claims are **supposed** to score `KNOWS`, so a high floor is not a delete list |
| Both | mixed | probe, and scope the delete list to capability-uplift claims |

`--extract` writes the claim set; preference claims in it must not be touched by a high `KNOWS` share.

## Invocation

- One skill: `python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge-floor.py --skill <name> [--extract]`
- Whole fleet: `python3 ${CLAUDE_SKILL_DIR}/scripts/floor-fleet.py --root <dir>` — writes each result as it lands (resumable); ranks by share of claims the strongest probed model already knows.

## The three buckets

Claims are extracted once to `<skill>/references/knowledge-claims.json` (cached, hash-stamped against SKILL.md); each is put to the bare model across a model × effort matrix.

| Bucket | Meaning | Action |
|---|---|---|
| **KNOWS** | model states the claim correctly | deletion **candidate** |
| **UNKNOWN** | does not know, or hedges | keep — real knowledge transfer |
| **CONFLICTS** | confidently states something else | keep, and make it louder |

`CONFLICTS` is the most valuable bucket: unaided, the model proceeds confidently wrong.

## Two limits

- Recall is not application: `KNOWS` is a candidate to confirm with an eval delta, never a licence to cut.
- A conflict never means the skill is wrong: the skill is presumed correct, the model stale (`SKILL.md` §"Rules for every mode" (the skill outranks training data)). The grader prompt encodes this; do not weaken it.

Re-run on each model release; the movement in `KNOWS` is the delete list.

## Floor results as a rubric input

Floor results move the unmeasured Dim 10 cap off its flat `8` and classify the skill: deletion candidate, pure transfer, or correction skill. High floor with durable conflicts means *louder*, not leaner. See `references/quality-rubric.md` § Negative-Transfer Gate.
