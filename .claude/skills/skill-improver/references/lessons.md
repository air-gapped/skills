# Lessons — transferable, evidence-backed, read in Phase 0

Cross-skill lessons from finished `fix` / `improve` / `freshen` passes. Phase 0 of every pass
reads this file and applies each entry whose `cue` matches the target. The pass ends by adding
**at most one** entry, or none.

## Entry format

```markdown
### <short title> (YYYY-MM-DD)
- **cue:** the shape of situation it applies to — a pattern another skill can hit, not this skill's facts
- **lesson:** the operation to perform, naming the skill component it concerns (SKILL.md rule, reference table, script, eval case)
- **evidence:** skill + date + the attribution rows or blocker it rests on, with the execution contrast
- **confidence:** high | medium | low — and why
```

| Admit | Reject |
|---|---|
| rests on a `helped`/`hurt` attribution row, or on a blocker that proved absent | rests only on `confounded` rows, or on adoption of the final version |
| cue fires on a different skill | cue restates one skill's fact ("cloud-init 26.1 is in noble-updates") |
| lesson is checkable ("run each bundled script on a planted positive case") | lesson is advice ("be thorough") |

A second pass whose evidence matches an existing entry adds its evidence line there instead of a new
entry. An entry with `helped` evidence from 3 different skills graduates: move the rule into the
reference file it concerns and delete the entry here. An entry whose cue fired and whose lesson
`hurt` gets deleted, with the reason in the commit body.

## Entries

### Distro-release gating hides package-version drift (2026-10-20)
- **cue:** a skill gates behaviour on a distro release name ("24.04 has feature X", "on RHEL 9 use Y")
- **lesson:** gate the SKILL.md rule on the installed package version (`dpkg -l <pkg>`, `rpm -q <pkg>`), and during freshen read the release's updates pocket and the distro's patch list for reverted upstream changes
- **evidence:** ubuntu-netplan and ubuntu-cloud-init, 2026-10-20 freshen — both mapped 24.04 to an upstream version that updates had moved (netplan 1.1.x, cloud-init 26.1), and the 24.04 cloud-init build reverts five upstream changes; each fix verified against Launchpad and the packaging branch (`helped`)
- **confidence:** high — two independent skills, same mechanism

### An assertion that fails in both arms is the eval, not the skill (2026-11-09)
- **cue:** an outcome run lists a weak case whose failed assertion also fails every run of the without arm, or the skill's `evals.json` names another harness in `provenance.harness`
- **lesson:** before editing SKILL.md, test the assertion against the runner — the tools `outcome-eval.py` grants, the empty workspace, the prompt's own constraints. When no correct answer can pass, correct the eval case in its own commit and re-run it with `--case`
- **evidence:** skill-improver 2026-11-09 fix — both weak cases (08, 11) failed on assertions no answer could pass (every judge vote FAIL in both arms); after rewording, `--case` re-runs went 0.67 → 1.00 with the skill on answers of the same substance, and a third assertion that had failed 2 of 3 runs passed 3 of 3 untouched (`helped`: the measurement was wrong, the skill was not)
- **confidence:** medium — one skill, two cases; the mechanism applies to any eval set older than its runner

### A case re-run credits an edit only against the old text in the same run (2026-11-09)
- **cue:** a `--case` re-run after a skill edit shows the failed assertion passing
- **lesson:** make the re-run `outcome-eval.py <skill-dir> --case <glob> --against HEAD` before committing the edit, so the pre-edit text answers the same case in the same run. Credit the edit when the old arm still fails, or when the cited moment is gone from the new answers and still in the old ones
- **evidence:** skill-improver 2026-11-09 improve — eval 12's assertion failed 2 of 3 on the benchmark and 0 of 3 after the edit, then the pre-edit text passed it 2 of 2 in a later against arm (only the answer moment separated the versions); eval 04's assertion failed 3 of 3 and again 2 of 2 on the old text and passed 5 of 5 on the new (`helped`)
- **confidence:** medium — one skill, two cases
