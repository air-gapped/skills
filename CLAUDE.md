# Skills repo

Each skill is a directory `.claude/skills/<name>/`. The reader of every file in
it is an agent in the middle of a task.

## Before changing a skill, read its history

1. `git log --format='%ad %s' --date=short -15 -- .claude/skills/<name>`:
   earlier commits say what was tried and why a rule exists.
2. `references/improvement-backlog.md`: the `## Discard guards` and
   `## Decided` sections list changes that were tried and rejected. Keep them.
3. `references/sources.md`: where each fact came from, and the `Freshened:`
   date of the last full check.

Done when you can say why the text you are about to change is there.

## Where content goes

| Content | File |
|---|---|
| What to do; a known failure, its versions and its fix | `SKILL.md`, detail in `references/<topic>.md` |
| Where a fact came from and how far it was verified | `references/sources.md` |
| Work that waits on something absent | `references/improvement-backlog.md`, `## Open`, with a `Blocker:` line |
| Outcome and trigger eval cases | `evals/evals.json`, `references/trigger-evals.json` |

A version, date, flag or model name in a skill is often newer than your
training data. Verify it online before changing it.

## Commit

```bash
make stage SKILL="<name> [<name>...]"
git commit
```

`make stage` formats, stages the skill and regenerates the README table and
the plugin manifest. A hook that fails prints what to fix; fix it, run
`make stage` again and commit again.

A push is refused when a skill with `evals/evals.json` has changed text and no
eval run on that text. Run the cases the change touches; the run writes
`evals/last-run.json`, which is committed with the change:

```bash
python3 .claude/skills/skill-improver/scripts/outcome-eval.py .claude/skills/<name> --case '<NN-glob>'
```

A case is about $2 at API prices; on a subscription it uses plan quota, not
money. State the number of cases before running.

## Rules for scoring, freshening, evals and backlogs

`.claude/skills/skill-improver/SKILL.md` and its `references/`.
