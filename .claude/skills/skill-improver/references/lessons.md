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

### Bundled check scripts can pass vacuously (2026-10-20)
- **cue:** a skill ships a script whose job is to detect a failure (assertion runner, leak scanner, linter)
- **lesson:** run each detector on a planted positive case and on an error-shaped input before trusting its "clean"/"pass"; add the planted case to the skill's test step
- **evidence:** claude-code-ci-harness, 2026-10-20 — the token-leak scanner never read its token list (always "clean"; a planted leak reproduced it) and the event asserter passed a run whose result was an API error (`is_error=true` with `subtype=success`); both fixed and re-run (`helped`)
- **evidence:** litellm-valkey, 2026-10-27 — the preflight script printed "ping healthy" and exited 0 on any non-200 ping; a mock returning 500 reproduced it, the first live run exposed it (`helped`)
- **confidence:** high — two skills, three scripts

### Universal capability claims break per item (2026-10-20)
- **cue:** a skill states that every member of a set supports something ("all modules accept the token", "the flag replaces the list"), or relies on a tool's `--help` for semantics
- **lesson:** verify the claim per member in the source at the pinned tag; list the exceptions in the reference table the agent reads
- **evidence:** ansible-idrac-9-10 (four module families reject `x_auth_token`; two examples would have failed) and jira-cli (`--component` appends although `--help` says replace; confirmed in code and live), both 2026-10-20 (`helped`)
- **confidence:** high — two skills, source-confirmed
